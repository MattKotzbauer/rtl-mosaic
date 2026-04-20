<!--
marp: true
theme: default
paginate: true
size: 16:9
header: "CS 1440R · Team 11 · Intermediate Presentation"
footer: "Leonardo Ferreira · Matt Kotzbauer · Warren Zhu"
-->

# rtl-mosaic
### A system-level RTL harness on top of SiliconMind-V1

**Team 11** — Leonardo Ferreira · Matt Kotzbauer · Warren Zhu
Intermediate Presentation · 2026-04-20

`github.com/MattKotzbauer/rtl-mosaic`

---

## What HT asked for

> "Build on top of previous work like Silicon Mind V1. Design a harness that
> takes a complex task, breaks it into pieces, uses LLM to generate code
> where we need bespoke generation, and uses off-the-shelf components
> elsewhere. Evaluate this."
> — HT, after our 4/13 meeting

Two new things vs SiliconMind:
1. **Decomposition** — go from one module to a *system* of modules
2. **Reuse** — pull from a corpus of ~50 known-good IP blocks instead of regenerating every primitive

---

## Why this matters: the gap SiliconMind doesn't fill

SiliconMind-V1 generates **one module at a time** very well (verified via Icarus testbench on 36K examples).

But real chip design is **hierarchical**: a CPU is a controller + ALU + register file + branch unit + … and most of those are off-the-shelf in industry.

A pure codegen model has to re-invent every primitive every time. We want the model to act more like a designer: *decompose, reach for known-good IP first, only generate what's actually new.*

---

## How we're different from prior work

<style scoped>
table { font-size: 0.78em; }
</style>

| Axis | SiliconMind-V1 | SOTA agentic Verilog | **Us** |
|---|---|---|---|
| Layer | trains small open model on 36K verified data | wraps big model in iter-on-testbench | wraps big model in **decompose + reuse** |
| Output unit | one module | one module | a *system* of modules |
| Verifier in loop | training-time | inference-time | inference-time |
| Novel piece | training-data pipeline | tight test-feedback | **IP corpus + MCP boundary** |

→ We are NOT training a model. We're NOT beating SOTA on VerilogEval. We claim the **system-level reuse pattern** is worth its complexity vs naked codegen — narrower, but defensible.

---

## Benchmark: ChipBench (UCSD/Columbia, 2025)

Three difficulty tiers — we use the two harder ones:

| Tier | # | What it tests |
|---|---|---|
| `dataset_self_contain` | 30 | single self-contained module |
| `dataset_not_self_contain` | 6 | hierarchical (submodules provided) |
| `dataset_cpu_ip` | 9 | RISC-V CPU IP blocks (controller, ALU, RegFile, …) |

Same eval as SiliconMind: Icarus Verilog testbench → `Mismatches: 0` = pass.

---

## Naive baseline (no harness, no reuse)

Single-shot Claude Sonnet 4.6 per problem, then `iverilog -g2012` + testbench.

| Tier | Compiled | Passed | Pass rate |
|---|---|---|---|
| `not_self_contain` | 5/6 | 3/6 | **50%** |
| `cpu_ip` | 5/9 | 1/9 | **11%** |
| **combined** | 10/15 | 4/15 | **27%** |

→ **The model holds up on small things and crashes on real designs.** That gap is what the harness has to close.

---

## Where the baseline breaks

- **Async FIFO** — timed out. Single-shot can't fit CDC reasoning.
- **CPU top** — timed out. ~17K-token prompt with full ISA.
- **PC_REG, chapter12_ctrl, cp0_reg** — compiled but wrong semantics.
- **3-input compare** — **408/421 mismatches** despite valid syntax.

Two failure modes: **too big to one-shot**, and **no feedback loop**.

---

## Proposed harness

<style scoped>
pre { font-size: 0.65em; line-height: 1.1; }
</style>

```
  spec --> Planner (LLM) --> subblocks JSON
                                |
                  +-------------+-------------+
                  v                           v
             REUSE_IP                    GENERATE
                  |                           |
          MCP Server                   Codegen LLM
   (ip_search, get_interface,         (per-module SV)
            instantiate)                      |
                  |                           |
                  +-------------+-------------+
                                v
                         Integrator
                (cat IP src + gen src + TopModule)
                                |
                                v
                          Verifier
                  (iverilog, vvp, mismatch)
                                |
                                v
                  pass/fail + JSON trace
```

