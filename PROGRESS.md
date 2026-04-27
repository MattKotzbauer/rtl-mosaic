# Progress Report — Final Presentation 2026-04-27

**Team 11**: Leonardo Ferreira, Matthew Kotzbauer, Warren Zhu
**Course**: CS 1440R / 2440R, HT Kung
**Slot**: Mon 4/27, 3:42pm

## What changed since the intermediate

The intermediate deck (`slides/intermediate.{md,pdf}`) framed the project as a
single-LLM harness. HT's note after the intermediate was: *turn this into a
benchmark; compare LLMs.* This presentation does that.

Concrete additions:

- **Multi-provider runner** (`eval/providers.py`): Claude CLI, OpenAI SDK,
  Bedrock (DeepSeek), Gemini REST.
- **Cross-LLM routing eval** (`eval/multi_routing.py`): runs the planner +
  router pipeline across N LLMs on the 9 cpu_ip problems, scores against the
  hand-labeled gold in `eval/gold_labels.py`. Aggregates to
  `results/multi_routing/summary.json`.
- **Cross-LLM scratch baseline** (`eval/run_multi.py`): same 15 ChipBench
  problems, single-shot Verilog gen, kept as a foil — answers "is the model
  that writes the best Verilog also the best at recognizing reusable IP?"
- **Figure pipeline** (`eval/make_figures.py`): 10 figures, all rebuilt from
  the JSON results.

## Models in the eval (14 total)

| Provider | Model | API path |
|---|---|---|
| Anthropic | Claude Opus 4.7 | `claude` CLI |
| Anthropic | Claude Sonnet 4.6 | `claude` CLI |
| Anthropic | Claude Haiku 4.5 | `claude` CLI |
| OpenAI | GPT-5.4 | OpenAI SDK |
| OpenAI | GPT-5.2 | OpenAI SDK |
| OpenAI | GPT-5.1 | OpenAI SDK |
| OpenAI | GPT-5 | OpenAI SDK |
| OpenAI | GPT-4.1 | OpenAI SDK |
| AWS Bedrock | DeepSeek-R1 | `bedrock-runtime` (us-east-1) |
| AWS Bedrock | DeepSeek V3.2 | `bedrock-runtime` (us-east-1) |
| Google | Gemini 2.5 Pro | REST |
| Google | Gemini 2.5 Flash-Lite | REST |
| Google | Gemini 3 Flash Preview | REST |
| Google | Gemini 3.1 Flash-Lite Preview | REST |

Same planner prompt, same router (deterministic, MCP-backed), same 20-IP
corpus, same 9 cpu_ip problems. No few-shot examples. Gemini 2.5 Flash,
Gemini 3 Pro Preview, and Gemini 3.1 Pro Preview returned mostly 503s and
are excluded.

## Headline results

### Routing F1 (planner + router vs hand-labeled gold)

Top 5 by mean F1 across 9 problems (from `results/multi_routing/summary.json`):

| Rank | Model | Precision | Recall | F1 | Kind agreement |
|---|---|---|---|---|---|
| 1 | DeepSeek V3.2 | 0.741 | 0.674 | **0.700** | 0.846 |
| 2 | DeepSeek-R1 | 0.722 | 0.578 | **0.621** | 0.741 |
| 3 | GPT-5.4 | 0.722 | 0.600 | **0.615** | 0.769 |
| 4 | GPT-4.1 | 0.556 | 0.519 | **0.533** | 0.806 |
| 5 | GPT-5.2 | 0.574 | 0.489 | **0.522** | 0.796 |

Bottom 3:

| Rank | Model | F1 | What went wrong |
|---|---|---|---|
| 10 | GPT-5 | 0.333 | under-decomposes (avg 1.0 subblocks/problem; never triggers the router) |
| 9 | Sonnet 4.6 | 0.456 | mis-routes: high subblock count, picks wrong IP |
| 8 | Opus 4.7 | 0.478 | high run-to-run variance — earlier runs got 0.678 |

### Scratch baseline (foil — `not just synthesis`)

Top scratch coders (cpu_ip pass rate):

