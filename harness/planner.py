"""Planner: ask Claude to decompose a Verilog spec into subblocks.

Each subblock is a dict:
  {name, role, suggested_kind: "REUSE_IP"|"GENERATE", port_spec: str, search_query: str}
"""
import json
import re

from harness._claude_cli import call_claude, strip_code_fences

PLANNER_SYSTEM = """You are a hardware decomposition planner.

You are given a natural-language specification for a Verilog module named TopModule.
Your job: break it into 1-6 subblocks that compose into TopModule.

For each subblock, decide whether it should be REUSE_IP (a common, reusable
piece of IP that probably exists in an IP catalog: FIFOs, register files,
ALUs, muxes, counters, decoders, control units, etc.) or GENERATE (custom
glue logic, datapaths, or anything specific to this spec).

Output ONLY a JSON array, no prose, no code fences. Example:

[
  {
    "name": "fifo_buf",
    "role": "data buffer",
    "suggested_kind": "REUSE_IP",
    "port_spec": "clk, rst, wr_en, rd_en, din[WIDTH-1:0] -> dout[WIDTH-1:0], full, empty",
    "search_query": "synchronous fifo"
  },
  {
    "name": "controller",
    "role": "top-level FSM",
    "suggested_kind": "GENERATE",
    "port_spec": "clk, rst_n, winc, rinc -> wfull, rempty",
    "search_query": "fifo controller fsm"
  }
]

Keep names short and snake_case. Keep search_query 2-5 words. Output ONLY
the JSON array."""


def _extract_json_array(text: str):
    """Best-effort: strip fences, find the first balanced [...] and parse it."""
    cleaned = strip_code_fences(text).strip()
    # try direct parse
    try:
        v = json.loads(cleaned)
        if isinstance(v, list):
            return v
    except Exception:
        pass
    # find first '[' and walk forward looking for the matching ']'
    start = cleaned.find("[")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(cleaned)):
        c = cleaned[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                blob = cleaned[start:i + 1]
                try:
                    v = json.loads(blob)
                    if isinstance(v, list):
                        return v
                except Exception:
                    return None
    return None


def _fallback_single_block(spec_text: str) -> list:
    return [{
        "name": "TopModule",
        "role": "entire spec",
        "suggested_kind": "GENERATE",
        "port_spec": "(see spec)",
        "search_query": _short_query(spec_text),
    }]


def _short_query(spec_text: str) -> str:
    # crude keyword pull from the first ~200 chars
    head = re.sub(r"[^a-zA-Z0-9 ]+", " ", spec_text[:200]).lower()
    words = [w for w in head.split() if len(w) > 3][:5]
    return " ".join(words) or "verilog module"


def decompose(spec_text: str) -> list:
    """Return a list of subblock dicts. On any failure, return a single
    GENERATE block covering the whole spec."""
    prompt = PLANNER_SYSTEM + "\n\nSPEC:\n" + spec_text
    try:
        raw = call_claude(prompt)
    except Exception as e:
        print(f"[planner] claude call failed: {e}")
        return _fallback_single_block(spec_text)
    parsed = _extract_json_array(raw)
    if not parsed:
        print("[planner] could not extract JSON array; falling back")
        return _fallback_single_block(spec_text)
    # sanity-check / normalize fields
    out = []
    for i, sb in enumerate(parsed):
        if not isinstance(sb, dict):
            continue
        kind = str(sb.get("suggested_kind", "GENERATE")).upper()
        if kind not in ("REUSE_IP", "GENERATE"):
            kind = "GENERATE"
        out.append({
            "name": str(sb.get("name") or f"sub_{i}"),
            "role": str(sb.get("role") or ""),
            "suggested_kind": kind,
            "port_spec": str(sb.get("port_spec") or ""),
            "search_query": str(sb.get("search_query") or sb.get("name", "")),
        })
    return out or _fallback_single_block(spec_text)


if __name__ == "__main__":
    import sys
    spec = open(sys.argv[1]).read()
    blocks = decompose(spec)
    print(json.dumps(blocks, indent=2))
