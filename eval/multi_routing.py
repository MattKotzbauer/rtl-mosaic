#!/usr/bin/env python3
"""Cross-LLM routing eval: swap planner LLM, score against hand-labeled gold.

For each (provider, cpu_ip problem):
  1. Send the planner prompt to the LLM
  2. Parse JSON subblocks
  3. Run ip_router.resolve_subblock on REUSE_IP-suggested blocks
  4. Score against eval/gold_labels.GOLD
"""
import os, sys, json, time, traceback, concurrent.futures, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.providers import call, PROVIDERS
from eval.gold_labels import GOLD, all_problem_ids
from eval.test_routing import _read_prompt, _score_problem
from harness.planner import PLANNER_SYSTEM, _extract_json_array, _fallback_single_block
from harness import ip_router

RESULTS_DIR = os.path.join(ROOT, "results", "multi_routing")
os.makedirs(RESULTS_DIR, exist_ok=True)


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


def run_one(provider_key, problem_id):
    t0 = time.time()
    out = {"problem": problem_id, "provider": provider_key}
    try:
        spec = _read_prompt(problem_id)
    except Exception as e:
        out["error"] = f"prompt: {e}"
        return out

    prompt = PLANNER_SYSTEM + "\n\nSPEC:\n" + spec
    try:
        raw = call(provider_key, prompt, timeout=180)
    except Exception as e:
        out["error"] = f"api: {e}"[:300]
        out["elapsed_s"] = round(time.time() - t0, 2)
        return out

    parsed = _extract_json_array(raw)
    blocks = _normalize_blocks(parsed, spec)
    out["raw_len"] = len(raw)

    router_records = []
    for sb in blocks:
        rec = {
            "name": sb.get("name"),
            "suggested_kind": sb.get("suggested_kind"),
            "search_query": sb.get("search_query"),
            "picked_ip": None,
            "router_kind": None,
        }
        if rec["suggested_kind"] == "REUSE_IP":
            try:
                res = ip_router.resolve_subblock(sb)
                rec["router_kind"] = res.get("kind")
                if res.get("kind") == "ip":
                    rec["picked_ip"] = res.get("id")
            except Exception as e:
                rec["router_error"] = str(e)[:200]
        router_records.append(rec)

    out["planner_blocks"] = blocks
    out["router_records"] = router_records
    out["score"] = _score_problem(problem_id, blocks, router_records)
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


def aggregate(results):
    """Per-provider P/R/KA averaged over problems."""
    by_p = {}
    for r in results:
        if "error" in r or "score" not in r:
            continue
        p = r["provider"]
        s = r["score"]
        by_p.setdefault(p, []).append(s)
    agg = {}
    for p, scores in by_p.items():
        n = len(scores)
        agg[p] = {
            "n": n,
            "precision_mean": round(sum(s["precision"] for s in scores) / n, 3),
            "recall_mean":    round(sum(s["recall"]    for s in scores) / n, 3),
            "kind_agreement_mean": round(sum(s["kind_agreement"] for s in scores) / n, 3),
            "f1_mean": round(sum(
                (2 * s["precision"] * s["recall"]) / (s["precision"] + s["recall"])
                if (s["precision"] + s["recall"]) > 0 else 0.0 for s in scores
            ) / n, 3),
            "avg_subblocks": round(sum(s["n_subblocks_planned"] for s in scores) / n, 2),
            "avg_picked_ips": round(sum(len(s["picked_ips"]) for s in scores) / n, 2),
        }
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", nargs="*", default=list(PROVIDERS.keys()))
    ap.add_argument("--problems", nargs="*", default=None)
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args()

    pids = args.problems or all_problem_ids()
    jobs = [(p, q) for p in args.providers for q in pids]
    print(f"[multi_routing] {len(args.providers)} providers x {len(pids)} problems = {len(jobs)} runs")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, p, q): (p, q) for p, q in jobs}
        for fut in concurrent.futures.as_completed(futs):
            r = fut.result()
            results.append(r)
            if "error" in r:
                print(f"  ERR  {r['provider']:30s} {r['problem']:30s} {r['error'][:80]}", flush=True)
            else:
                s = r["score"]
                print(f"  OK   {r['provider']:30s} {r['problem']:30s} "
                      f"P={s['precision']} R={s['recall']} KA={s['kind_agreement']}", flush=True)

    by_provider_problem = {}
    for r in results:
        by_provider_problem.setdefault(r["provider"], {})[r["problem"]] = r

    for p, perprob in by_provider_problem.items():
        safe = p.replace(":", "_").replace("/", "_")
        with open(os.path.join(RESULTS_DIR, f"{safe}.json"), "w") as f:
            json.dump(perprob, f, indent=2)

    agg = aggregate(results)
    sum_path = os.path.join(RESULTS_DIR, "summary.json")
    if os.path.exists(sum_path):
        existing = json.load(open(sum_path))
        existing.update(agg)
        agg = existing
    with open(sum_path, "w") as f:
        json.dump(agg, f, indent=2)

    # nice console table
    print("\n=== Summary (per provider, mean over problems) ===")
    print(f"{'provider':32s} {'P':>7s} {'R':>7s} {'F1':>7s} {'KA':>7s}  n_sub  n_pick")
    for p, m in sorted(agg.items(), key=lambda kv: -kv[1]["f1_mean"]):
        print(f"{p:32s} {m['precision_mean']:7.3f} {m['recall_mean']:7.3f} "
              f"{m['f1_mean']:7.3f} {m['kind_agreement_mean']:7.3f}  "
              f"{m['avg_subblocks']:5.2f}  {m['avg_picked_ips']:5.2f}")


if __name__ == "__main__":
    main()