---

## The MCP boundary (the part HT specifically asked for)

The agent **never reads IP source code**. It calls three tools:

```python
ip_search(spec_text: str)  -> [{id, description, score}, ...]
ip_get_interface(ip_id)    -> {name, description, params, ports, example}
ip_instantiate(ip_id, ...) -> "sync_fifo #(.WIDTH(8)) u_fifo (.clk(clk), ...);"
```

Why hide source:
- **Context budget**: a 200-line FIFO blows the prompt after ~3 modules
- **Clean contract**: same as a hardware engineer reading a datasheet
- **Hot-swap**: replace the FIFO impl, agent never notices
- **Security framing** (final-project hook): the boundary lets us audit which IP gets touched and inject license metadata

---

## What's in the repo right now

`github.com/MattKotzbauer/rtl-mosaic`

- `mcp/` — server + **20 IPs**, each with its own Icarus self-test. **20/20 pass**.
- `harness/` — planner, codegen, ip_router, integrator, CLI
- `eval/` — baseline runner, metrics, **routing-precision tests** (9 hand-labeled cpu_ip gold entries)
- `docs/` — architecture diagram, 52-module IP corpus plan, internal status doc

**End-to-end pipeline ran on full cpu_ip set tonight.** Numbers next slide.

---

## First harness sweep: cpu_ip set, 20-IP corpus

<style scoped>
table { font-size: 0.85em; }
</style>

| Metric | Baseline (single-shot) | Harness (decompose + reuse) |
|---|---|---|
| Pass rate | **1/9** | **1/9** |
| Compiled | 5/9 | 4/9 |
| Timeouts | 1 | **0** |
| Total IPs reused across runs | 0 | **11** (mostly register_file, mux2, priority_encoder, …) |

→ Headline pass rate didn't move. But the **failure mode shifted**: baseline timed out / hallucinated semantics; harness now mostly fails at **integrator wiring** (LLM-stitched TopModule emits bad macros).

→ That's a *fixable* failure with the adapter-DSL plan. Next week's first item.

---

## Routing precision (planner → IP picks vs gold)

avg precision **0.31** · avg recall **0.30** · avg kind-agreement **0.78** across all 9 cpu_ip problems. Planner correctly identifies REUSE_IP-vs-GENERATE 78% of the time; picks the *right* IP about a third of the time. Headroom is in the IP search ranking.

---

## IP corpus plan: ~50 modules, real sources

<style scoped>
table { font-size: 0.85em; }
</style>

| Source | License | Why |
|---|---|---|
| lowRISC OpenTitan `prim_generic/` | Apache-2.0 | RAM/ROM/CDC, production-tested |
| PULP `common_cells` | Solderpad-0.51 | FIFOs, arbiters, counters |
| Forencich `verilog-uart`/`-i2c`/`-axi` | MIT | Cleanest serial/comm modules |
| aolofsson/oh | MIT | adders, CSAs, dividers (pin to v1.0) |
| dawsonjon/fpu | MIT | FP add/mul/div/sqrt |

**52 modules** curated across memory · arithmetic · comm · control · misc.

→ Status today: **20 ingested + tested** (all pass Icarus) / 30 planned for final.

---

## What we're testing — and against what

**Primary**: pass rate, harness vs naked Claude, on 15 problems. Same metric as SiliconMind. Baseline today: **27%**. Target for final: **≥ 60%**.

**Secondary** (per `eval/metrics.py`):

- **# LLM calls / problem** — cost proxy
- **reuse ratio** — `loc_reused / (loc_reused + loc_generated)`
- **routing precision/recall** — vs hand-labeled gold per cpu_ip problem

<style scoped>
pre { font-size: 0.75em; }
</style>

```json
{ "problem": "Prob004_synchronous_FIFO",
  "summary": {"n_ip_reuses": 3, "n_generated": 1},
  "simulation": {"compiled": true, "passed": true} }
```

