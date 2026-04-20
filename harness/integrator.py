"""Integrator: stitch resolved subblocks into one Verilog file with a TopModule.

The TopModule wiring step is itself an LLM call (codegen) for the intermediate
demo: we hand Claude (i) the original spec and (ii) the available subblock
interfaces, and ask for one TopModule that wires them together.
"""
import os

from harness._claude_cli import call_claude, strip_code_fences

INTEGRATOR_SYSTEM = """You are integrating several Verilog submodules into a
single TopModule that satisfies the spec below.

You will be given:
  1. The original natural-language spec for TopModule.
  2. A list of available submodules, each with its module declaration header
     (so you know its ports + parameters) and an example instantiation.

Your job: emit ONE Verilog module named TopModule with the exact port list
from the spec. Inside, instantiate the available submodules as needed, declare
internal wires/regs, and add any glue logic required to satisfy the spec.

Rules:
- Do NOT redefine the submodules; assume they are already in the same
  compilation unit.
- Output ONLY the TopModule source. No markdown fences, no explanations.
- Must compile under `iverilog -g2012`.
- The module MUST be named exactly TopModule.
- If a needed submodule is missing, write the logic inline.
"""


def _read_source(path: str) -> str:
    try:
        with open(path) as f:
            return f.read().rstrip() + "\n"
    except Exception as e:
        return f"// [integrator] could not read {path}: {e}\n"


def _module_header_snippet(src: str, max_lines: int = 30) -> str:
    """Best-effort: pull the first `module ... );` from a Verilog source for the
    LLM, so the prompt stays small."""
    lines = src.splitlines()
    out = []
    started = False
    for ln in lines:
        s = ln.strip()
        if not started and s.startswith("module "):
            started = True
        if started:
            out.append(ln)
            if ");" in ln:
                break
        if len(out) >= max_lines:
            break
    return "\n".join(out)


def _build_top_prompt(spec_text: str, subblocks: list, sources: dict) -> str:
    parts = [INTEGRATOR_SYSTEM, "\n\nORIGINAL SPEC:\n", spec_text,
             "\n\nAVAILABLE SUBMODULES:\n"]
    for sb in subblocks:
        if sb["kind"] == "ip":
            parts.append(f"\n--- IP: {sb['id']} (instance suggested name: u_{sb['name']}) ---\n")
            parts.append("Header:\n")
            parts.append(_module_header_snippet(sources.get(sb["id"], "")))
            parts.append("\nExample instantiation:\n")
            parts.append(sb["instantiation"])
        else:  # gen
            parts.append(f"\n--- GEN: {sb['name']} ---\n")
            parts.append("Header:\n")
            parts.append(_module_header_snippet(sb["source_text"]))
    parts.append("\n\nNow emit ONLY the TopModule source.\n")
    return "".join(parts)


def integrate(spec_text: str, subblocks: list) -> str:
    """Produce one Verilog string: IP sources + generated sources + TopModule."""
    chunks = []
    sources = {}  # ip_id -> source text, for header extraction

    seen_ip_files = set()
    for sb in subblocks:
        if sb["kind"] == "ip":
            sf = sb.get("source_file")
            if sf and sf not in seen_ip_files:
                src = _read_source(sf)
                sources[sb["id"]] = src
                chunks.append(f"// === IP: {sb['id']} ({os.path.basename(sf)}) ===\n")
                chunks.append(src)
                chunks.append("\n")
                seen_ip_files.add(sf)
            elif sf:
                # already included; still record source for header use
                sources.setdefault(sb["id"], _read_source(sf))
        else:  # gen
            chunks.append(f"// === GEN: {sb['name']} ===\n")
            chunks.append(sb["source_text"])
            chunks.append("\n")

    # Ask LLM to produce the TopModule
    top_prompt = _build_top_prompt(spec_text, subblocks, sources)
    try:
        raw = call_claude(top_prompt)
        top_src = strip_code_fences(raw).strip() + "\n"
    except Exception as e:
        top_src = (f"// [integrator] LLM TopModule call failed: {e}\n"
                   "module TopModule (); endmodule\n")

    chunks.append("// === TopModule (LLM-stitched) ===\n")
    chunks.append(top_src)
    return "".join(chunks)
