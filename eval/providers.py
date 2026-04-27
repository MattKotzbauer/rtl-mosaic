"""Multi-provider LLM adapters: claude CLI, OpenAI, Gemini, Bedrock (DeepSeek)."""
import os, subprocess, json, time
from openai import OpenAI
import boto3

_OPENAI = None
_BEDROCK = None
_GENAI_KEY = os.environ.get("GEMINI_API_KEY")


def _openai():
    global _OPENAI
    if _OPENAI is None:
        _OPENAI = OpenAI()
    return _OPENAI


def _bedrock():
    global _BEDROCK
    if _BEDROCK is None:
        _BEDROCK = boto3.client("bedrock-runtime", region_name="us-east-1")
    return _BEDROCK


SYSTEM = (
    "You are a hardware design expert. Generate synthesizable Verilog code. "
    "Output ONLY the Verilog code, no markdown fences, no explanation. "
    "The module MUST be named TopModule."
)


def call_claude_cli(model, prompt, timeout=300):
    full = SYSTEM + "\n\n" + prompt
    r = subprocess.run(
        ["claude", "-p", full, "--model", model, "--max-turns", "3"],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI: {r.stderr[:300]}")
    return r.stdout


def call_openai(model, prompt, timeout=300):
    c = _openai()
    is_reasoning = model.startswith(("o1", "o3", "o4")) or "codex" in model
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "timeout": timeout,
    }
    if not is_reasoning and not model.startswith("gpt-5"):
        kwargs["temperature"] = 0.0
    if model.startswith("gpt-5") or is_reasoning:
        kwargs["max_completion_tokens"] = 8000
    else:
        kwargs["max_tokens"] = 4000
    resp = c.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def call_gemini(model, prompt, timeout=300):
    import urllib.request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={_GENAI_KEY}"
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 8000},
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.loads(r.read())
    cands = d.get("candidates", [])
    if not cands:
        raise RuntimeError(f"Gemini empty: {json.dumps(d)[:300]}")
    parts = cands[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def call_bedrock(model_id, prompt, timeout=300):
    c = _bedrock()
    resp = c.converse(
        modelId=model_id,
        system=[{"text": SYSTEM}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 8000, "temperature": 0.0},
    )
    parts = resp["output"]["message"]["content"]
    text = "".join(p.get("text", "") for p in parts if "text" in p)
    return text


PROVIDERS = {
    # provider key -> (callable, model id used in CLI/API)
    "claude:opus-4-7":   (call_claude_cli, "claude-opus-4-7"),
    "claude:sonnet-4-6": (call_claude_cli, "claude-sonnet-4-6"),
    "claude:haiku-4-5":  (call_claude_cli, "claude-haiku-4-5"),
    "openai:gpt-5.4":    (call_openai, "gpt-5.4"),
    "openai:gpt-5.2":    (call_openai, "gpt-5.2"),
    "openai:gpt-5.1":    (call_openai, "gpt-5.1"),
    "openai:gpt-5":      (call_openai, "gpt-5"),
    "openai:gpt-4.1":    (call_openai, "gpt-4.1"),
    "bedrock:deepseek-r1": (call_bedrock, "us.deepseek.r1-v1:0"),
    "bedrock:deepseek-v3.2": (call_bedrock, "deepseek.v3.2"),
    "gemini:2.5-pro":             (call_gemini, "gemini-2.5-pro"),
    "gemini:2.5-flash":           (call_gemini, "gemini-2.5-flash"),
    "gemini:2.5-flash-lite":      (call_gemini, "gemini-2.5-flash-lite"),
    "gemini:3-flash-preview":     (call_gemini, "gemini-3-flash-preview"),
    "gemini:3.1-flash-lite-preview": (call_gemini, "gemini-3.1-flash-lite-preview"),
}


def call(provider_key, prompt, timeout=300):
    fn, mid = PROVIDERS[provider_key]
    return fn(mid, prompt, timeout=timeout)


if __name__ == "__main__":
    import sys, concurrent.futures
    keys = list(PROVIDERS.keys())
    HW = "Reply with exactly the Verilog: module TopModule(); endmodule"
    def test(k):
        t0 = time.time()
        try:
            out = call(k, HW, timeout=120)
            ok = "endmodule" in out.lower()
            return k, ok, time.time()-t0, out[:200]
        except Exception as e:
            return k, False, time.time()-t0, str(e)[:200]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(keys)) as ex:
        for k, ok, dt, snip in ex.map(test, keys):
            mark = "OK " if ok else "ERR"
            print(f"[{mark}] {k:32s} {dt:5.1f}s  {snip!r}")
