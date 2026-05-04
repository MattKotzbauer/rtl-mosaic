#!/usr/bin/env python3
"""Build the IEEE final report's leading figure: pipeline schematic on top + headline result on bottom.

Required by the report rubric: a single figure summarizing approach AND results.
"""
import os, sys, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

SUMMARY = os.path.join(ROOT, "results", "multi_routing", "summary.json")
SCRATCH_DIR = os.path.join(ROOT, "results", "multi")
OUT_DIR = os.path.join(os.path.dirname(__file__), "figs")
os.makedirs(OUT_DIR, exist_ok=True)

# 4 headline models (best-of-provider with n=16)
FOCUS = [
    ("openai:gpt-5.2",            "GPT-5.2",            "#10a37f"),
    ("bedrock:deepseek-v3.2",     "DeepSeek V3.2",      "#4d6bfe"),
    ("gemini:2.5-flash-lite",     "Gemini 2.5 Flash-L", "#ea4335"),
    ("claude:opus-4-7",           "Claude Opus 4.7",    "#cc785c"),
]


def short_label(p):
    return p.replace("openai:","").replace("claude:","").replace("bedrock:","").replace("gemini:","")


def load_scratch_pass_rate(p):
    """Return cpu_ip pass rate for provider p, or None if missing."""
    safe = p.replace(":", "_").replace("/", "_")
    path = os.path.join(SCRATCH_DIR, safe, "results.json")
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    cpu = d["by_dataset"]["cpu_ip"]
    return cpu["passed"] / cpu["total"] if cpu["total"] else 0.0


def main():
    agg = json.load(open(SUMMARY))

    fig = plt.figure(figsize=(7.0, 5.4))  # IEEE 2-col page is ~3.4in wide; this is 1-col-spanning
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.5], hspace=0.35)

    # ============================================================
    # Top panel: pipeline schematic
    # ============================================================
    ax = fig.add_subplot(gs[0])
    ax.set_xlim(0, 10); ax.set_ylim(0, 2.4)
    ax.axis("off")

    def block(x, y, w, h, label, color, text_color="black", fs=8):
        b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.08",
                           facecolor=color, edgecolor="black", linewidth=0.7)
        ax.add_patch(b)
        ax.text(x + w/2, y + h/2, label, ha="center", va="center", fontsize=fs, color=text_color)

    def arrow(x1, y1, x2, y2):
        a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=10,
                            color="black", linewidth=0.8)
        ax.add_patch(a)

    # blocks
    block(0.1, 1.0, 1.4, 0.6, "Spec", "#f4f4f4", fs=9)
    block(1.9, 1.0, 1.6, 0.6, "Planner\n(LLM)", "#fff2cc", fs=8)
    block(3.9, 1.5, 1.7, 0.5, "REUSE_IP", "#d9ead3", fs=8)
    block(3.9, 0.5, 1.7, 0.5, "GENERATE", "#fce5cd", fs=8)
    block(6.0, 1.5, 1.5, 0.5, "Router\n(MCP→corpus)", "#cfe2f3", fs=7.5)
    block(6.0, 0.5, 1.5, 0.5, "Codegen\n(LLM)", "#fff2cc", fs=7.5)
    block(8.0, 1.0, 1.4, 0.6, "Integrator\n+ iverilog", "#d9d2e9", fs=7.5)

    # arrows
    arrow(1.5, 1.3, 1.85, 1.3)
    arrow(3.5, 1.3, 3.85, 1.75)
    arrow(3.5, 1.3, 3.85, 0.75)
    arrow(5.6, 1.75, 5.95, 1.75)
    arrow(5.6, 0.75, 5.95, 0.75)
    arrow(7.5, 1.75, 7.95, 1.4)
    arrow(7.5, 0.75, 7.95, 1.2)

    # corpus annotation
    ax.text(6.75, 2.2, "30-IP corpus + 16 hand-labeled gold problems",
            ha="center", va="center", fontsize=7.5, style="italic", color="#444")

    ax.set_title("(a) Per-LLM evaluation pipeline", fontsize=9, loc="left", pad=2)

    # ============================================================
    # Bottom panel: orthogonality scatter (routing F1 vs scratch pass rate)
    # ============================================================
    ax2 = fig.add_subplot(gs[1])

    for p, label, color in FOCUS:
        if p not in agg:
            continue
        f1 = agg[p]["f1_mean"]
        scr = load_scratch_pass_rate(p)
        if scr is None:
            continue
        ax2.scatter(scr, f1, s=160, color=color, edgecolor="black", linewidth=0.8, zorder=3)
        ax2.annotate(label, (scr, f1), xytext=(8, 6), textcoords="offset points", fontsize=8)

    # plot the rest of the LLMs as small grey dots for context
    rest_drawn = False
    for p, m in agg.items():
        if p in [f[0] for f in FOCUS]: continue
        scr = load_scratch_pass_rate(p)
        if scr is None: continue
        ax2.scatter(scr, m["f1_mean"], s=30, color="#bbb", edgecolor="#666", linewidth=0.4, zorder=2,
                    label="Other 11 LLMs" if not rest_drawn else None)
        rest_drawn = True

    ax2.set_xlabel("Scratch pass rate on cpu_ip set (single-shot Verilog → iverilog testbench)", fontsize=8.5)
    ax2.set_ylabel("Routing F1 vs hand-labeled gold (16 problems)", fontsize=8.5)
    ax2.set_xlim(-0.02, 0.5)
    ax2.set_ylim(0, 0.6)
    ax2.tick_params(labelsize=8)
    ax2.grid(alpha=0.25)
    ax2.legend(loc="lower right", fontsize=7.5, frameon=True)

    ax2.set_title("(b) IP-reuse skill is its own axis: 4 frontier providers, no scratch-vs-routing diagonal",
                  fontsize=9, loc="left", pad=2)

    out = os.path.join(OUT_DIR, "leading.pdf")
    fig.savefig(out, bbox_inches="tight"); fig.savefig(out.replace(".pdf",".png"), dpi=200, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
