# rtl-mosaic

A system-level RTL design harness on top of [SiliconMind-V1](https://arxiv.org/abs/2603.08719).

**CS 1440R Team 11** (Spring 2026, Harvard, HT Kung) — Leonardo Ferreira, Matt Kotzbauer, Warren Zhu

## What it does

Takes a chip-design spec (e.g. *"design a 16-bit CPU with these instructions…"*),
decomposes it into subblocks via an LLM planner, and resolves each subblock to
**either** an off-the-shelf IP module from a curated corpus **or** a freshly
LLM-generated module. Stitches them into one `TopModule` and verifies against
an Icarus Verilog testbench.

```
spec  →  Planner (LLM)  →  per-subblock router  →  Integrator  →  iverilog
                            │                       │
                            ├─ REUSE_IP via MCP    │
                            └─ GENERATE via LLM    │
```

Built to extend SiliconMind-V1 (which generates one module at a time) to
*systems* of modules, where the win comes from reusing known-good IP rather
than regenerating every primitive.

## Layout

| Dir | What |
|---|---|
| `mcp/`      | IP-search MCP server + 5 mock IPs (sync/async FIFO, mux4, regfile, up_counter) |
| `harness/`  | Planner, codegen, IP router, integrator, end-to-end CLI |
| `eval/`     | Baseline runner, metrics module |
| `docs/`     | Architecture diagram, 52-module IP corpus plan |
| `slides/`   | Intermediate presentation (Marp markdown + PDF) |
| `results/`  | Run outputs (gitignored) |

## Run

```bash
# baseline (single-shot Claude on each ChipBench problem)
python eval/run_baseline.py --datasets not_self_contain cpu_ip

# end-to-end harness on one problem
python -m harness.run_harness \
    /path/to/Prob004_synchronous_FIFO_prompt.txt \
    /path/to/Prob004_synchronous_FIFO_ref.sv \
    /path/to/Prob004_synchronous_FIFO_test.sv

# MCP smoke tests
python -m pytest mcp/test_mcp.py -v
```

Requires `iverilog -g2012` and the `claude` CLI on `PATH`.

## Status (2026-04-19)

| Component | Status |
|---|---|
| ChipBench dataset + Icarus eval | ✓ working |
| MCP server with 5 mock IPs | ✓ all tests green |
| Planner / codegen / integrator | ✓ end-to-end demo on Prob004 + Prob006 |
| Baseline measured | ✓ 4/15 = 27% on hierarchical + cpu_ip |
| Real IP corpus (~50 modules) | planned, not yet ingested |
| Test-feedback loop | planned |

## Baseline numbers

Single-shot Claude Sonnet 4.6 + iverilog testbench:

| Tier | Pass rate |
|---|---|
| `not_self_contain` (hierarchical) | 3/6 = **50%** |
| `cpu_ip` (RISC-V IP blocks) | 1/9 = **11%** |
| combined | 4/15 = **27%** |

The 50% → 11% drop is the gap the harness has to close.
