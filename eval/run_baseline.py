#!/usr/bin/env python3
"""Naive ChipBench baseline: single-shot Claude on each problem, evaluate w/ iverilog.

Runs on both `not_self_contain` (hierarchical) and `cpu_ip` (RISC-V IP) datasets.
"""
import subprocess, os, sys, json, time, concurrent.futures, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHIPBENCH = os.path.join(os.path.dirname(ROOT), "ChipBench", "Verilog Gen")
RESULTS_DIR = os.path.join(ROOT, "results", "baseline")
os.makedirs(RESULTS_DIR, exist_ok=True)

DATASETS = {
    "not_self_contain": os.path.join(CHIPBENCH, "dataset_not_self_contain"),
    "cpu_ip": os.path.join(CHIPBENCH, "dataset_cpu_ip"),
}

SYSTEM = (
    "You are a hardware design expert. Generate synthesizable Verilog code. "
    "Output ONLY the Verilog code, no markdown fences, no explanation. "
    "The module MUST be named TopModule."
)

def collect(dataset_dir):
    out = {}
    for f in sorted(os.listdir(dataset_dir)):
        if f.endswith("_prompt.txt"):
            prefix = f.replace("_prompt.txt", "")
            out[prefix] = {
                "prompt": os.path.join(dataset_dir, f),
                "ref": os.path.join(dataset_dir, prefix + "_ref.sv"),
                "test": os.path.join(dataset_dir, prefix + "_test.sv"),
            }
    return out

def call_claude(prompt_text, model="claude-sonnet-4-6", max_turns=3, timeout=300):
    full = SYSTEM + "\n\n" + prompt_text
    result = subprocess.run(
        ["claude", "-p", full, "--model", model, "--max-turns", str(max_turns)],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {result.stderr[:200]}")
    return result.stdout

def extract_verilog(response):
    lines = response.strip().split("\n")
    cleaned, in_code = [], False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        cleaned.append(line)
    return "\n".join(cleaned)

def evaluate(tag, generated, ref_path, test_path, out_dir):
    gen_file = os.path.join(out_dir, f"{tag}_gen.sv")
    with open(gen_file, "w") as f:
        f.write(generated)
    ref_code = open(ref_path).read()
    test_code = open(test_path).read()
    combined = os.path.join(out_dir, f"{tag}_combined.sv")
    with open(combined, "w") as f:
        f.write(generated + "\n\n" + ref_code + "\n\n" + test_code)
    sim_bin = os.path.join(out_dir, f"{tag}_sim")
    cr = subprocess.run(
        ["iverilog", "-g2012", "-o", sim_bin, combined],
        capture_output=True, text=True, timeout=30,
    )
    if cr.returncode != 0:
        return {"compiled": False, "passed": False, "compile_errors": cr.stderr[:500]}
    sr = subprocess.run(["vvp", sim_bin], capture_output=True, text=True, timeout=60, cwd=out_dir)
    out = sr.stdout + sr.stderr
    passed = "Mismatches: 0 in" in out
    mline = next((l for l in out.split("\n") if "Mismatches:" in l), "N/A")
    return {"compiled": True, "passed": passed, "mismatch_line": mline, "sim_output": out[-400:]}

def run_one(dataset, name, paths):
    tag = f"{dataset}__{name}"
    out_dir = os.path.join(RESULTS_DIR, dataset)
    os.makedirs(out_dir, exist_ok=True)
    prompt_text = open(paths["prompt"]).read()
    t0 = time.time()
    try:
        resp = call_claude(prompt_text)
    except Exception as e:
        return tag, {"error": str(e)[:300], "stage": "llm"}
    elapsed = time.time() - t0
    code = extract_verilog(resp)
    try:
        r = evaluate(name, code, paths["ref"], paths["test"], out_dir)
    except Exception as e:
        r = {"error": f"eval: {e}"[:300], "stage": "eval"}
    r["api_time"] = round(elapsed, 1)
    status = "PASS" if r.get("passed") else ("COMPILE_FAIL" if not r.get("compiled", True) else "FAIL")
    print(f"  [{status:12s}] {tag}  ({elapsed:.0f}s)")
    return tag, r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--datasets", nargs="+", default=list(DATASETS.keys()))
    args = ap.parse_args()

    jobs = []
    for ds in args.datasets:
        for name, paths in collect(DATASETS[ds]).items():
            jobs.append((ds, name, paths))
    print(f"Running {len(jobs)} problems across {len(args.datasets)} datasets, {args.workers} workers")
    print("=" * 70)

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_one, *j): j for j in jobs}
        for f in concurrent.futures.as_completed(futs):
            tag, r = f.result()
            results[tag] = r

    by_ds = {ds: {"total": 0, "compiled": 0, "passed": 0} for ds in args.datasets}
    for tag, r in results.items():
        ds = tag.split("__", 1)[0]
        by_ds[ds]["total"] += 1
        if r.get("compiled"): by_ds[ds]["compiled"] += 1
        if r.get("passed"): by_ds[ds]["passed"] += 1

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for ds, s in by_ds.items():
        pct = 100 * s["passed"] / s["total"] if s["total"] else 0
        print(f"  {ds:25s}  passed {s['passed']}/{s['total']}  ({pct:.1f}%)  compiled {s['compiled']}/{s['total']}")

    out = os.path.join(RESULTS_DIR, "results.json")
    with open(out, "w") as f:
        json.dump({"by_dataset": by_ds, "per_problem": results}, f, indent=2)
    print(f"\nSaved {out}")

if __name__ == "__main__":
    main()
