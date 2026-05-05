#!/usr/bin/env python3
"""Cost-and-latency analysis for the multi-LLM routing eval.

Reads per-provider records from results/multi_routing/<provider>.json,
estimates cost and aggregates latency, joins with F1 from summary.json,
prints a table sorted by F1, and writes results/multi_routing/cost_latency.json.

Token estimation: input ~ 800 tokens (ChipBench prompt + planner system prompt);
output ~ raw_len / 4. We do not have actual token counts logged per call.
"""
import os, sys, json, glob
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTING_DIR = os.path.join(ROOT, "results", "multi_routing")
SUMMARY = os.path.join(ROUTING_DIR, "summary.json")
OUT = os.path.join(ROUTING_DIR, "cost_latency.json")

# USD per 1M tokens, 2026 published rates.
PRICES = {
    "claude:opus-4-7":              (15.00, 75.00),
    "claude:sonnet-4-6":             (3.00, 15.00),
    "claude:haiku-4-5":              (1.00,  5.00),
    "openai:gpt-5.4":               (10.00, 40.00),
    "openai:gpt-5.2":                (5.00, 20.00),
    "openai:gpt-5.1":                (3.00, 12.00),
    "openai:gpt-5":                  (2.50, 10.00),
    "openai:gpt-4.1":                (2.00,  8.00),
    "bedrock:deepseek-r1":           (1.35,  5.40),
    "bedrock:deepseek-v3.2":         (0.85,  3.50),
    "gemini:2.5-pro":                (1.25, 10.00),
    "gemini:2.5-flash":              (0.30,  2.50),
    "gemini:2.5-flash-lite":         (0.10,  0.40),
    "gemini:3-flash-preview":        (0.30,  2.50),
    "gemini:3.1-flash-lite-preview": (0.10,  0.40),
}
INPUT_TOKENS_EST = 800


def main():
    summary = json.load(open(SUMMARY))
    rows = {}
    files = [p for p in sorted(glob.glob(os.path.join(ROUTING_DIR, "*.json")))
             if not p.endswith(("summary.json", "cost_latency.json", "failure_modes.json"))]
    for f in files:
        d = json.load(open(f))
        latencies, output_tokens, n_records = [], [], 0
        provider = None
        for rec in d.values():
            if "error" in rec or "elapsed_s" not in rec:
                continue
            provider = rec.get("provider", provider)
            latencies.append(float(rec["elapsed_s"]))
            output_tokens.append(int(rec.get("raw_len", 0)) / 4.0)
            n_records += 1
        if provider is None or n_records == 0:
            continue
        in_p, out_p = PRICES.get(provider, (0.0, 0.0))
        cost_per_call = (INPUT_TOKENS_EST * in_p + np.mean(output_tokens) * out_p) / 1e6
        total_cost = (INPUT_TOKENS_EST * n_records * in_p +
                      sum(output_tokens) * out_p) / 1e6
        f1 = summary.get(provider, {}).get("f1_mean", 0.0)
        rows[provider] = {
            "n": n_records,
            "f1": f1,
            "mean_latency_s": float(np.mean(latencies)),
            "std_latency_s": float(np.std(latencies)),
            "mean_output_tokens_est": float(np.mean(output_tokens)),
            "total_cost_usd": float(total_cost),
            "cost_per_call_usd": float(cost_per_call),
            "cost_per_run_16_usd": float(cost_per_call * 16),
            "cost_per_f1_point_usd": float(cost_per_call * 16 / f1) if f1 > 0 else float("inf"),
            "input_price_per_m": in_p,
            "output_price_per_m": out_p,
        }

    json.dump(rows, open(OUT, "w"), indent=2)
    print(f"wrote {OUT}\n")

    print(f"{'provider':32s} {'F1':>5s} {'lat_s':>6s} {'tok_out':>7s} {'$/call':>8s} {'$/run':>8s} {'$/F1pt':>8s}")
    print("-" * 82)
    for p, r in sorted(rows.items(), key=lambda kv: -kv[1]["f1"]):
        print(f"{p:32s} {r['f1']:5.3f} {r['mean_latency_s']:6.1f} "
              f"{r['mean_output_tokens_est']:7.0f} "
              f"{r['cost_per_call_usd']*100:7.4f}c "
              f"{r['cost_per_run_16_usd']:7.4f}$ "
              f"{r['cost_per_f1_point_usd']:7.4f}$")

    print("\nCost-effectiveness ranking ($/F1pt, ascending = best):")
    cost_ranked = sorted(
        [(p, r) for p, r in rows.items() if r["f1"] > 0.0],
        key=lambda kv: kv[1]["cost_per_f1_point_usd"],
    )
    for i, (p, r) in enumerate(cost_ranked, 1):
        print(f"  {i:2d}. {p:32s} ${r['cost_per_f1_point_usd']:.4f}/F1pt "
              f"(F1={r['f1']:.3f}, ${r['cost_per_run_16_usd']:.4f}/run)")


if __name__ == "__main__":
    main()