| Model | not_self_contain | cpu_ip |
|---|---|---|
| Claude Sonnet 4.6 | 3/6 = 50% | 1/9 = 11% |
| Claude Haiku 4.5 | 3/6 = 50% | 1/9 = 11% |
| GPT-5.4 | 1/6 = 17% | 1/9 = 11% |
| All others | ≤ 2/6 | 1/9 |

Scratch pass rates are low and very flat across LLMs on cpu_ip. The
routing axis spreads models out far more — that's the headline.

## Figures (in `slides/figs/`)

| File | What it shows |
|---|---|
| `routing_f1.pdf` | P / R / F1 grouped bars per LLM, sorted by F1 |
| `routing_heatmap.pdf` | per-(LLM, problem) F1 heatmap |
| `provider_rollup.pdf` | mean F1 by provider family (OpenAI / Anthropic / Bedrock) |
| `kind_vs_f1.pdf` | scatter: kind agreement vs F1 (knowing *when* to reuse ≠ picking the right IP) |
| `decomposition.pdf` | avg subblocks + REUSE_IP % per LLM |
| `problem_difficulty.pdf` | per-problem mean F1 across 10 LLMs (which problems are hardest) |
| `ip_frequency.pdf` | which IPs the corpus actually surfaces; green = also in gold, red = mis-routes |
| `latency.pdf` | seconds-per-planner-call by LLM |
| `scratch_baseline.pdf` | scratch-Verilog pass rate by LLM, both datasets |
| `routing_vs_scratch.pdf` | scatter: routing F1 vs scratch pass rate (orthogonal axes) |

## What we can claim cleanly

1. **IP-reuse skill is its own axis.** Across 10 LLMs, routing F1 ranges from
   0.33 to 0.70 while scratch pass rate on cpu_ip is flat at 1/9 for most.
   A scratch-only benchmark would call these models indistinguishable.
2. **The planner is the bottleneck, not the codegen.** Same router on the
   same corpus; variance lives in subblock decomposition and the
   `search_query` field. GPT-5 produces 1 subblock on average and never
   triggers the router.
3. **Provider family doesn't predict the winner.** Bedrock/DeepSeek tops the
   board on routing; Anthropic tops scratch. They're solving different tasks.
4. **A 20-IP corpus is enough to score 9 cpu_ip problems meaningfully.** No
   evidence yet that we need a 200-IP corpus to differentiate models.

## What we are not claiming

- Not that the harness end-to-end beats single-shot codegen on cpu_ip. It
  doesn't (1/9 vs 1/9). That's a separate, slower fix.
- Not SOTA on any existing benchmark. We re-eval on ChipBench.
- Not that any model is "better" overall — only that *routing* and *scratch*
  are independent axes.

## Caveats

- **Run-to-run variance**: temperature 0 still gives noticeable variance on
  some Anthropic models (Opus 4.7: 0.678 → 0.478 between two runs). One run
  of each model in the headline numbers; needs averaging across N seeds.
- **Gold labels**: 9 hand-labeled entries by one annotator (Matt). Recall
  is only as good as the gold set. Some problems have empty gold (`Prob001
  controller`: no IP fits in the 20-corpus) — those score 1.0 vacuously when
  the model also picks nothing.
- **Gemini scratch**: 400-class API errors during the scratch sweep on most
  problems; routing eval ran clean. Gemini scratch numbers excluded from
  comparison.

## Repo layout (relevant subset)

```
eval/
  providers.py          # multi-provider LLM adapters
  multi_routing.py      # cross-LLM routing eval driver
  run_multi.py          # cross-LLM scratch baseline driver
  make_figures.py       # all 10 figures from results JSON
  gold_labels.py        # hand-labeled gold for cpu_ip
  test_routing.py       # scoring (P/R/KA against gold)
results/
  multi_routing/        # per-LLM routing JSON + summary.json
  multi/                # per-LLM scratch JSON
slides/
  intermediate.{md,pdf} # original presentation
  final.tex             # final presentation source
  figs/                 # all PDF/PNG figures
```
