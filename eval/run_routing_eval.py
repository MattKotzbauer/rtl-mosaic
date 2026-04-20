#!/usr/bin/env python3
"""CLI driver for the routing eval.

Examples:
    # full sweep over all 9 ChipBench cpu_ip problems
    python eval/run_routing_eval.py

    # smoke test on one problem
    python eval/run_routing_eval.py --problems Prob001_controller

    # a couple of problems, sequentially
    python eval/run_routing_eval.py --problems Prob001_controller Prob002_alu \\
            --workers 1
"""
from __future__ import annotations

import argparse
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from eval.gold_labels import all_problem_ids  # noqa: E402
from eval.test_routing import run_routing_eval  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--problems", nargs="+", default=None,
        help="problem ids to run (default: all 9 cpu_ip problems)",
    )
    ap.add_argument(
        "--workers", type=int, default=3,
        help="ThreadPoolExecutor parallelism (default 3)",
    )
    ap.add_argument(
        "--no-write", action="store_true",
        help="don't write results/routing/eval.json (useful for smoke tests)",
    )
    args = ap.parse_args()

    pids = args.problems or all_problem_ids()
    payload = run_routing_eval(
        problem_ids=pids,
        max_workers=args.workers,
        write_json=not args.no_write,
    )
    return 0 if payload["aggregate"].get("n", 0) >= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
