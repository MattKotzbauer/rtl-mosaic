#!/usr/bin/env python3
"""Quantify the four failure modes from the multi-LLM routing eval.

Modes (single-seed approximations):
  1. hallucinated_pick   -- planner suggested REUSE_IP, router picked an IP,
                            but the picked IP is NOT in this problem's gold set.
  2. over_decomposition  -- planner returned >=4 subblocks AND >=80% are GENERATE.
  3. under_decomposition -- planner returned <=1 subblock total AND gold has >=2
                            expected_subblocks.
  4. kind_flip_suspect   -- planner's REUSE_IP/GENERATE decisions don't match
                            gold (kind_agreement < 1.0). True kind-flip needs
                            multi-seed; this is a single-seed proxy.

Output:
  - results/multi_routing/failure_modes.json  -- per-(provider, mode) counts
  - prints leaderboard (sorted by total failures ascending = best first)
"""
import os, sys, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.gold_labels import GOLD

ROUTING_DIR = os.path.join(ROOT, "results", "multi_routing")
OUT_PATH = os.path.join(ROUTING_DIR, "failure_modes.json")

MODES = [
    "hallucinated_pick",
    "over_decomposition",
    "under_decomposition",
    "kind_flip_suspect",
]


def classify(record, gold_entry):
    """Return list of mode-name strings this (model, problem) record hits."""
    hits = []
    if "score" not in record or "error" in record:
        return hits
    blocks = record.get("planner_blocks", [])
    routers = record.get("router_records", [])
    score = record["score"]
    gold_ips = set(gold_entry.get("expected_subblocks", []))

    # 1. hallucinated_pick: any router pick not in gold (when gold non-empty)
    #    or any pick when gold is empty.
    for rr in routers:
        ip = rr.get("picked_ip")
        if ip and ip not in gold_ips:
            hits.append("hallucinated_pick")
            break

    # 2. over_decomposition: >=4 blocks, >=80% GENERATE
    if len(blocks) >= 4:
        n_gen = sum(1 for b in blocks if b.get("suggested_kind") == "GENERATE")
        if n_gen / len(blocks) >= 0.80:
            hits.append("over_decomposition")

    # 3. under_decomposition: <=1 block planned but gold has >=2 expected IPs
    #    (we use len(gold_ips) as "expected complexity" proxy)
    if len(blocks) <= 1 and len(gold_ips) >= 2:
        hits.append("under_decomposition")

    # 4. kind_flip_suspect: planner kind disagrees with gold
    if score.get("kind_agreement", 1.0) < 1.0:
        hits.append("kind_flip_suspect")

    return hits


def main():
    counts = {}  # provider -> {mode: int}
    total_problems = {}  # provider -> n records considered
    files = sorted(p for p in glob.glob(os.path.join(ROUTING_DIR, "*.json"))
                   if not p.endswith("summary.json")
                   and not p.endswith("failure_modes.json"))

    for f in files:
        per_prob = json.load(open(f))
        for prob_id, rec in per_prob.items():
            if "error" in rec or "score" not in rec:
                continue
            provider = rec.get("provider")
            if not provider:
                continue
            gold = GOLD.get(prob_id, {"expected_subblocks": []})
            counts.setdefault(provider, {m: 0 for m in MODES})
            total_problems[provider] = total_problems.get(provider, 0) + 1
            for mode in classify(rec, gold):
                counts[provider][mode] += 1

    # build output
    out = {
        "modes": MODES,
        "by_provider": {
            p: {**counts[p], "n_problems": total_problems[p]}
            for p in counts
        },
        "notes": {
            "hallucinated_pick": "Planner tagged a subblock REUSE_IP and the router picked an IP not in the problem's gold IP set.",
            "over_decomposition": ">=4 subblocks, >=80% labeled GENERATE.",
            "under_decomposition": "<=1 subblock planned for a problem whose gold expects >=2 reusable IPs.",
            "kind_flip_suspect": "Single-seed proxy for true kind-flip: kind_agreement < 1.0 on this run. True kind-flip requires multi-seed runs not yet collected.",
        },
    }
    os.makedirs(ROUTING_DIR, exist_ok=True)
    json.dump(out, open(OUT_PATH, "w"), indent=2)
    print(f"wrote {OUT_PATH}")

    # leaderboard
    rows = []
    for p, c in counts.items():
        total = sum(c[m] for m in MODES)
        rows.append((p, total, c, total_problems[p]))
    rows.sort(key=lambda r: r[1])  # ascending = best first

    print(f"\n{'provider':32s} {'tot':>4s}  {'n':>3s}  hall  over  under  kind")
    print("-" * 70)
    for p, total, c, n in rows:
        print(f"{p:32s} {total:>4d}  {n:>3d}  "
              f"{c['hallucinated_pick']:>4d}  {c['over_decomposition']:>4d}  "
              f"{c['under_decomposition']:>5d}  {c['kind_flip_suspect']:>4d}")


if __name__ == "__main__":
    main()
