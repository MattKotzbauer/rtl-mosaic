Slide 1 — Title

Hi everyone, we're Team 11 — Leo, Matt, and Warren. Our project is compositional RTL design with LLM agents. The intermediate version was a single harness on top of one LLM. This final version turns that harness into a benchmark. We ran fourteen frontier large language models from four different providers — Anthropic Claude, OpenAI GPT, AWS Bedrock DeepSeek, and Google Gemini — through the same harness and scored each one on a single specific question: does it actually use the IP catalog correctly when given a chip design spec? That's the headline of this whole presentation.

Slide 2 — The eval

Here's how the pipeline works. We start with a chip design specification — for example, a register file or a small CPU module. We send that specification to an LLM that we're treating as a planner. The planner reads the spec and returns a JSON list of subblocks. For each subblock the planner decides one of two things. Either it tags the subblock as REUSE_IP, meaning the planner thinks this is something a real IP catalog would already cover, like a FIFO or a register file or a multiplexer. Or it tags it as GENERATE, meaning this is custom glue logic specific to this design.

Anything tagged REUSE_IP then goes through our router. The router is a deterministic component — it takes the planner's search query and looks through our corpus of twenty IP modules over an MCP server. It picks the IP from the corpus whose keywords overlap most with the planner's search query.

Then we score the result against nine hand-labeled gold entries that we created for the ChipBench cpu_ip dataset. The gold labels were written by Matt, by hand, after looking at each problem's specification. For each problem the gold says: here are the IP IDs from the corpus that a sensible planner-plus-router should reuse, and here are the role-level decisions about which subblocks should be REUSE_IP versus GENERATE.

We track three metrics. Precision is: of the IPs the router picked, what fraction did the human also flag as gold? Recall is: of the gold IPs, what fraction did the router actually pick? And kind agreement is: at the subblock level, did the planner's REUSE_IP versus GENERATE decision match the human's? F1 is the harmonic mean of precision and recall — we use F1 as our headline number because it captures both kinds of failure in one value.

The point we want to land here, before any results: this is not a Verilog pass-rate benchmark. A model can write perfectly correct Verilog and still fail this evaluation, by re-authoring a register file from scratch when there's already a register file sitting in the corpus.

Slide 3 — Models tested

Fourteen models in the eval. Three from Anthropic — Claude Opus 4.7, Claude Sonnet 4.6, and Claude Haiku 4.5. Five from OpenAI — GPT-5.4 from this March, GPT-5.2 from December, GPT-5.1 from November, GPT-5 from August, and GPT-4.1 from April of last year. We deliberately included this whole release line to ask the question: does newer beat older within a family? Two from AWS Bedrock — DeepSeek-R1 and DeepSeek V3.2. And four from Google Gemini — 2.5 Pro, 2.5 Flash-Lite, 3 Flash Preview, and 3.1 Flash-Lite Preview.

The protocol is identical across all fourteen. Same planner system prompt. No few-shot examples. Same router with the same keyword-matching logic. Same twenty-IP corpus. Same nine cpu_ip problems. The only thing that changes between rows in our results table is the LLM. So when you see one model rank higher than another, that's a property of the model, not of any other moving piece in the system.

Three models we tried but had to exclude. GPT-5-codex isn't a chat model, it's completion-only, and we didn't want to plumb a separate code path for one model. Gemini 2.5 Flash, Gemini 3 Pro Preview, and Gemini 3.1 Pro Preview returned five-oh-three errors on most calls during our run window — looks like rate limiting on the preview tiers, not a model bug, but the n was too low to be comparable.

Slide 4 — Result one, routing F1 by LLM

This is our headline chart. Let me walk through the axes carefully.

The x-axis is the fourteen models, sorted by F1 score from highest on the left to lowest on the right. Each model's bar group has three bars next to each other. The leftmost bar in each group, with the lighter shade, is precision. The middle bar, slightly darker, is recall. The rightmost bar with the black outline is F1. The y-axis is the score on a zero-to-one scale, where each value is the mean over our nine cpu_ip problems.

Color coding: green bars are OpenAI, orange bars are Anthropic, blue bars are AWS Bedrock for the DeepSeek models. We use color-by-provider so you can see at a glance whether one company's models cluster together.

The first thing to notice is that they don't cluster. Provider family does not predict the winner. The top two are both DeepSeek — V3.2 at F1 of zero point seven, and R1 at zero point six two one. Then GPT-5.4 at zero point six one five. The Anthropic Claude family is in the middle of the pack. The bottom of the chart is GPT-5 at zero point three three three.

Second observation, and this is more counterintuitive. Newer doesn't always beat older within a single family. GPT-4.1 at F1 zero point five three three actually beats GPT-5.2, GPT-5.1, and GPT-5. We're not claiming GPT-4.1 is a smarter model overall. What we are claiming is that a single planner prompt is not a faithful read on a model's full capability. For our first cut at this benchmark, holding the prompt constant across all models is the right protocol — it's the only way to get apples-to-apples comparisons. But it does mean some models are showing up worse than they would in real use.

Third observation. GPT-5 sits at the very bottom with F1 zero point three three. We dug into why. GPT-5 returns on average exactly one subblock per problem. It under-decomposes everything into a single big GENERATE block, which means the router never gets called. We'll come back to this on the failure-modes slide.

Slide 5 — Result two, scratch baseline as a foil

This chart is the foil for the previous one. We took the same fourteen models and ran the same fifteen ChipBench problems through them, but with no harness, no IP catalog, no decomposition. Just: here's a specification, please write me Verilog, output goes through Icarus Verilog and the ChipBench testbench. This is what most existing Verilog benchmarks measure.

