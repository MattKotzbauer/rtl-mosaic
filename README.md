# rtl-mosaic

System-level RTL design harness on top of [SiliconMind-V1](https://arxiv.org/abs/2603.08719), plus a benchmark for evaluating LLMs on IP-reuse versus scratch Verilog generation.

**CS 1440R Team 11** (Spring 2026, Harvard, HT Kung) — Leonardo Ferreira, Matt Kotzbauer, Warren Zhu.

> **For full project context, current status, and open TODOs, read [CONTEXT.md](./CONTEXT.md), which is the canonical reference for the project state.**

## What it does

```
spec  →  Planner (LLM)  →  per-subblock router  →  Integrator  →  iverilog
                            │                       │
                            ├─ REUSE_IP via MCP    │
                            └─ GENERATE via LLM    │
```

Take a chip-design spec. An LLM-as-planner decomposes it into subblocks, tagging each as `REUSE_IP` (an off-the-shelf piece of IP from a curated corpus) or `GENERATE` (custom glue logic). The router resolves `REUSE_IP` subblocks to a 30-IP corpus over MCP. An integrator stitches everything into one `TopModule` and verifies against an Icarus Verilog testbench.

The headline finding from the multi-LLM benchmark is that **IP-reuse skill behaves as an axis independent of scratch Verilog generation**. Across 15 frontier LLMs from 4 providers, routing F1 spans 0.13 to 0.52 while scratch Verilog pass rate on the same problems remains roughly flat, so a reuse-aware metric exposes capability differences that scratch-only benchmarks obscure.

## Layout

| Dir | What |
|---|---|
| `eval/`     | Multi-LLM routing eval, scratch baseline, gold labels, figure pipeline |
| `harness/`  | Planner + IP router + codegen + integrator (end-to-end CLI) |
| `mcp/`      | IP-search MCP server + 30-IP corpus + per-IP self-tests |
| `slides/`   | Final-presentation Beamer source + PDF + figures + spoken script |
| `report/`   | IEEE 2-col final report (in progress, due 2026-05-10) |
| `results/`  | Generated outputs (`multi_routing/`, `multi/`, `harness/`), with large files gitignored |
| `docs/`     | Architecture diagram, IP corpus plan |

## Run

```bash
# environment
source ~/school/.env  # OPENAI_API_KEY, GEMINI_API_KEY, AWS creds for Bedrock
# requires `claude` CLI on PATH for Anthropic models, `iverilog -g2012` for sim

# multi-LLM routing eval (15 models x 16 problems = 240 calls)
python3 eval/multi_routing.py --workers 16

# multi-LLM scratch baseline (foil)
python3 eval/run_multi.py --all --workers 4

# end-to-end harness on one problem
python3 -m harness.run_harness <prompt.txt> <ref.sv> <test.sv>

# regenerate all 10 figures from results JSON
python3 eval/make_figures.py

# IP corpus self-tests (all 30 should pass)
python3 -m pytest mcp/test_mcp.py -v
```

## Headline numbers (26-problem eval, 2026-05-05)

Routing F1 — best-of-provider, single seed and 3-seed mean:

| Provider | Model | F1 (1 seed, n=26) | F1 (3 seeds, n=26) | σ_prob |
|---|---|---|---|---|
| Google | Gemini 2.5 Flash-Lite | 0.464 | **0.514** | 0.094 |
| Anthropic | Claude Opus 4.7 | 0.265 | **0.404** | 0.161 |
| AWS Bedrock | DeepSeek V3.2 | 0.355 | **0.390** | 0.071 |
| OpenAI | GPT-5.2 | 0.433 | **0.381** | 0.126 |

Scratch baseline (single-shot Verilog → Icarus testbench):

| Tier | Most models pass at | Best |
|---|---|---|
| `not_self_contain` (6 hierarchical) | 1–2 / 6 | Sonnet 4.6, Haiku 4.5 at 3/6 |
| `cpu_ip` (9 RISC-V IP blocks) | 1 / 9 | flat across providers |

The full leaderboard for all 15 models is in `results/multi_routing/summary.json` and rendered in `slides/figs/routing_f1.pdf`. Per-provider data including planner blocks and router decisions is in `results/multi_routing/<provider>.json`.

## Status (2026-05-04)

| Component | Status |
|---|---|
| 30-IP corpus with self-tests | ✓ all pass |
| Multi-provider runner (Claude / OpenAI / Bedrock / Gemini) | ✓ |
| 16-problem hand-labeled gold | ✓ |
| 15-model × 16-problem routing eval | ✓ |
| Scratch baseline (15 models) | ✓ |
| Figure pipeline (10 figures) | ✓ |
| Final presentation deck + spoken script | ✓ submitted 2026-04-27 |
| End-to-end harness on extended set | partial (older 1/9 cpu_ip, not re-run) |
| Reuse-ratio metric on TopModule | not wired |
| Multi-seed runs (n=3 for headline 4) | ✓ done 2026-05-05 |
| Embedding-similarity router as alt | ✓ implemented (`harness/ip_router_embed.py`) |
| Failure-mode quantification | ✓ done (`results/multi_routing/failure_modes.json`) |
| Cost-and-latency analysis | ✓ done (`results/multi_routing/cost_latency.json`) |
| INTEGRITY.md (anti-LLM-slop docs) | ✓ done (`docs/INTEGRITY.md`) |
| IEEE 3-page final report | ✓ ready (due Fri 2026-05-08) |

See [CONTEXT.md](./CONTEXT.md) for the full TODO list, weak spots, and reproduction notes.

## License

Code: MIT. Corpus IPs: MIT (each IP carries an explicit `license` field in `mcp/corpus/catalog.json`).
