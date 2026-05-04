# Project Context — rtl-mosaic
*Canonical state doc for Team 11 (CS 1440R, Spring 2026). Read this first before any work on the project.*

Last sync: 2026-05-04 (six days to final report deadline)

---

## What this project is

We built a **system-level RTL design harness** on top of the SiliconMind-V1 idea, plus a **benchmark** for evaluating large language models (LLMs) on the IP-reuse-versus-scratch axis of chip design. The harness takes a Verilog spec, asks an LLM-as-planner to decompose it into subblocks, routes any subblock tagged `REUSE_IP` to a curated 30-IP corpus over an MCP server, and integrates the result into a `TopModule` verified by Icarus Verilog testbenches.

The **central claim** we land on, supported by 16-problem multi-LLM data:
**IP-reuse skill is its own axis.** It does not track scratch Verilog pass rate. A reuse-aware metric reveals model capabilities that scratch-only benchmarks (VerilogEval, original ChipBench) hide.

## Where we are

**Final presentation**: submitted Mon 2026-04-27 at 3:42pm. Slot was 12 min; we used the 8-frame Beamer deck in `slides/final.{tex,pdf}` and the verbatim spoken script in `slides/script_plain.md`.

**Final report**: due Sun 2026-05-10 23:59 EDT. IEEE 8.5×11 two-column, 3 pages excluding refs and supplement. PDF + zip submission. Graded on (1) novelty, (2) results and significance, (3) writing quality.

**State of the eval** (see `results/multi_routing/summary.json`):
- 15 LLMs across 4 providers ran the routing pipeline on 16 ChipBench problems
- Headline 4 models for the report (best-of-provider, full n=16):
  - Claude Opus 4.7 — F1=0.375
  - GPT-5.2 — F1=0.467
  - DeepSeek V3.2 — F1=0.441
  - Gemini 2.5 Flash-Lite — F1=0.437
- Scratch baseline (foil): mostly flat at ~1/9 = 11% on cpu_ip; Anthropic best on not_self_contain at 50%

**State of the corpus** (see `mcp/corpus/catalog.json`):
- 30 IPs, all passing Icarus self-tests
- Categories: memory, datapath, counter, sequence, primitive, clock
- Hand-written; license MIT throughout

**State of the gold labels** (see `eval/gold_labels.py`):
- 16 hand-labeled entries (Matt) — 9 cpu_ip + 7 self_contain
- Each entry: expected_subblocks (gold IP IDs) + expected_kinds (REUSE_IP/GENERATE per role) + rationale
- One annotator. Inter-annotator agreement TODO if time permits.

## Files that matter

| Path | Role |
|---|---|
| `eval/providers.py` | Multi-provider LLM adapters (Claude CLI, OpenAI SDK, Bedrock, Gemini REST) |
| `eval/multi_routing.py` | Cross-LLM routing eval driver — primary entry point |
| `eval/run_multi.py` | Cross-LLM scratch baseline (foil) |
| `eval/gold_labels.py` | Hand-labeled gold for 16 problems |
| `eval/test_routing.py` | Scoring (P/R/F1, kind agreement) against gold |
| `eval/make_figures.py` | Regenerates all 10 figures from results JSON |
| `harness/{planner,codegen,ip_router,integrator}.py` | End-to-end pipeline (Claude-only currently) |
| `mcp/server.py` + `mcp/corpus/` | IP-search MCP server + 30-IP corpus + tests |
| `results/multi_routing/summary.json` | Headline numbers per provider |
| `results/multi_routing/<provider>.json` | Full per-(model, problem) records |
| `results/multi/<provider>/results.json` | Scratch baseline per provider |
| `slides/final.{tex,pdf}` | Submitted final-presentation deck |
| `slides/script_plain.md` | Verbatim spoken script for the presentation |
| `slides/figs/*.pdf` | All 10 figures from the deck |
| `report/report.tex` | Final 3-page IEEE report (in progress) |
| `PROGRESS.md` | Detailed status log + delta tables |

## What's done

