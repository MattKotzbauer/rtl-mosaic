#!/usr/bin/env python3
"""Build presentation figures from results/multi_routing/* and results/multi/*."""
import os, sys, json, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTING_DIR = os.path.join(ROOT, "results", "multi_routing")
SCRATCH_DIR = os.path.join(ROOT, "results", "multi")
FIG_DIR = os.path.join(ROOT, "slides", "figs")
os.makedirs(FIG_DIR, exist_ok=True)


def label(p):
    return (p.replace("openai:", "")
             .replace("claude:", "")
             .replace("bedrock:", "")
             .replace("deepseek-", "ds-"))


def color(p):
    if p.startswith("openai"):  return "#10a37f"
    if p.startswith("claude"):  return "#cc785c"
    if p.startswith("bedrock"): return "#4d6bfe"
    return "#888"


def provider_group(p):
    if p.startswith("openai"):  return "OpenAI"
    if p.startswith("claude"):  return "Anthropic"
    if p.startswith("bedrock"): return "Bedrock (DeepSeek)"
    return "?"


def load_summary():
    p = os.path.join(ROUTING_DIR, "summary.json")
    return json.load(open(p)) if os.path.exists(p) else {}


def load_per_provider():
    out = {}
    for f in glob.glob(os.path.join(ROUTING_DIR, "*.json")):
        if f.endswith("summary.json"):
            continue
        d = json.load(open(f))
        # provider key is on first record
        for v in d.values():
            out[v["provider"]] = d
            break
    return out


def load_scratch():
    out = {}
    for d in glob.glob(os.path.join(SCRATCH_DIR, "*", "results.json")):
        r = json.load(open(d))
        p = r.get("provider", os.path.basename(os.path.dirname(d)))
        out[p] = r
    return out


def save(fig, name):
    out = os.path.join(FIG_DIR, name)
    fig.savefig(out + ".pdf"); fig.savefig(out + ".png", dpi=150)
    plt.close(fig)
    print(f"wrote {out}.{{pdf,png}}")