Axes: x-axis is the same fourteen models. The y-axis is pass rate on a zero-to-one scale, where pass means the testbench reports zero mismatches against the reference. Each model has two bars — the lighter bar is the not-self-contain set, which is six hierarchical problems, and the darker bar with the outline is the cpu_ip set, which is nine RISC-V CPU IP problems.

Two takeaways from this chart. The first is that scratch pass rates on cpu_ip are low and remarkably flat across models. Almost every model gets exactly one out of nine, which is around eleven percent. The Anthropic Claude models do best on the easier not-self-contain set, where Sonnet and Haiku each pass three out of six. So if you only had this chart, you'd say all the models are roughly equivalent on hierarchical RTL.

The second takeaway is that this chart and the previous chart are telling different stories about the same models. Look at Claude Sonnet 4.6. It's one of the best scratch coders on this chart. On the previous chart it was sitting near the bottom of the routing F1 leaderboard. That's the orthogonality claim, and the next slide makes it visual.

Slide 6 — Result three, routing F1 versus scratch pass rate

This is a scatter plot. Each dot is one model. The x-axis is the model's scratch pass rate on cpu_ip — the same number from the previous slide, ranging from zero to about zero point five. The y-axis is the model's routing F1, the same number from the slide two before this, ranging from zero up to about zero point seven. Color of each dot is provider — green for OpenAI, orange for Anthropic, blue for Bedrock. Each dot is also labeled with the model name.

If routing skill were just a side-effect of "smarter model writes better code overall," then the dots would line up along the diagonal — high scratch pass rate would predict high routing F1. They don't. There's a cluster of dots in the upper-left of the plot that have low scratch pass rates but high routing F1, with DeepSeek V3.2 being the clearest example, sitting at scratch around zero point one one and routing F1 at zero point seven. And there are dots near the origin that have low scratch and low routing — those models are failing on both axes for different reasons.

The implication is concrete. A reuse-aware metric like ours surfaces a model capability — recognizing when something is reusable IP — that scratch benchmarks completely hide. Existing single-module benchmarks like VerilogEval and the original ChipBench score both the model that re-authors a two-hundred-line FIFO from gates and the model that says "use the corpus FIFO with these widths" identically, as long as both compile and pass simulation. Our benchmark gives those two models very different scores.

Slide 7 — Failure modes

Across the fourteen models we saw four distinct failure modes that recurred enough to be worth naming.

The first is hallucinated picks. The planner correctly tags a 32-bit ALU as REUSE_IP, but the router, looking at the search query the planner provided, picks something completely wrong — in one specific run, GPT-5.4 generated a search query for an ALU that the router resolved to priority_encoder. The router does string-overlap on keywords. If the planner's query field is bad, the router is bad downstream.

The second is over-decomposition. Some weaker models split a five-line specification into five or six subblocks, all marked GENERATE. They're not using the corpus, and they're burning context budget on logic that doesn't exist.

The third is under-decomposition, which is the opposite. GPT-5 in particular returns one big GENERATE block for almost every problem. Average of one point zero subblocks per problem in our data. The router never even gets called, so even if the corpus has a perfect match for what the spec needs, GPT-5 will never find it. That's why GPT-5 sits at the bottom of the routing chart even though it's a competent code model.

The fourth is what we call kind-flip. Same model, same problem, temperature set to zero — supposedly deterministic — and it still swings between REUSE_IP and GENERATE on the same subblock between runs. We saw real run-to-run variance even at deterministic settings, especially in the Anthropic family. Claude Opus 4.7 went from F1 zero point six seven eight in one run to zero point four seven eight in a later run, with no other changes.

The interpretation we want to argue for: none of these are fundamental LLM-skill problems in the usual sense of "the model isn't smart enough." Three out of four are prompt design and corpus coverage problems. The fourth, kind-flip, is a sampling-variance issue. All of these are tractable places for follow-up work to push.

Slide 8 — Takeaways and future work

Three takeaways.

One. IP-reuse skill is its own axis. It does not track scratch pass rate. A multi-model evaluation surfaces that gap clearly. A single-model harness benchmark, like the one in our intermediate presentation, hides it. If we hadn't run multiple models, we wouldn't know that some of the strongest scratch coders are some of the weakest IP routers.

Two. The planner is the bottleneck, not the codegen. We held the router and the corpus and the gold labels fixed across all fourteen models. The variance in routing F1 — almost a 0.4 spread — lives entirely in subblock decomposition and the search-query field that the planner emits. So a follow-up that fine-tunes a small open-source model just for planner output, in the SiliconMind style, could close most of that gap without changing anything else in the pipeline.

Three. A 20-IP corpus is enough to score 9 cpu_ip problems meaningfully. We don't see evidence that we'd need to grow the corpus to two hundred IPs to differentiate models at this scale. Corpus depth, not breadth, was the right call.

For future work, three concrete next steps. Open the eval up to community submissions — same protocol, any model, any planner prompt, results published. Add a real reuse-ratio metric on the integrated TopModule output, measuring lines of code reused versus lines of code generated. And fine-tune a small open-source model on traces from the strongest planner — that's the obvious extension of SiliconMind into the system-level setting.

Slide 9 — References and code

The full list of prior work is on this slide — ChipGPT, VeriGen, RTLCoder, ChipNeMo, HiVeGen, MAGE, SiliconMind. Benchmarks we evaluate against — ChipBench, VerilogEval, RealBench. Open-source IP corpora that informed our corpus design — OpenTitan, PULP common cells, Adapteva OH, Forencich's UART/I2C/AXI/Ethernet, dawsonjon's FPU.

All of the code is on GitHub at MattKotzbauer slash rtl-mosaic. The PROGRESS.md file in the root has the full numerical results, all ten figures, the evaluation protocol, and a delta table comparing the nine-problem and sixteen-problem versions of the eval. We're happy to take questions.
