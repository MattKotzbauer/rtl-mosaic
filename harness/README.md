# SiliconMind Harness (system-level pipeline)

Decomposes a Verilog spec into subblocks, resolves each one to either a
reused IP (via MCP) or a freshly generated module (via Claude), then stitches
them into a single `TopModule` and verifies with Icarus Verilog.

```
   spec_prompt
       |
       v
   planner.py        (Claude -> JSON list of subblocks)
       |
       v
   ip_router.py      (per subblock: REUSE_IP via mcp.server | GENERATE via codegen)
       |
       v
   integrator.py     (cat IP sources + gen sources + LLM-stitched TopModule)
       |
       v
   run_harness.py    (iverilog -g2012, vvp, JSON trace)
```

## Run

```
python -m harness.run_harness \
    "/path/to/Prob004_synchronous_FIFO_prompt.txt" \
    "/path/to/Prob004_synchronous_FIFO_ref.sv" \
    "/path/to/Prob004_synchronous_FIFO_test.sv"
```

Outputs land in `results/harness/<prob>_combined.sv` and
`results/harness/<prob>_trace.json`.

## JSON trace fields

- `problem`              short tag (e.g. `Prob004_synchronous_FIFO`)
- `using_real_mcp`       true if `mcp.server` was importable, else stub
- `timings_sec`          plan / resolve / integrate wall time
- `planner_output`       raw subblocks the planner produced
- `subblocks`            resolved subblocks (kind = `ip` or `gen`, ids, paths)
- `summary`              counts of reused vs generated
- `simulation`           `compiled`, `passed`, mismatch line, sim tail
- `combined_path`        path to the assembled Verilog file