# ---------------------------------------------------------------------------
# Figure 1: P / R / F1 grouped bars (sorted by F1)
# ---------------------------------------------------------------------------
def fig_routing_f1(agg):
    items = sorted(agg.items(), key=lambda kv: -kv[1]["f1_mean"])
    labels = [label(p) for p, _ in items]
    p_  = [m["precision_mean"] for _, m in items]
    r_  = [m["recall_mean"]    for _, m in items]
    f1  = [m["f1_mean"]        for _, m in items]
    cols = [color(p) for p, _ in items]
    x = np.arange(len(labels)); w = 0.27
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.bar(x - w, p_, w, label="Precision", color=cols, alpha=0.55)
    ax.bar(x,     r_, w, label="Recall",    color=cols, alpha=0.78)
    ax.bar(x + w, f1, w, label="F1",        color=cols, edgecolor="black", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Score (mean over 9 cpu_ip problems)")
    ax.set_ylim(0, 1.02)
    ax.set_title("IP routing quality by LLM (planner+router vs hand-labeled gold)")
    ax.legend(loc="upper right", fontsize=9, ncols=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "routing_f1")


# ---------------------------------------------------------------------------
# Figure 2: Per-problem F1 heatmap (provider x problem)
# ---------------------------------------------------------------------------
def fig_routing_heatmap(per_prov):
    if not per_prov:
        return
    providers = sorted(per_prov.keys(), key=lambda p: -np.mean([
        per_prov[p][q]["score"]["precision"] + per_prov[p][q]["score"]["recall"]
        for q in per_prov[p] if "score" in per_prov[p][q]
    ]))
    problems = sorted({q for d in per_prov.values() for q in d.keys()})
    M = np.full((len(providers), len(problems)), np.nan)
    for i, p in enumerate(providers):
        for j, q in enumerate(problems):
            r = per_prov[p].get(q)
            if r and "score" in r:
                pr, rc = r["score"]["precision"], r["score"]["recall"]
                f1 = 2 * pr * rc / (pr + rc) if (pr + rc) > 0 else 0.0
                M[i, j] = f1
    fig, ax = plt.subplots(figsize=(11, 4.5))
    im = ax.imshow(M, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1.0)
    ax.set_yticks(range(len(providers))); ax.set_yticklabels([label(p) for p in providers], fontsize=9)
    ax.set_xticks(range(len(problems))); ax.set_xticklabels(
        [q.replace("Prob", "P").replace("_", " ").split()[0] + " " + " ".join(q.split("_")[1:])[:14]
         for q in problems], rotation=30, ha="right", fontsize=8)
    for i in range(len(providers)):
        for j in range(len(problems)):
            v = M[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if v < 0.4 or v > 0.85 else "black")
    ax.set_title("Per-problem routing F1 (rows = LLM, cols = cpu_ip problem)")
    fig.colorbar(im, ax=ax, label="F1", shrink=0.7)
    fig.tight_layout()
    save(fig, "routing_heatmap")


# ---------------------------------------------------------------------------
# Figure 3: Decomposition behavior (avg subblocks + REUSE_IP rate)
# ---------------------------------------------------------------------------
def fig_decomposition(per_prov):
    if not per_prov:
        return
    rows = []
    for p, prob_d in per_prov.items():
        ns, n_reuse, n_total = [], 0, 0
        for r in prob_d.values():
            blocks = r.get("planner_blocks", [])
            ns.append(len(blocks))
            n_reuse += sum(1 for b in blocks if b.get("suggested_kind") == "REUSE_IP")
            n_total += len(blocks)
        rows.append((p, np.mean(ns), n_reuse / n_total if n_total else 0.0))
    rows.sort(key=lambda r: -r[2])
    labels = [label(r[0]) for r in rows]
    sub_avg = [r[1] for r in rows]
    reuse_pct = [r[2] for r in rows]
    cols = [color(r[0]) for r in rows]
    x = np.arange(len(labels))
    fig, ax1 = plt.subplots(figsize=(11, 4.5))
    ax1.bar(x - 0.2, sub_avg, 0.4, color=cols, alpha=0.55, label="Avg subblocks per problem")
    ax1.set_ylabel("Avg subblocks per problem", color="#444")
    ax1.set_xticks(x); ax1.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax1.set_ylim(0, max(sub_avg) * 1.3)
    ax2 = ax1.twinx()
    ax2.bar(x + 0.2, reuse_pct, 0.4, color=cols, edgecolor="black", linewidth=0.5,
            label="% of subblocks marked REUSE_IP")
    ax2.set_ylabel("% subblocks marked REUSE_IP", color="#444")
    ax2.set_ylim(0, 1.0)
    ax1.set_title("Planner decomposition behavior by LLM")
    ax1.grid(axis="y", alpha=0.2)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8.5)
    fig.tight_layout()
    save(fig, "decomposition")