---

## Risks (what could kill this)

- **Interface mismatch.** Most IP needs adapter glue. We're betting the LLM can write that glue from port lists alone. If not → adapter-layer DSL.
- **Retrieval quality.** Keyword scoring on 50 modules is fine. At 500 we'd need embeddings. Defer.
- **License audit.** OpenCores GitHub mirrors strip LICENSE files. We'll only ingest from sources we can verify.
- **Vendor primitives.** Excluded entirely (Xilinx XPM, Intel megafunctions). All `prim_generic/`, no `prim_xilinx/`.
- **Verifier coverage.** Icarus testbenches only check what they check. Same limit SiliconMind has.

---

## Path to final (next week)

<style scoped>
table { font-size: 0.85em; }
</style>

| Day | Task | Owner |
|---|---|---|
| Mon–Tue | Grow corpus 20 → 50 IPs (mostly OpenTitan + PULP) | Matt |
| Mon–Tue | Improve planner (multi-shot, retry on parse fail) | Warren |
| Wed | TopModule wiring: replace LLM stitch with adapter DSL | Warren |
| Wed–Thu | Test-feedback loop (re-run on testbench failure) | Leo |
| Thu | Full eval sweep on all 15 hierarchical + IP problems | Leo |
| Fri | Write-up + slide deck for final | all |

**Target for final**: pass rate **≥ 60%** vs **27%** baseline today.

---

## What we want feedback on

1. Is **27% → 60%** the right ambition for the final, or should we aim higher / be more conservative?
2. **MCP boundary**: are we doing enough on the security/audit angle, or should that be a separate slide on its own?
3. **IP corpus depth vs breadth** — 50 deep-tested modules vs 200 shallow ones?
4. Should the planner itself be a **fine-tuned** model (Strategy 2) or stay prompt-only (Strategy 4)?

---

## Backup: failure mode breakdown

→ ~half are **decomposable** failures — the harness's sweet spot.

<style scoped>
table { font-size: 0.62em; }
th, td { padding: 0.25em 0.6em !important; }
</style>

| Problem | Status | Why it failed |
|---|---|---|
| ns_c · 3-input compare | FAIL | 408/421 mismatches; semantic |
| ns_c · async FIFO | TIMEOUT | can't fit CDC one-shot |
| ns_c · CPU top | TIMEOUT | 17K-token prompt; needs decomp |
| cpu_ip · controller | FAIL | wrong opcode encoding |
| cpu_ip · ALU | FAIL | wrong op mapping |
| cpu_ip · Branch_Unit | FAIL | branch condition wrong |
| cpu_ip · ALU_Controller | FAIL | similar to controller |
| cpu_ip · PC_REG | COMPILE_FAIL | bad port match |
| cpu_ip · chapter12_ctrl | COMPILE_FAIL | unknown identifier |
| cpu_ip · cp0_reg | COMPILE_FAIL | port count mismatch |
| cpu_ip · div | TIMEOUT | one-shot too big |

---

## Backup: real planner output (Prob004 sync FIFO)

<style scoped>
pre { font-size: 0.66em; line-height: 1.15; }
</style>

```json
[
  { "name": "dual_port_ram",  "role": "parameterizable dual-port RAM storage",
    "suggested_kind": "REUSE_IP", "search_query": "dual port RAM" },
  { "name": "wr_ptr",         "role": "write pointer and full flag logic",
    "suggested_kind": "REUSE_IP", "search_query": "fifo write pointer" },
  { "name": "rd_ptr",         "role": "read pointer and empty flag logic",
    "suggested_kind": "REUSE_IP", "search_query": "fifo read pointer" },
  { "name": "sync_fifo_top",  "role": "top-level glue",
    "suggested_kind": "GENERATE" }
]
```

→ Router resolved 3/4 to IP. Compiled clean. Sim: 232/327 mismatches on `rdata` (`wfull`, `rempty` correct) — wiring bug in the LLM-stitched top, NOT a decomposition failure. Exactly the kind of issue the adapter-layer DSL fixes.

---

# Thank you

`github.com/MattKotzbauer/rtl-mosaic`

Questions?
