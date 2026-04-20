# Architecture

```
                          ┌──────────────────────────────────┐
   spec_prompt.txt  ───▶  │   Planner (LLM)                  │
                          │   "decompose into subblocks"     │
                          └────────────────┬─────────────────┘
                                           │  JSON: [{name, role,
                                           │         suggested_kind,
                                           │         port_spec,
                                           │         search_query}, …]
                                           ▼
                          ┌──────────────────────────────────┐
                          │   IP Router (per subblock)       │
                          └──────────┬───────────────┬───────┘
                                     │               │
                          REUSE_IP   │               │   GENERATE
                                     ▼               ▼
                       ┌──────────────────┐  ┌────────────────┐
                       │  MCP IP-Search   │  │   Codegen LLM   │
                       │  ─ ip_search     │  │  per-module SV  │
                       │  ─ get_interface │  └────────┬────────┘
                       │  ─ instantiate   │           │
                       │  (no source)     │           │
                       └────────┬─────────┘           │
                                │                     │
                  inst snippet  │                     │ source
                  + source_file │                     │
                                ▼                     ▼
                          ┌──────────────────────────────────┐
                          │   Integrator                     │
                          │   - concat IP sources            │
                          │   - concat generated sources     │
                          │   - LLM writes TopModule wiring  │
                          └────────────────┬─────────────────┘
                                           │  combined.sv
                                           ▼
                          ┌──────────────────────────────────┐
                          │   Verifier (Icarus Verilog)      │
                          │   iverilog + vvp + testbench     │
                          └────────────────┬─────────────────┘
                                           │
                                           ▼
                                    pass / fail
                                    + JSON trace
                                    (for metrics)
```

## Why the MCP boundary

The agent never reads IP source. It sees:
- a one-line description
- the port list + parameters
- an instantiation template

That's the contract a hardware engineer would use. It also keeps the agent's
context small (a 200-line FIFO would otherwise blow the budget after a few
modules) and makes IP swap-in/swap-out trivial.

## What's stubbed for the intermediate

- Planner uses single-shot LLM prompting; no self-verify yet.
- TopModule wiring is itself LLM-generated rather than templated.
- Corpus has 5 mocked modules; final has ~50 from real sources (see
  [IP_CORPUS_PLAN.md](IP_CORPUS_PLAN.md)).
- No retrieval beyond keyword scoring.
- No retry loop on testbench failure.

## What we lift from SiliconMind-V1

- Icarus Verilog as the only verifier (open-source, reproducible).
- Testbench-driven binary pass/fail as the gate (vs Dolphin's soft LLM judge).
- Module-level codegen comes from a SiliconMind-style model in spirit; for now
  we use Claude Sonnet 4.6 as a placeholder.

## What's new vs SiliconMind-V1

SiliconMind targets *one module at a time*. We target *systems of modules*,
where the win comes from reusing known-good IP rather than re-generating
every primitive from scratch.