# ---------------------------------------------------------------------------
# Figure 4: Per-problem difficulty (avg F1 across LLMs)
# ---------------------------------------------------------------------------
def fig_problem_difficulty(per_prov):
    if not per_prov:
        return
    problems = sorted({q for d in per_prov.values() for q in d.keys()})
    avg_f1, gold_count = [], []
    for q in problems:
        f1s = []
        for d in per_prov.values():
            r = d.get(q)
            if r and "score" in r:
                pr, rc = r["score"]["precision"], r["score"]["recall"]
                f1s.append(2 * pr * rc / (pr + rc) if (pr + rc) > 0 else 0.0)
        avg_f1.append(np.mean(f1s) if f1s else 0.0)
        # gold-IP count from any non-error record
        gc = 0
        for d in per_prov.values():
            r = d.get(q)
            if r and "score" in r:
                gc = len(r["score"]["gold_ips"]); break
        gold_count.append(gc)
    order = np.argsort(avg_f1)
    labels = [problems[i].replace("Prob", "P").split("_")[0] + " " +
              "_".join(problems[i].split("_")[1:])[:18] for i in order]
    sorted_f1 = [avg_f1[i] for i in order]
    sorted_gold = [gold_count[i] for i in order]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.barh(range(len(labels)), sorted_f1, color="#888")
    for i, (b, g) in enumerate(zip(bars, sorted_gold)):
        ax.text(b.get_width() + 0.01, i, f"gold={g}", va="center", fontsize=8, color="#333")
    ax.set_yticks(range(len(labels))); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Mean F1 across 10 LLMs")
    ax.set_xlim(0, 1.05)
    ax.set_title("Per-problem routing difficulty (cpu_ip set)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save(fig, "problem_difficulty")


# ---------------------------------------------------------------------------
# Figure 5: Picked-IP frequency (which IPs the corpus actually surfaces)
# ---------------------------------------------------------------------------
def fig_ip_frequency(per_prov):
    if not per_prov:
        return
    from collections import Counter
    counts = Counter()
    by_provider = {}  # ip -> {provider: n}
    gold_ips = set()
    for d in per_prov.values():
        for r in d.values():
            if "router_records" not in r:
                continue
            p = r["provider"]
            for rec in r["router_records"]:
                ip = rec.get("picked_ip")
                if ip:
                    counts[ip] += 1
                    by_provider.setdefault(ip, {}).setdefault(p, 0)
                    by_provider[ip][p] += 1
            if "score" in r:
                gold_ips.update(r["score"].get("gold_ips", []))
    if not counts:
        return
    items = counts.most_common()
    ips = [i for i, _ in items]
    n = [c for _, c in items]
    in_gold = ["#2a9d8f" if i in gold_ips else "#e76f51" for i in ips]
    fig, ax = plt.subplots(figsize=(9, max(3, len(ips) * 0.32)))
    ax.barh(range(len(ips)), n, color=in_gold)
    ax.set_yticks(range(len(ips))); ax.set_yticklabels(ips, fontsize=9)
    ax.set_xlabel("Times picked across all (LLM, problem) runs")
    ax.invert_yaxis()
    ax.set_title("Which IPs got picked? (green = also in gold; red = mis-routes)")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save(fig, "ip_frequency")


# ---------------------------------------------------------------------------
# Figure 6: Provider rollup (means by provider family)
# ---------------------------------------------------------------------------
def fig_provider_rollup(agg):
    by_g = {}
    for p, m in agg.items():
        by_g.setdefault(provider_group(p), []).append(m["f1_mean"])
    groups = sorted(by_g.keys())
    means = [np.mean(by_g[g]) for g in groups]
    stds  = [np.std(by_g[g])  for g in groups]
    counts = [len(by_g[g])   for g in groups]
    cols = ["#10a37f" if g == "OpenAI" else ("#cc785c" if g == "Anthropic" else "#4d6bfe") for g in groups]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars = ax.bar(groups, means, yerr=stds, capsize=6, color=cols, edgecolor="black", linewidth=0.5)
    for b, m, n in zip(bars, means, counts):
        ax.text(b.get_x() + b.get_width()/2, m + 0.02, f"{m:.2f}\nn={n}",
                ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Mean routing F1 (± std across models)")
    ax.set_title("Provider rollup: routing F1")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "provider_rollup")


# ---------------------------------------------------------------------------
# Figure 7: kind_agreement vs F1 scatter
# ---------------------------------------------------------------------------
def fig_kind_vs_f1(agg):
    fig, ax = plt.subplots(figsize=(7, 5))
    for p, m in agg.items():
        c = color(p)
        ax.scatter(m["kind_agreement_mean"], m["f1_mean"], s=130,
                   color=c, edgecolor="black", linewidth=0.7, zorder=3)
        ax.annotate(label(p), (m["kind_agreement_mean"], m["f1_mean"]),
                    xytext=(6, 4), textcoords="offset points", fontsize=8.5)
    ax.set_xlabel("Kind agreement (REUSE_IP vs GENERATE matches gold)")
    ax.set_ylabel("Routing F1")
    ax.set_xlim(0.5, 1.05)
    ax.set_ylim(0, 0.85)
    ax.grid(alpha=0.25)
    ax.set_title("Knowing when to reuse ≠ picking the right IP")
    fig.tight_layout()
    save(fig, "kind_vs_f1")


# ---------------------------------------------------------------------------
# Figure 8: latency / throughput
# ---------------------------------------------------------------------------
def fig_latency(per_prov):
    if not per_prov:
        return
    rows = []
    for p, d in per_prov.items():
        times = [r.get("elapsed_s") for r in d.values() if r.get("elapsed_s")]
        if times:
            rows.append((p, np.mean(times), np.std(times)))
    rows.sort(key=lambda r: r[1])
    labels = [label(r[0]) for r in rows]
    means = [r[1] for r in rows]
    stds  = [r[2] for r in rows]
    cols  = [color(r[0]) for r in rows]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(range(len(labels)), means, yerr=stds, capsize=4, color=cols, edgecolor="black", linewidth=0.5)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Seconds per problem (mean ± std)")
    ax.set_title("Planner latency by LLM (single API call per cpu_ip problem)")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "latency")


