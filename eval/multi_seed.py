#!/usr/bin/env python3
"""Multi-seed routing eval for the 4 headline models on the 26-problem set.

For each (model, problem, seed) triple, run the planner+router pipeline.
Aggregate to mean +/- std per (model, problem). Useful for putting error
bars on every cell of the leaderboard.

Output:
  results/multi_seed/<provider>__seed<n>.json   (per seed, per provider)
  results/multi_seed/summary.json                (per-provider mean+std)
"""
import os, sys, json, time, traceback, concurrent.futures, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.providers import call
from eval.gold_labels import GOLD, all_problem_ids
from eval.test_routing import _read_prompt, _score_problem
from harness.planner import PLANNER_SYSTEM, _extract_json_array, _fallback_single_block
from harness import ip_router

DST = os.path.join(ROOT, "results", "multi_seed")
os.makedirs(DST, exist_ok=True)

HEADLINE = [
    "claude:opus-4-7",
    "openai:gpt-5.2",
    "bedrock:deepseek-v3.2",
    "gemini:2.5-flash-lite",
]


def _normalize_blocks(parsed, spec_text):
    out = []
    for i, sb in enumerate(parsed or []):
        if not isinstance(sb, dict):
            continue
        kind = str(sb.get("suggested_kind", "GENERATE")).upper()
        if kind not in ("REUSE_IP", "GENERATE"):
            kind = "GENERATE"
        out.append({
            "name": str(sb.get("name") or f"sub_{i}"),
            "role": str(sb.get("role") or ""),
            "suggested_kind": kind,
            "port_spec": str(sb.get("port_spec") or ""),
            "search_query": str(sb.get("search_query") or sb.get("name", "")),
        })
    return out or _fallback_single_block(spec_text)


def run_one(provider_key, problem_id, seed):
    t0 = time.time()
    out = {"problem": problem_id, "provider": provider_key, "seed": seed}
    try:
        spec = _read_prompt(problem_id)
    except Exception as e:
        out["error"] = f"prompt: {e}"; return out

    # Add a per-seed nonce to nudge non-deterministic providers; harmless for deterministic ones
    prompt = PLANNER_SYSTEM + "\n\nSPEC:\n" + spec + f"\n\n[seed={seed}]"
    try:
        raw = call(provider_key, prompt, timeout=180)
    except Exception as e:
        out["error"] = f"api: {e}"[:300]
        out["elapsed_s"] = round(time.time() - t0, 2)
        return out

    parsed = _extract_json_array(raw)
    blocks = _normalize_blocks(parsed, spec)
    router_records = []
    for sb in blocks:
        rr = {
            "name": sb.get("name"),
            "suggested_kind": sb.get("suggested_kind"),
            "search_query": sb.get("search_query"),
            "picked_ip": None,
            "router_kind": None,
        }
        if rr["suggested_kind"] == "REUSE_IP":
            try:
                res = ip_router.resolve_subblock(sb)
                rr["router_kind"] = res.get("kind")
                if res.get("kind") == "ip":
                    rr["picked_ip"] = res.get("id")
            except Exception as e:
                rr["router_error"] = str(e)[:200]
        router_records.append(rr)

    out["planner_blocks"] = blocks
    out["router_records"] = router_records
    out["score"] = _score_problem(problem_id, blocks, router_records)
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


def f1(s):
    p, r = s["precision"], s["recall"]
    return 2*p*r / (p + r) if (p + r) > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--providers", nargs="*", default=HEADLINE)
    args = ap.parse_args()

    pids = all_problem_ids()
    jobs = [(p, q, s) for p in args.providers for q in pids for s in range(args.seeds)]
    print(f"[multi_seed] {len(args.providers)} providers x {len(pids)} problems x {args.seeds} seeds = {len(jobs)} runs")

    by_pps = {}  # (provider, problem, seed) -> rec
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, p, q, s): (p, q, s) for p, q, s in jobs}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            key = (r["provider"], r["problem"], r["seed"])
            by_pps[key] = r
            tag = "ERR" if "error" in r else "OK "
            print(f"  {tag}  s{r['seed']}  {r['provider']:32s} {r['problem']:38s}", flush=True)

    # write per-(provider, seed) JSON
    for p in args.providers:
        for s in range(args.seeds):
            block = {q: by_pps.get((p, q, s)) for q in pids}
            safe = p.replace(":", "_") + f"__seed{s}"
            json.dump(block, open(os.path.join(DST, safe + ".json"), "w"), indent=2)

    # aggregate
    summary = {}
    for p in args.providers:
        # per-problem F1 across seeds
        per_problem = []
        for q in pids:
            f1_seeds = []
            for s in range(args.seeds):
                rec = by_pps.get((p, q, s))
                if rec and "score" in rec:
                    f1_seeds.append(f1(rec["score"]))
            if f1_seeds:
                mean = sum(f1_seeds) / len(f1_seeds)
                std = (sum((x - mean)**2 for x in f1_seeds) / len(f1_seeds)) ** 0.5
                per_problem.append({"problem": q, "f1_mean": round(mean, 3), "f1_std": round(std, 3), "n_seeds": len(f1_seeds)})
        if per_problem:
            f1_means = [r["f1_mean"] for r in per_problem]
            f1_stds  = [r["f1_std"]  for r in per_problem]
            summary[p] = {
                "n_problems": len(per_problem),
                "n_seeds": args.seeds,
                "f1_mean_of_means": round(sum(f1_means) / len(f1_means), 3),
                "f1_mean_of_stds":  round(sum(f1_stds) / len(f1_stds), 3),
                "per_problem": per_problem,
            }

    json.dump(summary, open(os.path.join(DST, "summary.json"), "w"), indent=2)
    print(f"\nwrote {DST}/summary.json")
    print(f"\n{'provider':32s}  F1-mean   mean-std   n-prob   n-seeds")
    print("-" * 80)
    for p, m in sorted(summary.items(), key=lambda kv: -kv[1]['f1_mean_of_means']):
        print(f"{p:32s}  {m['f1_mean_of_means']:.3f}     {m['f1_mean_of_stds']:.3f}      {m['n_problems']:>3d}      {m['n_seeds']:>3d}")


if __name__ == "__main__":
    main()
