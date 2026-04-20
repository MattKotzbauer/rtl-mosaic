"""Routing eval: how well does the planner+ip_router match the gold labels?

For each ChipBench cpu_ip problem we:
  1. Read the prompt.
  2. Run `harness.planner.decompose(prompt)` to get a list of subblocks.
  3. For each subblock, call `harness.ip_router.resolve_subblock(subblock)`.
     - If the router returns kind=="ip", record `picked_ip = result["id"]`.
     - Otherwise record `picked_ip = None` (planner punted to GENERATE, or
       router fell through because no IP matched).
  4. Score against `eval.gold_labels.GOLD[problem]`:
       - precision = correctly-picked IPs / total IPs picked
       - recall    = correctly-picked IPs / GOLD IPs (set-based, deduped)
       - kind_agreement = fraction of *planner subblocks* whose REUSE_IP /
         GENERATE classification agrees with the GOLD-labeled subblock that
         best matches it by name (substring match on snake-case tokens).

Notes:
  - We work over IP-id sets (deduped) because a problem might legitimately use
    e.g. cla_adder twice; we don't want to double-count.
  - "Correctly picked" means the router's chosen id appears in
    `gold.expected_subblocks`. Picks not in gold are still counted in the
    denominator of precision (false positives).
  - One problem failing (e.g. claude CLI hiccup) must not abort the whole run.

Usable both as a pytest test (it exposes `test_routing_eval` which runs all
problems and asserts the JSON file got written) and as a library (call
`run_routing_eval(...)` directly from `run_routing_eval.py`).
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import time
import traceback
from typing import Any

# Make sure the repo root is on sys.path so `import harness.*` works whether
# this is invoked via pytest or `python eval/test_routing.py`.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eval.gold_labels import GOLD, all_problem_ids  # noqa: E402

CHIPBENCH_CPU_IP = os.path.join(
    os.path.dirname(_REPO_ROOT),
    "ChipBench", "Verilog Gen", "dataset_cpu_ip",
)
RESULTS_DIR = os.path.join(_REPO_ROOT, "results", "routing")
RESULTS_JSON = os.path.join(RESULTS_DIR, "eval.json")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _prompt_path(problem_id: str) -> str:
    return os.path.join(CHIPBENCH_CPU_IP, f"{problem_id}_prompt.txt")


def _read_prompt(problem_id: str) -> str:
    with open(_prompt_path(problem_id)) as f:
        return f.read()


_TOK_RE = re.compile(r"[a-z0-9]+")


def _tokens(s: str) -> set[str]:
    return set(_TOK_RE.findall((s or "").lower()))


def _best_gold_kind_for(planner_name: str,
                        expected_kinds: dict[str, str]) -> str | None:
    """Find the gold-label entry in expected_kinds whose name shares the most
    tokens with the planner's subblock name.  Returns None if no overlap
    (caller decides what to do)."""
    if not expected_kinds:
        return None
    pt = _tokens(planner_name)
    if not pt:
        return None
    best, best_overlap = None, 0
    for gold_name, kind in expected_kinds.items():
        gt = _tokens(gold_name)
        overlap = len(pt & gt)
        if overlap > best_overlap:
            best, best_overlap = kind, overlap
    return best


def _score_problem(problem_id: str,
                   planner_blocks: list[dict],
                   router_results: list[dict]) -> dict[str, Any]:
    """Compute precision / recall / kind_agreement for one problem."""
    gold = GOLD[problem_id]
    gold_ips = set(gold["expected_subblocks"])
    expected_kinds = gold["expected_kinds"]

    # IP set the router actually picked (deduped).
    picked_ips = set()
    for r in router_results:
        if r.get("picked_ip"):
            picked_ips.add(r["picked_ip"])

    # precision / recall over IP id sets.
    if picked_ips:
        precision = len(picked_ips & gold_ips) / len(picked_ips)
    else:
        # No IPs picked: precision is undefined; report 1.0 iff gold is also
        # empty (we agreed nothing reusable), else 0.0.
        precision = 1.0 if not gold_ips else 0.0

    if gold_ips:
        recall = len(picked_ips & gold_ips) / len(gold_ips)
    else:
        # No gold IPs: recall is undefined; report 1.0 iff we also picked
        # none, else 0.0 (we hallucinated IPs that don't fit).
        recall = 1.0 if not picked_ips else 0.0

    # kind_agreement: per planner subblock, find the best-matching gold entry
    # by token overlap and check if planner's REUSE_IP/GENERATE agrees.
    n_compared = 0
    n_agreed = 0
    for sb, rr in zip(planner_blocks, router_results):
        # Planner's *intent* (suggested_kind) is what we're really evaluating
        # here, not whether the router actually found a match (that's captured
        # by precision/recall already).
        planner_kind = (sb.get("suggested_kind") or "GENERATE").upper()
        gold_kind = _best_gold_kind_for(sb.get("name", ""), expected_kinds)
        if gold_kind is None:
            # No matching gold entry => skip (can't evaluate).
            continue
        n_compared += 1
        if planner_kind == gold_kind:
            n_agreed += 1
    # If no planner subblock name overlapped with any gold label, we can't
    # evaluate kind agreement -- treat as vacuously satisfied (1.0) rather
    # than penalizing with 0.0.
    kind_agreement = (n_agreed / n_compared) if n_compared else 1.0

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "kind_agreement": round(kind_agreement, 3),
        "n_subblocks_planned": len(planner_blocks),
        "picked_ips": sorted(picked_ips),
        "gold_ips": sorted(gold_ips),
        "n_kind_compared": n_compared,
        "n_kind_agreed": n_agreed,
    }


# ---------------------------------------------------------------------------
# per-problem runner
# ---------------------------------------------------------------------------

def _run_problem(problem_id: str) -> dict[str, Any]:
    """Run planner + router on one problem and return a result dict.

    Always returns a dict; on failure the dict carries an `error` key and the
    score fields are zeroed.
    """
    from harness import planner, ip_router  # local import: lazy + per-thread

    t0 = time.time()
    out: dict[str, Any] = {"problem": problem_id}
    try:
        prompt = _read_prompt(problem_id)
    except FileNotFoundError as e:
        out["error"] = f"prompt not found: {e}"
        out["elapsed_s"] = round(time.time() - t0, 2)
        return out

    try:
        blocks = planner.decompose(prompt)
    except Exception as e:
        out["error"] = f"planner failed: {e}"
        out["traceback"] = traceback.format_exc()[-800:]
        out["elapsed_s"] = round(time.time() - t0, 2)
        return out

    router_records: list[dict[str, Any]] = []
    for sb in blocks:
        rec: dict[str, Any] = {
            "name": sb.get("name"),
            "suggested_kind": (sb.get("suggested_kind") or "GENERATE").upper(),
            "search_query": sb.get("search_query"),
            "picked_ip": None,
            "router_kind": None,
        }
        # We intentionally only run the router for REUSE_IP-suggested blocks.
        # For GENERATE-suggested blocks, calling resolve_subblock would invoke
        # codegen (an LLM call we don't need to evaluate routing).
        if rec["suggested_kind"] == "REUSE_IP":
            try:
                res = ip_router.resolve_subblock(sb)
                rec["router_kind"] = res.get("kind")
                if res.get("kind") == "ip":
                    rec["picked_ip"] = res.get("id")
            except Exception as e:
                rec["router_error"] = str(e)[:200]
        router_records.append(rec)

    score = _score_problem(problem_id, blocks, router_records)
    out["planner_blocks"] = blocks
    out["router_records"] = router_records
    out["score"] = score
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


# ---------------------------------------------------------------------------
# top-level runner
# ---------------------------------------------------------------------------

def run_routing_eval(problem_ids: list[str] | None = None,
                     max_workers: int = 3,
                     write_json: bool = True) -> dict[str, Any]:
    """Run the routing eval on the given problems (default = all 9).

    Returns the aggregate dict that's also written to RESULTS_JSON.
    """
    pids = problem_ids or all_problem_ids()
    bad = [p for p in pids if p not in GOLD]
    if bad:
        raise ValueError(f"unknown problem ids: {bad}")

    print(f"[routing-eval] running {len(pids)} problem(s) with "
          f"{max_workers} worker(s)")
    print("=" * 78)

    results: dict[str, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        fut_to_pid = {ex.submit(_run_problem, p): p for p in pids}
        for fut in concurrent.futures.as_completed(fut_to_pid):
            pid = fut_to_pid[fut]
            try:
                results[pid] = fut.result()
            except Exception as e:
                results[pid] = {
                    "problem": pid,
                    "error": f"future raised: {e}",
                    "traceback": traceback.format_exc()[-800:],
                }
            r = results[pid]
            if "error" in r:
                print(f"  [ERROR     ] {pid}  ({r.get('elapsed_s', '?')}s)  "
                      f"{r['error'][:80]}")
            else:
                s = r["score"]
                print(f"  [OK        ] {pid}  ({r['elapsed_s']}s)  "
                      f"P={s['precision']}  R={s['recall']}  "
                      f"KA={s['kind_agreement']}  "
                      f"n_sub={s['n_subblocks_planned']}  "
                      f"picked={s['picked_ips']}")

    # ----- summary table --------------------------------------------------
    print()
    _print_summary_table(pids, results)

    aggregate = _aggregate(pids, results)
    payload = {
        "per_problem": results,
        "aggregate": aggregate,
        "problems": pids,
    }
    if write_json:
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(RESULTS_JSON, "w") as f:
            json.dump(payload, f, indent=2)
        print(f"\n[routing-eval] wrote {RESULTS_JSON}")
    return payload


def _aggregate(pids: list[str],
               results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    okrows = [results[p]["score"] for p in pids
              if "score" in results[p] and "error" not in results[p]]
    if not okrows:
        return {"n": 0, "n_errors": len(pids)}
    n = len(okrows)
    return {
        "n": n,
        "n_errors": len(pids) - n,
        "avg_precision": round(sum(r["precision"] for r in okrows) / n, 3),
        "avg_recall": round(sum(r["recall"] for r in okrows) / n, 3),
        "avg_kind_agreement": round(
            sum(r["kind_agreement"] for r in okrows) / n, 3),
    }


def _print_summary_table(pids: list[str],
                         results: dict[str, dict[str, Any]]) -> None:
    name_w = max(len("Problem"),
                 max((len(p) for p in pids), default=10))
    cols = ["precision", "recall", "kind_agreement", "n_subblocks_planned"]
    head = f"{'Problem':<{name_w}} | " + " | ".join(
        f"{c:<19}" if c == "n_subblocks_planned" else f"{c:<14}"
        for c in cols
    )
    print(head)
    print("-" * len(head))

    okrows: list[dict[str, Any]] = []
    for pid in pids:
        r = results[pid]
        if "error" in r:
            row_str = f"{pid:<{name_w}} | ERROR ({r['error'][:50]})"
            print(row_str)
            continue
        s = r["score"]
        okrows.append(s)
        cells = [
            f"{s['precision']:<14.2f}",
            f"{s['recall']:<14.2f}",
            f"{s['kind_agreement']:<14.2f}",
            f"{s['n_subblocks_planned']:<19d}",
        ]
        print(f"{pid:<{name_w}} | " + " | ".join(cells))

    if okrows:
        n = len(okrows)
        avg_p = sum(r["precision"] for r in okrows) / n
        avg_r = sum(r["recall"] for r in okrows) / n
        avg_k = sum(r["kind_agreement"] for r in okrows) / n
        print("-" * len(head))
        cells = [
            f"{avg_p:<14.2f}",
            f"{avg_r:<14.2f}",
            f"{avg_k:<14.2f}",
            f"{'-':<19}",
        ]
        print(f"{'AVERAGE':<{name_w}} | " + " | ".join(cells))


# ---------------------------------------------------------------------------
# pytest entry point
# ---------------------------------------------------------------------------

def test_routing_eval():
    """Runs the full routing eval. This costs N LLM calls (one per problem)."""
    payload = run_routing_eval()
    assert os.path.exists(RESULTS_JSON), "results JSON wasn't written"
    assert payload["aggregate"]["n"] >= 1, "no problems scored successfully"


if __name__ == "__main__":
    run_routing_eval()
