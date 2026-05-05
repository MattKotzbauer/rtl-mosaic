#!/usr/bin/env python3
"""Build the stacked-bar failure-mode figure from results/multi_routing/failure_modes.json."""
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "results", "multi_routing", "failure_modes.json")
OUT_SLIDES = os.path.join(ROOT, "slides", "figs", "failure_modes")
OUT_REPORT = os.path.join(ROOT, "report", "figs", "failure_modes")
SUMMARY = os.path.join(ROOT, "results", "multi_routing", "summary.json")

MODE_COLORS = {
    "hallucinated_pick":   "#d62728",   # red
    "over_decomposition":  "#ff7f0e",   # orange
    "under_decomposition": "#9467bd",   # purple
    "kind_flip_suspect":   "#17becf",   # teal
}
MODE_LABELS = {
    "hallucinated_pick":   "Hallucinated pick",
    "over_decomposition":  "Over-decomposition",
    "under_decomposition": "Under-decomposition",
    "kind_flip_suspect":   "Kind disagreement (single-seed)",
}


def short_label(p):
    return (p.replace("openai:", "")
             .replace("claude:", "")
             .replace("bedrock:", "")
             .replace("gemini:", ""))


def main():
    d = json.load(open(SRC))
    modes = d["modes"]
    by_p = d["by_provider"]
    agg = json.load(open(SUMMARY))

    # sort by F1 descending so highest-F1 models on top of horizontal bars
    providers = sorted(by_p.keys(), key=lambda p: -agg.get(p, {}).get("f1_mean", 0))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(providers))
    left = np.zeros(len(providers))
    for m in modes:
        vals = np.array([by_p[p][m] for p in providers])
        ax.barh(y, vals, left=left, color=MODE_COLORS[m], edgecolor="black",
                linewidth=0.4, label=MODE_LABELS[m])
        left += vals

    # F1 annotation on right of each bar
    for i, p in enumerate(providers):
        f1 = agg.get(p, {}).get("f1_mean", 0)
        n = by_p[p]["n_problems"]
        ax.text(left[i] + 0.5, i, f"F1={f1:.2f} (n={n})",
                va="center", fontsize=8, color="#444")

    ax.set_yticks(y)
    ax.set_yticklabels([short_label(p) for p in providers], fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Failure-mode incidents (one record can hit multiple modes)")
    ax.set_title("Per-LLM failure-mode counts on 16-problem routing eval (sorted by F1)")
    ax.legend(loc="lower right", fontsize=8.5, framealpha=0.95)
    ax.grid(axis="x", alpha=0.25)
    ax.set_xlim(0, max(left) * 1.30)
    fig.tight_layout()

    for out in (OUT_SLIDES, OUT_REPORT):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        fig.savefig(out + ".pdf", bbox_inches="tight")
        fig.savefig(out + ".png", dpi=160, bbox_inches="tight")
        print(f"wrote {out}.pdf and {out}.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