# ---------------------------------------------------------------------------
# Figure 9: scratch baseline (foil)
# ---------------------------------------------------------------------------
def fig_scratch(scr):
    if not scr:
        return
    rows = []
    for p, r in scr.items():
        b = r["by_dataset"]
        rows.append({
            "p": p,
            "nsc": b["not_self_contain"]["passed"] / b["not_self_contain"]["total"],
            "cpu": b["cpu_ip"]["passed"] / b["cpu_ip"]["total"],
        })
    rows.sort(key=lambda r: -(r["nsc"] + r["cpu"]))
    labels = [label(r["p"]) for r in rows]
    nsc = [r["nsc"] for r in rows]
    cpu = [r["cpu"] for r in rows]
    cols = [color(r["p"]) for r in rows]
    x = np.arange(len(labels)); w = 0.36
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(x - w/2, nsc, w, label="not_self_contain (n=6)", color=cols, alpha=0.55)
    ax.bar(x + w/2, cpu, w, label="cpu_ip (n=9)", color=cols, edgecolor="black", linewidth=0.5)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Pass rate (Icarus testbench)")
    ax.set_ylim(0, 1.0)
    ax.set_title("Scratch baseline: single-shot Verilog generation by LLM")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save(fig, "scratch_baseline")


# ---------------------------------------------------------------------------
# Figure 10: routing F1 vs scratch cpu_ip pass rate scatter
# ---------------------------------------------------------------------------
def fig_routing_vs_scratch(agg, scr):
    common = sorted(set(agg.keys()) & set(scr.keys()), key=lambda p: -agg[p]["f1_mean"])
    if not common:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    for p in common:
        c = color(p)
        x_ = scr[p]["by_dataset"]["cpu_ip"]["passed"] / scr[p]["by_dataset"]["cpu_ip"]["total"]
        y_ = agg[p]["f1_mean"]
        ax.scatter(x_, y_, s=130, color=c, edgecolor="black", linewidth=0.7, zorder=3)
        ax.annotate(label(p), (x_, y_), xytext=(6, 4), textcoords="offset points", fontsize=8.5)
    ax.set_xlabel("Scratch pass rate on cpu_ip")
    ax.set_ylabel("Routing F1 (planner+router vs gold)")
    ax.set_xlim(-0.02, 0.5)
    ax.set_ylim(0, 0.85)
    ax.grid(alpha=0.25)
    ax.set_title("Routing skill is not a function of scratch coding skill")
    fig.tight_layout()
    save(fig, "routing_vs_scratch")


if __name__ == "__main__":
    agg = load_summary()
    per_prov = load_per_provider()
    scr = load_scratch()
    print(f"agg providers: {len(agg)}; per-provider files: {len(per_prov)}; scratch: {len(scr)}")
    if agg:
        fig_routing_f1(agg)
        fig_provider_rollup(agg)
        fig_kind_vs_f1(agg)
    if per_prov:
        fig_routing_heatmap(per_prov)
        fig_decomposition(per_prov)
        fig_problem_difficulty(per_prov)
        fig_ip_frequency(per_prov)
        fig_latency(per_prov)
    if scr:
        fig_scratch(scr)
    if agg and scr:
        fig_routing_vs_scratch(agg, scr)
