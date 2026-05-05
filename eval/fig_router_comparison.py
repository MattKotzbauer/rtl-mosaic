#!/usr/bin/env python3
"""Side-by-side bar comparing keyword vs embedding router F1 per LLM."""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KW = os.path.join(ROOT, "results", "multi_routing", "summary.json")
EM = os.path.join(ROOT, "results", "multi_routing_embed", "summary.json")
OUT_S = os.path.join(ROOT, "slides", "figs", "router_comparison")
OUT_R = os.path.join(ROOT, "report", "figs", "router_comparison")


def short(p):
    return p.replace("openai:","").replace("claude:","").replace("bedrock:","").replace("gemini:","")


def color(p):
    if p.startswith("openai"):  return "#10a37f"
    if p.startswith("claude"):  return "#cc785c"
    if p.startswith("bedrock"): return "#4d6bfe"
    return "#ea4335"


def main():
    kw = json.load(open(KW))
    em = json.load(open(EM))
    rows = []
    for p in kw:
        if p in em:
            rows.append((p, kw[p]["f1_mean"], em[p]["f1_mean"], em[p]["f1_mean"] - kw[p]["f1_mean"]))
    rows.sort(key=lambda r: -r[3])  # by improvement

    labels = [short(r[0]) for r in rows]
    kw_f1 = [r[1] for r in rows]
    em_f1 = [r[2] for r in rows]
    cols = [color(r[0]) for r in rows]
    deltas = [r[3] for r in rows]

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(labels)); w = 0.4
    ax.bar(x - w/2, kw_f1, w, label="Keyword router", color=cols, alpha=0.5, edgecolor="black", linewidth=0.4)
    ax.bar(x + w/2, em_f1, w, label="Embedding router", color=cols, alpha=1.0, edgecolor="black", linewidth=0.4)
    for i, d in enumerate(deltas):
        sign = "+" if d >= 0 else ""
        clr = "#1a7a1a" if d > 0.01 else ("#a01010" if d < -0.01 else "#666")
        ax.text(i, max(kw_f1[i], em_f1[i]) + 0.02, f"{sign}{d:.2f}", ha="center", fontsize=8, color=clr, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Routing F1 (mean over 16 problems)")
    ax.set_title("Embedding-similarity router vs keyword-overlap router (same planner outputs)")
    ax.set_ylim(0, max(em_f1 + kw_f1) * 1.20)
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    for o in (OUT_S, OUT_R):
        os.makedirs(os.path.dirname(o), exist_ok=True)
        fig.savefig(o + ".pdf", bbox_inches="tight"); fig.savefig(o + ".png", dpi=160, bbox_inches="tight")
        print(f"wrote {o}.pdf and {o}.png")
    plt.close(fig)

    # Also print summary
    mean_d = sum(deltas) / len(deltas)
    pos = sum(1 for d in deltas if d > 0.01)
    print(f"\n{'model':32s}  keyword  embed   delta")
    print("-" * 60)
    for r in rows:
        sign = "+" if r[3] >= 0 else ""
        print(f"{short(r[0]):32s}  {r[1]:>6.3f}  {r[2]:>6.3f}  {sign}{r[3]:>6.3f}")
    print(f"\nmean delta = {mean_d:+.3f},  models improved by >0.01 = {pos}/{len(rows)}")


if __name__ == "__main__":
    main()
