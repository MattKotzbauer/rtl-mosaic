"""Codegen: ask Claude to write one synthesizable Verilog module."""
from harness._claude_cli import call_claude, strip_code_fences

CODEGEN_SYSTEM = """You are a hardware design expert. Generate ONE synthesizable
Verilog module implementing the spec below.

Rules:
- Output ONLY Verilog code. No markdown fences. No explanations.
- The module must be named exactly as requested.
- Use SystemVerilog-2012 features sparingly; iverilog -g2012 must compile it.
- No `include` directives, no testbenches, no $display.
"""


def generate_module(name: str, spec: str) -> str:
    """Call claude to produce a single named module's Verilog source."""
    prompt = (
        CODEGEN_SYSTEM
        + f"\n\nMODULE NAME (required): {name}\n\nSPEC:\n{spec}\n"
    )
    raw = call_claude(prompt)
    return strip_code_fences(raw).strip() + "\n"


if __name__ == "__main__":
    import sys
    print(generate_module(sys.argv[1], sys.argv[2]))
