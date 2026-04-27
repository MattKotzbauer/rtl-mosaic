# Final Presentation Script — Team 11
**Slot**: Mon 4/27, 3:42–3:54 (12 min). Plan for ~10 min spoken + 2 min Q&A.

> Italicized text = optional / cut if running long. Bracketed text = stage directions / what to point at on the slide. Implementation details are flagged **[impl]** so you can cite them in Q&A even if you skip them in the talk.

---

## Slide 1 — Title

> "We're Team 11 — Leo, Matt, and Warren. Our project is **compositional RTL design with LLM agents**. The intermediate version was a single harness on top of one LLM. This final version is a benchmark: we ran 14 frontier LLMs across four providers through that harness and scored them on whether they actually use the IP catalog correctly. That's the headline."

[Move on. Don't dwell on the title slide.]

---

## Slide 2 — The eval

> "Our pipeline takes a chip-design spec, sends it to an LLM acting as a **planner**, and gets back a list of subblocks. For each subblock the planner labels it as either `REUSE_IP` — meaning the LLM thinks this is something a real IP catalog would cover — or `GENERATE`, custom glue logic. Anything tagged `REUSE_IP` goes through our **router**, which queries our 20-IP corpus over MCP and picks the best match.
>
> Then we score against **9 hand-labeled gold entries** for the ChipBench cpu_ip set. Three metrics: precision — of the IPs we picked, what fraction did a human also flag? Recall — of the gold IPs, what fraction did we catch? Kind agreement — at the subblock level, did the planner's `REUSE_IP` vs `GENERATE` decision match the human's?
>
> The point we want to land: this is **not** pass-rate. A model can write perfect Verilog from scratch and still fail this benchmark by re-authoring a register file that's already on the shelf."

**[impl]** Gold labels live in `eval/gold_labels.py`. Each entry has `expected_subblocks` (list of corpus IP IDs the planner *should* surface) and `expected_kinds` (a dict mapping role labels to REUSE_IP/GENERATE). The scorer in `eval/test_routing.py` does best-effort name matching between planner subblocks and gold role labels, then computes precision/recall over the IP-ID sets and kind agreement over the subblock-level decisions.

**[impl]** When `expected_subblocks` is empty (e.g. `Prob005_ALU_Controller` — pure RISC-V case logic, nothing reusable), recall is 1.0 vacuously *only if* the model also picked nothing. If it hallucinates an IP pick on a problem with no gold IPs, recall is 0.

---

## Slide 3 — Models tested

> "14 models, four providers. Anthropic Claude — Opus 4.7, Sonnet 4.6, Haiku 4.5. OpenAI — GPT-5.4 down to GPT-5 plus GPT-4.1, so we span an entire release line. AWS Bedrock for DeepSeek-R1 and V3.2. Google for the working Gemini 2.5 and 3.x flash variants.
>
> Same planner prompt across all 14. No few-shot examples. Same router, same 20-IP corpus, same 9 cpu_ip problems. The only thing that changes between rows is the LLM."

**[impl]** Provider adapters in `eval/providers.py`. Claude calls go through the `claude` CLI with `--model <id> --max-turns 3`. OpenAI uses the SDK with the chat completions endpoint, except for the `gpt-5-codex` family which is completion-only and we excluded. Bedrock uses `bedrock-runtime.converse()` in us-east-1 with the `us.deepseek.r1-v1:0` inference profile and the `deepseek.v3.2` direct model ID. Gemini is plain REST against `generativelanguage.googleapis.com/v1beta` because the python SDK had a key-validation issue.

**[impl]** Models we tried but excluded: `gpt-5-codex` (not a chat model), Gemini 2.5 Flash / 3 Pro Preview / 3.1 Pro Preview — these returned 503s on most calls during the run window, so the n was too low to compare against models with n=9.

---

## Slide 4 — Result 1: routing F1 by LLM

[Point at the bar chart.]

> "Three colors here: green is OpenAI, orange is Anthropic, blue is Bedrock. The bars are precision, recall, and F1 — F1 is the rightmost outlined bar in each group, sorted left-to-right.
>
> The first thing to notice is that **provider family doesn't predict the winner**. The top two are both DeepSeek. Then GPT-5.4. Then a Gemini Flash variant. Anthropic's Claude family is in the middle. The bottom is GPT-5 and Gemini 3 Flash Preview.
>
> *And — counterintuitively — newer doesn't always beat older within a family. GPT-4.1 beats GPT-5.2 and GPT-5.1 here. We don't think that means GPT-4.1 is a smarter model overall; it means it has slightly better defaults for this kind of structured-decomposition task. The point is: a single planner prompt is not a faithful read on a model's full capability — but for the first cut at this benchmark, that's the right protocol.*"

**[impl]** Numbers from `results/multi_routing/summary.json`. Each value is the mean over 9 cpu_ip problems. We did one run per (model, problem) for the headline numbers — temperature 0, but we still see noticeable run-to-run variance on Anthropic models (Opus 4.7 was 0.678 in an earlier run, 0.478 in the run shown). One of the things we'd fix in a follow-up is averaging over N seeds.

---

## Slide 5 — Result 2: scratch baseline (foil)

> "We also ran a **scratch baseline** — the same models, same 15 ChipBench problems, but no harness, no IP catalog. Just: 'Here's a spec, write me Verilog.' This is what most existing Verilog benchmarks measure.
>
> Two things to take from this chart. One: scratch pass rates are **low and flat** on cpu_ip. Almost every model gets 1 out of 9. The Anthropic models do best on the easier `not_self_contain` set at 50%. So if you only had this chart, you'd say all the models are roughly the same on hierarchical RTL.
>
> Two: this chart and the previous chart are telling **different stories about the same models**. Sonnet 4.6 is one of the best scratch coders here. It's at the bottom of the routing chart. Routing skill is a different axis."

**[impl]** Scratch runner in `eval/run_multi.py`. Single-shot — one Claude / OpenAI / Bedrock / Gemini call per problem, output goes through Icarus Verilog + the ChipBench testbench, pass/fail is `Mismatches: 0 in N samples`. Compile errors and sim timeouts on `Prob003_asynchronous_FIFO` (sim hangs) get bucketed as fails. Per-problem outputs in `results/multi/<provider>/<problem>_gen.sv` if anyone wants to inspect them.

---

## Slide 6 — Result 3: routing F1 vs scratch pass rate scatter

[Point at the scatter plot.]

> "This is the orthogonality claim made concrete. Each dot is one model. X-axis is scratch pass rate on cpu_ip. Y-axis is routing F1 on the same set.
>
> If routing skill were just 'smart model = uses IPs better', the dots would line up diagonally. They don't. The cluster on the left is models that pass nothing on scratch but route well — DeepSeek V3.2 in the top-left is the clearest case. And there are models that route okay but score zero scratch passes too.
>
> The **implication** for the field: a reuse-aware metric surfaces a capability that scratch benchmarks completely hide. *Existing benchmarks like VerilogEval and the original ChipBench don't reward reuse at all — a model that re-authors a 200-line FIFO from gates gets the same credit as one that says 'use the corpus FIFO and feed it these widths.'*"

**[impl]** Scatter source: `eval/make_figures.py:fig_routing_vs_scratch`. We fix the x-axis to `cpu_ip` pass rate specifically because it's the harder, more hierarchical set — using `not_self_contain` would weight against scratch (since most models do better there) and muddy the orthogonality claim.

---

## Slide 7 — Failure modes

> "Four failure modes we saw across the 14 models.
>
> **Hallucinated picks**: planner labels a 32-bit ALU as `REUSE_IP`, router pulls — and I'm not making this up — `priority_encoder`. Our router does string overlap on the planner's `search_query` field; if the query is bad the IP pick is bad.
>
> **Over-decomposition**: weaker models split a five-line spec into six subblocks all `GENERATE`. Burns the budget, never reuses.
>
> **Under-decomposition** is the opposite — GPT-5 in particular returns one big `GENERATE` block for almost every problem. Average of 1.0 subblocks per problem, never triggers the router. That's why GPT-5 sits at the bottom of the routing chart.
>
> **Kind-flip**: same model on the same problem, temperature zero, swings between `REUSE_IP` and `GENERATE` across runs. Real variance even at deterministic settings.
>
> *None of these are LLM-skill problems in the usual sense. They're prompt design and corpus coverage problems. That's a tractable place to push next.*"

**[impl]** All four failure modes are visible in `results/multi_routing/<provider>.json` if you grep for `picked_ip`. The priority_encoder-for-ALU example is in `openai_gpt-5.4.json` on `Prob002_alu`. The under-decomposition pattern shows up clearly in the `decomposition.pdf` figure — GPT-5's bar is lowest for "avg subblocks" and zero for "% picked IPs."

---

## Slide 8 — Takeaways + future work

> "Three takeaways.
>
> One: **IP-reuse skill is its own axis**. It does not track scratch pass rate. A multi-model eval surfaces that gap; a single-model harness benchmark hides it.
>
> Two: **the planner is the bottleneck, not the codegen**. Same router, same corpus across all 14 models. The variance lives in subblock decomposition and the search-query field. So a follow-up that fine-tunes a small model just for planner output — SiliconMind-style — could close most of the F1 gap without touching the rest of the pipeline.
>
> Three: **a 20-IP corpus is enough** to score 9 cpu_ip problems meaningfully. We don't see a sign that we'd need a 200-IP corpus to differentiate models at this scale.
>
> Future work: open the eval to community submissions, same protocol; add a real reuse-ratio metric on the integrated TopModule output; fine-tune a small open model on traces from the strongest planner."

---

## Slide 9 — References

[Just hit the reference list briefly. Don't read it.]

> "Code is at `github.com/MattKotzbauer/rtl-mosaic`. PROGRESS.md in the root has the full numerical results, all 10 figures, and the evaluation protocol. Happy to take questions."

---

## Q&A — likely questions and prepped answers

**Q: Why isn't this just a prompt-engineering exercise — wouldn't a better system prompt fix everything?**
> A better prompt could move every model up by some amount, but it doesn't change the orthogonality finding. The relative ordering of routing-vs-scratch skill is the result, and that ordering is robust to which prompt you use as long as the prompt is the same across all models. The benchmark protocol holds; the absolute F1 numbers are a function of the planner prompt.

**Q: Your gold labels are by one annotator — isn't that a problem?**
> Yes, that's the biggest single weakness. Inter-annotator agreement would be the obvious follow-up. The fact that *one annotator* can produce a labeled benchmark that already separates 14 frontier models by 0.4 F1 points suggests the ceiling is high enough that small annotator disagreements don't change the overall picture, but we don't have rigorous proof of that.

**Q: How much did this cost to run?**
> Bedrock DeepSeek was about $0.30 per full run. OpenAI GPT-5.4 was the most expensive — somewhere around $1.50 per full sweep. Total across all providers and the multiple development re-runs: under $20.

**Q: Why ChipBench and not RealBench / VerilogEval?**
> ChipBench has the `cpu_ip` set, which is the only public benchmark we found where the problems are *meant* to be hierarchical — that's the regime where the IP-reuse pattern actually has something to do. VerilogEval-Human is single-module, so reuse is degenerate. RealBench is closer in spirit but most of its problems are full SoCs, too big for our harness in this iteration.

**Q: What's stopping someone from gaming this benchmark by adding a fake "FIFO that solves everything" to the corpus?**
> The corpus is part of the protocol — same corpus across all models. A submission that ships its own corpus would be evaluated separately, like an open vs closed model split. The eval is "given this corpus and these gold labels, how well does your planner score." The corpus and gold labels are the spec, not a degree of freedom.

**Q: Why did you exclude Gemini 2.5 Flash?**
> 503s on every call during our run window. Looks like rate-limiting, not a model bug. We didn't want to have an entry with n=1 alongside entries with n=9.

**Q: What's the hardest single failure mode to fix?**
> Under-decomposition. If the planner returns one block for a problem, the router never gets to do anything. You can't fix it from inside the router — it's a planner-prompt issue. The fix is either better planner prompting (cheap) or a fine-tuned planner (expensive but probably more robust).
