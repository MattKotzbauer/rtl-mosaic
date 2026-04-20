"""Tiny wrapper around the `claude` CLI used by planner / codegen / integrator."""
import subprocess

CLAUDE_BIN = "claude"
DEFAULT_MODEL = "claude-sonnet-4-6"


def call_claude(prompt: str, model: str = DEFAULT_MODEL, max_turns: int = 1,
                timeout: int = 180) -> str:
    """Run `claude -p <prompt> --model <model> --max-turns <n>` and return stdout.

    Raises RuntimeError on non-zero exit so callers can decide what to do.
    """
    result = subprocess.run(
        [CLAUDE_BIN, "-p", prompt, "--model", model, "--max-turns", str(max_turns)],
        capture_output=True, text=True, timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (rc={result.returncode}): {result.stderr[:300]}"
        )
    return result.stdout


def strip_code_fences(text: str) -> str:
    """Strip ```...``` fences if present, returning interior content."""
    lines = text.strip().splitlines()
    if not lines:
        return text
    if lines[0].strip().startswith("```"):
        # drop opening fence
        lines = lines[1:]
        # drop trailing fence if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
    # also handle case where fences appear mid-text
    out, in_fence = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        out.append(ln)
    return "\n".join(out)
