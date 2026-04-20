"""Metrics for the silicon-mind-harness eval.

Per problem we record:
  - passed (bool): testbench reported zero mismatches
  - compiled (bool): iverilog accepted the integrated source
  - n_llm_calls (int): planner + each codegen + integrator-stitch call
  - n_ip_reuses (int): how many subblocks resolved to an IP from the corpus
  - n_generated (int): how many subblocks were LLM-written
  - loc_generated (int): LOC across LLM-written modules
  - loc_reused (int): LOC across IP modules pulled from corpus
  - reuse_ratio (float): loc_reused / (loc_reused + loc_generated)

Aggregates into a markdown table for the slide deck.
"""
import json, os, sys
from typing import TypedDict

class ProblemMetrics(TypedDict, total=False):
    problem: str
    passed: bool
    compiled: bool
    n_llm_calls: int
    n_ip_reuses: int
    n_generated: int
    loc_generated: int
    loc_reused: int
    reuse_ratio: float
    api_time_s: float
    error: str

def loc(text: str) -> int:
    return sum(1 for l in text.splitlines() if l.strip() and not l.strip().startswith("//"))

def from_trace(problem: str, trace: dict, sim_result: dict) -> ProblemMetrics:
    """trace is the JSON the harness emits per run; sim_result is the iverilog outcome."""
    n_llm = 1  # planner
    n_ip = 0
    n_gen = 0
    loc_gen = 0
    loc_reu = 0
    for sb in trace.get("subblocks", []):
        kind = sb.get("kind")
        if kind == "ip":
            n_ip += 1
            src = sb.get("source_text", "")
            loc_reu += loc(src)
        elif kind == "gen":
            n_gen += 1
            n_llm += 1
            loc_gen += loc(sb.get("source_text", ""))
    if "topmodule_source" in trace:
        n_llm += 1
        loc_gen += loc(trace["topmodule_source"])
    total = loc_gen + loc_reu
    return {
        "problem": problem,
        "passed": bool(sim_result.get("passed")),
        "compiled": bool(sim_result.get("compiled")),
        "n_llm_calls": n_llm,
        "n_ip_reuses": n_ip,
        "n_generated": n_gen,
        "loc_generated": loc_gen,
        "loc_reused": loc_reu,
        "reuse_ratio": (loc_reu / total) if total else 0.0,
        "api_time_s": float(trace.get("api_time_s", 0.0)),
    }

def render_markdown_table(rows: list[ProblemMetrics]) -> str:
    if not rows:
        return "_(no results yet)_\n"
    cols = ["problem", "passed", "n_llm_calls", "n_ip_reuses", "n_generated", "loc_reused", "loc_generated", "reuse_ratio"]
    head = "| " + " | ".join(cols) + " |"
    sep  = "|" + "|".join("---" for _ in cols) + "|"
    lines = [head, sep]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            if isinstance(v, float):
                cells.append(f"{v:.2f}")
            elif isinstance(v, bool):
                cells.append("✓" if v else "✗")
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"

def aggregate(rows: list[ProblemMetrics]) -> dict:
    if not rows:
        return {}
    n = len(rows)
    return {
        "n_problems": n,
        "pass_rate": sum(r["passed"] for r in rows) / n,
        "compile_rate": sum(r["compiled"] for r in rows) / n,
        "avg_llm_calls": sum(r["n_llm_calls"] for r in rows) / n,
        "avg_reuse_ratio": sum(r["reuse_ratio"] for r in rows) / n,
        "total_ip_reuses": sum(r["n_ip_reuses"] for r in rows),
        "total_generated_modules": sum(r["n_generated"] for r in rows),
    }

def main():
    if len(sys.argv) < 2:
        print("usage: metrics.py <results_dir_with_trace_json_files>")
        sys.exit(1)
    rd = sys.argv[1]
    rows = []
    for fn in sorted(os.listdir(rd)):
        if fn.endswith("_trace.json"):
            with open(os.path.join(rd, fn)) as f:
                payload = json.load(f)
            rows.append(from_trace(payload["problem"], payload["trace"], payload["sim_result"]))
    print(render_markdown_table(rows))
    print("\n## Aggregate\n")
    for k, v in aggregate(rows).items():
        if isinstance(v, float):
            print(f"- **{k}**: {v:.3f}")
        else:
            print(f"- **{k}**: {v}")

if __name__ == "__main__":
    main()