- Multi-provider LLM adapter (claude CLI, OpenAI, Bedrock, Gemini)
- 30-IP corpus, all with passing self-tests
- 16-problem hand-labeled gold
- 15 models × 16 problems = 240-call routing eval (run 2026-04-27)
- 10 figures generated automatically from JSON
- Final presentation deck + verbatim script delivered
- Repo public at github.com/MattKotzbauer/rtl-mosaic

## What's open (in priority order for the report)

**Must-have for May 10 submission**:
1. Write the 3-page IEEE report (`report/report.tex`)
2. Build a single leading figure (rubric requires it)
3. Update `README.md` (currently dated 2026-04-19, says 5 IPs)
4. Build supplement zip per Canvas naming convention

**Should-have for "results and significance" rubric category**:
5. End-to-end harness sweep on 16 problems (we only have routing scores; need TopModule pass/fail)
6. Reuse-ratio metric on integrated TopModule (LoC reused / total)
7. Quantify the four failure modes from slide 7
8. Multi-seed runs (n=3) for the four headline models — closes variance objection
9. Embedding-similarity router as a comparison to keyword router
10. Cost / latency table

**Nice-to-have**:
- Inter-annotator agreement (Cohen's kappa) on a subset of gold labels
- Expand gold labels to 25+ problems
- Wire up real OpenTitan / PULP IPs
- Test-feedback retry loop (was promised in intermediate)
- Public leaderboard at footemp.bar
- Demo video / GIF

The full TODO list (30 tasks) is tracked in the agent task system.

## Honest weak spots (do not over-claim in the report)

1. **Harness end-to-end does not currently beat scratch baseline on cpu_ip.** Both are 1/9. The intermediate-deck claim that decomposition + IP-reuse beats scratch on cpu_ip is not currently supported. Either commit fully to routing-quality as the headline (recommended) or run a test-feedback loop and re-measure end-to-end before claiming a win.
2. **Run-to-run variance is real.** Claude Opus 4.7 went from F1=0.678 (one early run, 9 problems) to F1=0.375 (current 16-problem run). Single-seed numbers are noisy — multi-seed runs would close this.
3. **Single annotator on gold labels.** Cohen's kappa with a second annotator is the obvious follow-up.
4. **Keyword router has known disambiguation failures.** With 30 IPs in the corpus, generic search queries collide (e.g., `"counter"` resolves to `up_counter` even when `up_down_counter` is the right pick). This is a router design limitation, not an LLM limitation.

## How to reproduce the headline numbers

```bash
# from repo root
source ~/school/.env  # OPENAI_API_KEY, GEMINI_API_KEY, AWS creds
python3 eval/multi_routing.py --workers 16
python3 eval/make_figures.py
# results land in results/multi_routing/summary.json + slides/figs/
```

End-to-end harness on one problem:
```bash
python3 -m harness.run_harness <prompt> <ref> <test>
```

## Voice / writing notes for the report

- Direct, opinionated, undergraduate voice. Not "this work makes a significant contribution."
- "I" / "we" freely, contractions OK.
- No "novel," "innovative," "leveraging," "compelling," "elegant," "promising."
- No semicolons.
- No symmetrical hedging ("while X is impressive, Y could be improved").
- Trust the reader. Skip rhetorical punchlines like "X is not Y. It is Z."
- IEEE 2-column hard limit: 3 pages. Cut before you write.

## Team

- **Matt Kotzbauer** — corpus, multi-LLM eval, figures, presentation, report
- **Warren Zhu** — planner, integrator, adapter-DSL for TopModule wiring
- **Leo Ferreira** — eval scaffolding, baseline runner, slide deck logistics
  *(rough split — confirm with team before finalizing the contribution statement)*

## Pointers

- Repo: https://github.com/MattKotzbauer/rtl-mosaic
- Local: `/home/matt/school/1440r/project/silicon-mind-harness/`
- Course Canvas: course 165320
- Final report instructions: see Canvas announcement "Final Project Reports Due on Sunday (5/10)"
