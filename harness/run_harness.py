"""End-to-end harness CLI.

Usage:
  python -m harness.run_harness <prompt_file> <ref_file> <test_file>

Pipeline: planner -> ip_router (per subblock) -> integrator -> iverilog/vvp.
Writes results/harness/<prob>_combined.sv and a JSON trace alongside it.
"""
import argparse
import json
import os
import subprocess
import sys
import time

from harness import planner, ip_router, integrator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results", "harness")
os.makedirs(RESULTS_DIR, exist_ok=True)


def _prob_tag(prompt_path: str) -> str:
    base = os.path.basename(prompt_path)
    if base.endswith("_prompt.txt"):
        base = base[: -len("_prompt.txt")]
    return base


def _compile_and_run(combined_path: str, tag: str):
    sim_bin = os.path.join(RESULTS_DIR, f"{tag}_sim")
    cr = subprocess.run(
        ["iverilog", "-g2012", "-o", sim_bin, combined_path],
        capture_output=True, text=True, timeout=60,
    )
    if cr.returncode != 0:
        return {"compiled": False, "passed": False,
                "compile_errors": cr.stderr[:1000]}
    sr = subprocess.run(
        ["vvp", sim_bin], capture_output=True, text=True, timeout=120,
        cwd=RESULTS_DIR,
    )
    out = sr.stdout + sr.stderr
    passed = "Mismatches: 0 in" in out
    mline = next((l for l in out.split("\n") if "Mismatches:" in l), "N/A")
    return {"compiled": True, "passed": passed, "mismatch_line": mline,
            "sim_tail": out[-600:]}


def run(prompt_file: str, ref_file: str, test_file: str) -> dict:
    tag = _prob_tag(prompt_file)
    print(f"[harness] === {tag} ===")
    spec = open(prompt_file).read()

    t0 = time.time()
    print("[harness] planner: decomposing spec ...")
    subblocks = planner.decompose(spec)
    plan_time = time.time() - t0
    print(f"[harness] planner produced {len(subblocks)} subblock(s) in {plan_time:.1f}s")
    for sb in subblocks:
        print(f"  - {sb['name']:20s} kind={sb['suggested_kind']:9s} "
              f"query='{sb['search_query']}'")

    t1 = time.time()
    resolved = []
    for sb in subblocks:
        print(f"[harness] resolve: {sb['name']} ({sb['suggested_kind']})")
        try:
            r = ip_router.resolve_subblock(sb)
        except Exception as e:
            print(f"  resolve failed: {e}; treating as gen stub")
            r = {"kind": "gen", "name": sb["name"],
                 "source_text": f"// stub for {sb['name']} (resolve failed)\n"}
        resolved.append(r)
        if r["kind"] == "ip":
            print(f"    -> IP {r['id']} from {r['source_file']}")
        else:
            print(f"    -> GENERATED ({len(r['source_text'])} chars)")
    resolve_time = time.time() - t1

    t2 = time.time()
    print("[harness] integrator: stitching TopModule ...")
    top_only = integrator.integrate(spec, resolved)
    integrate_time = time.time() - t2

    # Append the ref's helper modules + testbench so we can simulate.
    ref_code = open(ref_file).read()
    test_code = open(test_file).read()
    full = (top_only + "\n// === REF (helpers + RefModule) ===\n" + ref_code
            + "\n// === TESTBENCH ===\n" + test_code)

    combined_path = os.path.join(RESULTS_DIR, f"{tag}_combined.sv")
    with open(combined_path, "w") as f:
        f.write(full)
    print(f"[harness] wrote {combined_path}")

    sim = _compile_and_run(combined_path, tag)

    trace = {
        "problem": tag,
        "using_real_mcp": ip_router.using_real_mcp(),
        "timings_sec": {
            "plan": round(plan_time, 1),
            "resolve": round(resolve_time, 1),
            "integrate": round(integrate_time, 1),
        },
        "planner_output": subblocks,
        "subblocks": [
            {
                "name": r.get("name"),
                "kind": r["kind"],
                "ip_id": r.get("id"),
                "source_file": r.get("source_file"),
                "source_chars": (len(r["source_text"])
                                 if r["kind"] == "gen" else None),
            }
            for r in resolved
        ],
        "summary": {
            "n_total": len(resolved),
            "n_reused": sum(1 for r in resolved if r["kind"] == "ip"),
            "n_generated": sum(1 for r in resolved if r["kind"] == "gen"),
        },
        "simulation": sim,
        "combined_path": combined_path,
    }
    trace_path = os.path.join(RESULTS_DIR, f"{tag}_trace.json")
    with open(trace_path, "w") as f:
        json.dump(trace, f, indent=2)

    status = ("PASS" if sim.get("passed") else
              "COMPILE_FAIL" if not sim.get("compiled") else "FAIL")
    print(f"[harness] {tag}: {status}  "
          f"(reused {trace['summary']['n_reused']} / generated "
          f"{trace['summary']['n_generated']})")
    print(f"[harness] trace: {trace_path}")
    return trace


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt_file")
    ap.add_argument("ref_file")
    ap.add_argument("test_file")
    args = ap.parse_args()
    trace = run(args.prompt_file, args.ref_file, args.test_file)
    print("\n=== JSON TRACE ===")
    print(json.dumps(trace, indent=2))
    sys.exit(0 if trace.get("simulation", {}).get("passed") else 1)


if __name__ == "__main__":
    main()
