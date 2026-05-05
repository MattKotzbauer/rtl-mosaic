#!/usr/bin/env python3
"""Replay cached planner outputs through the embedding router and rescore.

Reads results/multi_routing/<provider>.json (already has planner_blocks),
swaps the keyword router for the embedding router, recomputes P/R/F1/KA.
Saves to results/multi_routing_embed/.
"""
import os, sys, json, glob, time
import concurrent.futures

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from eval.gold_labels import GOLD
from eval.test_routing import _score_problem
from harness import ip_router_embed

SRC = os.path.join(ROOT, "results", "multi_routing")
DST = os.path.join(ROOT, "results", "multi_routing_embed")
os.makedirs(DST, exist_ok=True)


def rerun_record(rec):
    """Replay one (LLM, problem) record through the embedding router."""
    out = dict(rec)
    blocks = rec.get("planner_blocks", []) or []
    new_router_records = []
    for sb in blocks:
        rr = {
            "name": sb.get("name"),
            "suggested_kind": sb.get("suggested_kind"),
            "search_query": sb.get("search_query"),
            "picked_ip": None,
            "router_kind": None,
        }
        if sb.get("suggested_kind") == "REUSE_IP":
            try:
                res = ip_router_embed.resolve_subblock(sb)
                rr["router_kind"] = res.get("kind")
                if res.get("kind") == "ip":
                    rr["picked_ip"] = res.get("id")
                rr["embed_score"] = res.get("score")
            except Exception as e:
                rr["router_error"] = str(e)[:200]
        new_router_records.append(rr)
    out["router_records"] = new_router_records
    if "score" in rec:
        out["score"] = _score_problem(rec["problem"], blocks, new_router_records)
    return out


def main():
    # warm up cache (one API call per IP)
    ip_router_embed._load_corpus_embeddings()

    new_summary = {}
    for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
        if any(f.endswith(x) for x in ("summary.json","failure_modes.json","cost_latency.json")):
            continue
        d = json.load(open(f))
        provider = None
        new_d = {}
        scores = []
        for prob_id, rec in d.items():
            if "error" in rec:
                new_d[prob_id] = rec; continue
            new_rec = rerun_record(rec)
            new_d[prob_id] = new_rec
            provider = new_rec.get("provider", provider)
            if "score" in new_rec:
                scores.append(new_rec["score"])
        out_f = os.path.join(DST, os.path.basename(f))
        json.dump(new_d, open(out_f, "w"), indent=2)
        if provider and scores:
            n = len(scores)
            f1s = []
            for s in scores:
                p, r = s["precision"], s["recall"]
                f1s.append(2*p*r/(p+r) if (p+r) > 0 else 0)
            new_summary[provider] = {
                "n": n,
                "precision_mean": round(sum(s["precision"] for s in scores)/n, 3),
                "recall_mean":    round(sum(s["recall"]    for s in scores)/n, 3),
                "kind_agreement_mean": round(sum(s["kind_agreement"] for s in scores)/n, 3),
                "f1_mean": round(sum(f1s)/n, 3),
                "avg_subblocks": round(sum(s["n_subblocks_planned"] for s in scores)/n, 2),
                "avg_picked_ips": round(sum(len(s["picked_ips"]) for s in scores)/n, 2),
            }
            print(f"  {provider:32s} F1={new_summary[provider]['f1_mean']:.3f} (n={n})")

    json.dump(new_summary, open(os.path.join(DST, "summary.json"), "w"), indent=2)
    print(f"\nwrote {DST}/summary.json with {len(new_summary)} providers")


if __name__ == "__main__":
    main()
