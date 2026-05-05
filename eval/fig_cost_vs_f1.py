#!/usr/bin/env python3
"""Cost-vs-F1 scatter with Pareto frontier."""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "multi_routing", "cost_latency.json")
OUT_SLIDES = os.path.join(ROOT, "slides", "figs", "cost_vs_f1")
OUT_REPORT = os.path.join(ROOT, "report", "figs", "cost_vs_f1")


def color(p):
    if p.startswith("openai:"):  return "#10a37f"
    if p.startswith("claude:"):  return "#cc785c"
    if p.startswith("bedrock:"): return "#4d6bfe"
    if p.startswith("gemini:"):  return "#ea4335"
    return "#888"


def short(p):
    return (p.replace("openai:", "")
             .replace("claude:", "")
             .replace("bedrock:", "")
             .replace("gemini:", ""))


def main():
    d = json.load(open(SRC))
    items = sorted(d.items(), key=lambda kv: kv[1]["cost_per_run_16_usd"])
    xs = [r["cost_per_run_16_usd"] for _, r in items]
    ys = [r["f1"] for _, r in items]
    cols = [color(p) for p, _ in items]

    # Pareto frontier: walk from cheapest model and keep only points that
    # dominate everything cheaper (i.e. higher F1 than any cheaper model).
    pareto_x, pareto_y = [], []
    best_f1 = -1
    for x, y in zip(xs, ys):
        if y > best_f1:
            pareto_x.append(x); pareto_y.append(y)
            best_f1 = y

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(pareto_x, pareto_y, "k--", linewidth=1.0, alpha=0.6, label="Pareto frontier")
    for (p, r), c in zip(items, cols):
        ax.scatter(r["cost_per_run_16_usd"], r["f1"], s=130,
                   color=c, edgecolor="black", linewidth=0.7, zorder=3)
        ax.annotate(short(p), (r["cost_per_run_16_usd"], r["f1"]),
                    xytext=(7, 5), textcoords="offset points", fontsize=8.5)

    ax.set_xscale("log")
    ax.set_xlabel("Cost per 16-problem run (USD, log scale)")
    ax.set_ylabel("Routing F1 (mean across 16 problems)")
    ax.set_title("Cost vs routing F1 — provider colors: green=OpenAI, orange=Anthropic, blue=Bedrock, red=Gemini")
    ax.set_ylim(0, 0.6)
    ax.grid(alpha=0.25, which="both")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()

    for out in (OUT_SLIDES, OUT_REPORT):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out + ".pdf", bbox_inches="tight")
        fig.savefig(out + ".png", dpi=160, bbox_inches="tight")
        print(f"wrote {out}.pdf and {out}.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
