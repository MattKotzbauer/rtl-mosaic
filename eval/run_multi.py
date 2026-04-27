#!/usr/bin/env python3
"""Run baseline (single-shot) on a list of providers x 15 ChipBench problems.

Usage:
  python eval/run_multi.py <provider_key>            # one model
  python eval/run_multi.py --all                     # all PROVIDERS in parallel processes
"""
import os, sys, json, time, subprocess, concurrent.futures, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from eval.providers import call, PROVIDERS

CHIPBENCH = os.path.join(os.path.dirname(ROOT), "ChipBench", "Verilog Gen")
RESULTS_DIR = os.path.join(ROOT, "results", "multi")
os.makedirs(RESULTS_DIR, exist_ok=True)

DATASETS = {
    "not_self_contain": os.path.join(CHIPBENCH, "dataset_not_self_contain"),
    "cpu_ip": os.path.join(CHIPBENCH, "dataset_cpu_ip"),
}


def collect(d):
    out = {}
    for f in sorted(os.listdir(d)):
        if f.endswith("_prompt.txt"):
            p = f.replace("_prompt.txt", "")
            out[p] = {
                "prompt": os.path.join(d, f),
                "ref":    os.path.join(d, p + "_ref.sv"),
                "test":   os.path.join(d, p + "_test.sv"),
            }
    return out


def extract(text):
    # Strip markdown fences if present
    lines, out, infence = text.strip().split("\n"), [], False
    for ln in lines:
        if ln.strip().startswith("```"):
            infence = not infence
            continue
        out.append(ln)
    return "\n".join(out)


def evaluate(tag, gen, ref_p, test_p, work):
    os.makedirs(work, exist_ok=True)
    gen_f = os.path.join(work, f"{tag}_gen.sv")
    open(gen_f, "w").write(gen)
    combined = os.path.join(work, f"{tag}_combined.sv")
    open(combined, "w").write(gen + "\n\n" + open(ref_p).read() + "\n\n" + open(test_p).read())
    sim = os.path.join(work, f"{tag}_sim")
    cr = subprocess.run(["iverilog", "-g2012", "-o", sim, combined],
                        capture_output=True, text=True, timeout=30)
    if cr.returncode != 0:
        return {"compiled": False, "passed": False, "err": cr.stderr[:300]}
    sr = subprocess.run(["vvp", sim], capture_output=True, text=True, timeout=60, cwd=work)
    out = sr.stdout + sr.stderr
    return {
        "compiled": True,
        "passed": "Mismatches: 0 in" in out,
        "mismatch_line": next((l for l in out.split("\n") if "Mismatches:" in l), "N/A"),
    }


def run_one(provider_key, dataset, name, paths, work):
    tag = f"{dataset}__{name}"
    prompt = open(paths["prompt"]).read()
    t0 = time.time()
    try:
        raw = call(provider_key, prompt, timeout=300)
    except Exception as e:
        return tag, {"compiled": False, "passed": False, "err": f"API: {e}"[:300], "api_time": time.time()-t0}
    api_time = time.time() - t0
    gen = extract(raw)
    try:
        res = evaluate(tag, gen, paths["ref"], paths["test"], work)
    except subprocess.TimeoutExpired as e:
        res = {"compiled": True, "passed": False, "err": f"sim_timeout: {e.cmd[-1][-60:]}"}
    except Exception as e:
        res = {"compiled": False, "passed": False, "err": f"eval: {type(e).__name__}: {e}"[:300]}
    res["api_time"] = api_time
    return tag, res


def run_provider(provider_key, max_workers=4):
    safe = provider_key.replace(":", "_").replace("/", "_")
    work = os.path.join(RESULTS_DIR, safe)
    os.makedirs(work, exist_ok=True)
    out_path = os.path.join(work, "results.json")

    todo = []
    for ds, ddir in DATASETS.items():
        for name, paths in collect(ddir).items():
            todo.append((ds, name, paths))

    print(f"[{provider_key}] starting {len(todo)} problems", flush=True)
    per = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_one, provider_key, ds, name, p, work): (ds, name) for ds, name, p in todo}
        for fut in concurrent.futures.as_completed(futs):
            tag, res = fut.result()
            per[tag] = res
            mark = "PASS" if res["passed"] else ("CFAIL" if not res.get("compiled") else "SIM_FAIL")
            print(f"[{provider_key}] {mark:8s} {tag}", flush=True)

    summary = {"by_dataset": {}, "per_problem": per, "provider": provider_key}
    for ds in DATASETS:
        items = [(k, v) for k, v in per.items() if k.startswith(ds + "__")]
        summary["by_dataset"][ds] = {
            "total": len(items),
            "compiled": sum(1 for _, v in items if v.get("compiled")),
            "passed": sum(1 for _, v in items if v.get("passed")),
        }
    json.dump(summary, open(out_path, "w"), indent=2)
    print(f"[{provider_key}] DONE  {summary['by_dataset']}  -> {out_path}", flush=True)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.all:
        # Run each provider as its own process for true parallelism + isolation
        procs = []
        for k in PROVIDERS:
            p = subprocess.Popen([sys.executable, __file__, k, "--workers", str(args.workers)],
                                 stdout=open(os.path.join(RESULTS_DIR, f"{k.replace(':','_')}.log"), "w"),
                                 stderr=subprocess.STDOUT)
            procs.append((k, p))
            print(f"launched {k} pid={p.pid}")
        for k, p in procs:
            p.wait()
            print(f"finished {k} rc={p.returncode}")
    else:
        run_provider(args.provider, max_workers=args.workers)
