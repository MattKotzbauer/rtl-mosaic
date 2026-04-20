"""IP-search MCP server for the SiliconMind harness.

Exposes three tools:
  - ip_search(spec_text)           keyword/TF scoring over the catalog
  - ip_get_interface(ip_id)        port/parameter info, NO source code
  - ip_instantiate(...)            Verilog instantiation snippet

The agent never sees IP source code via this server. The harness concatenates
source files separately based on the ip_id chosen.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
CATALOG_PATH = CORPUS_DIR / "catalog.json"

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "for", "with", "to", "in", "on",
    "is", "are", "be", "this", "that", "it", "we", "i", "need", "want",
    "module", "block", "design", "use", "using",
}


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if t.lower() not in _STOPWORDS]


def _load_catalog() -> list[dict[str, Any]]:
    with CATALOG_PATH.open() as f:
        return json.load(f)["ips"]


def _score(query_tokens: list[str], entry: dict[str, Any]) -> float:
    """Simple TF-style score over name + description + keywords."""
    bag = []
    bag.extend(_tokenize(entry.get("name", "")))
    bag.extend(_tokenize(entry.get("description", "")))
    bag.extend(_tokenize(entry.get("category", "")))
    bag.extend(_tokenize(entry.get("id", "")))
    for kw in entry.get("keywords", []):
        bag.extend(_tokenize(kw))
        # Multi-word keyword phrase bonus: if the whole phrase appears in the
        # query string, boost a lot.
    counts = Counter(bag)

    score = 0.0
    for tok in query_tokens:
        if tok in counts:
            score += 1.0 + 0.1 * counts[tok]

    # Phrase bonuses for multi-word keywords
    qtext = " " + " ".join(query_tokens) + " "
    for kw in entry.get("keywords", []):
        kw_norm = " ".join(_tokenize(kw))
        if kw_norm and (" " + kw_norm + " ") in qtext:
            score += 2.0

    return score


def ip_search(spec_text: str) -> list[dict[str, Any]]:
    """Return up to 5 candidate IPs ranked by keyword relevance.

    Each result: {id, name, description, score, hint}. No source code.
    """
    catalog = _load_catalog()
    qtoks = _tokenize(spec_text)
    scored = [(_score(qtoks, e), e) for e in catalog]
    scored = [(s, e) for s, e in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)

    out = []
    for score, e in scored[:5]:
        # Build a short relevance hint: which query tokens matched
        matched = sorted({t for t in qtoks if t in (
            _tokenize(e["name"]) + _tokenize(e["description"]) +
            [w for kw in e.get("keywords", []) for w in _tokenize(kw)] +
            _tokenize(e["id"]) + _tokenize(e["category"])
        )})
        out.append({
            "id": e["id"],
            "name": e["name"],
            "description": e["description"],
            "score": round(score, 3),
            "hint": "matched: " + ", ".join(matched) if matched else "weak match",
        })
    return out


def _example_instantiation(entry: dict[str, Any]) -> str:
    """Build a canonical example instantiation string with default params."""
    pname = entry["id"]
    inst = f"u_{pname}"
    param_str = ", ".join(
        f".{p['name']}({p['default']})" for p in entry.get("params", [])
    )
    port_lines = []
    for p in entry["ports"]:
        # Use the port name as the placeholder net name in the example
        port_lines.append(f"    .{p['name']}({p['name']})")
    ports_block = ",\n".join(port_lines)
    if param_str:
        head = f"{pname} #({param_str}) {inst} (\n"
    else:
        head = f"{pname} {inst} (\n"
    return head + ports_block + "\n);"


def ip_get_interface(ip_id: str) -> dict[str, Any]:
    """Return interface info for an IP. NO source code, ever."""
    catalog = _load_catalog()
    for e in catalog:
        if e["id"] == ip_id:
            return {
                "name": e["name"],
                "id": e["id"],
                "category": e["category"],
                "description": e["description"],
                "params": e.get("params", []),
                "ports": e["ports"],
                "example_instantiation": _example_instantiation(e),
                "license": e.get("license", "unknown"),
            }
    raise KeyError(f"unknown ip_id: {ip_id}")


def ip_instantiate(
    ip_id: str,
    instance_name: str,
    params: dict[str, Any] | None = None,
    port_map: dict[str, str] | None = None,
) -> str:
    """Produce a Verilog instantiation snippet for the given IP.

    params:    {PARAM_NAME: value}    -> rendered as #(.PARAM(value), ...)
    port_map:  {port_name: net_name}  -> rendered as .port(net), ...
               Ports omitted from port_map are wired to a same-name net.
    """
    catalog = _load_catalog()
    entry = next((e for e in catalog if e["id"] == ip_id), None)
    if entry is None:
        raise KeyError(f"unknown ip_id: {ip_id}")

    params = params or {}
    port_map = port_map or {}

    # Validate params
    valid_params = {p["name"] for p in entry.get("params", [])}
    for k in params:
        if k not in valid_params:
            raise ValueError(f"unknown parameter '{k}' for {ip_id}")

    # Validate ports
    valid_ports = {p["name"] for p in entry["ports"]}
    for k in port_map:
        if k not in valid_ports:
            raise ValueError(f"unknown port '{k}' for {ip_id}")

    # Render parameters
    if params:
        param_str = ", ".join(f".{k}({v})" for k, v in params.items())
        head = f"{ip_id} #({param_str}) {instance_name} (\n"
    else:
        head = f"{ip_id} {instance_name} (\n"

    # Render ports in declared order
    port_lines = []
    for p in entry["ports"]:
        net = port_map.get(p["name"], p["name"])
        port_lines.append(f"    .{p['name']}({net})")
    return head + ",\n".join(port_lines) + "\n);"


# ---------------------------------------------------------------------------
# MCP wiring (FastMCP if available, otherwise a plain stub for testing).
# ---------------------------------------------------------------------------

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore

    mcp = FastMCP("silicon-mind-ip-search")

    @mcp.tool()
    def ip_search_tool(spec_text: str) -> list[dict[str, Any]]:
        """Search the IP catalog for modules matching a spec description."""
        return ip_search(spec_text)

    @mcp.tool()
    def ip_get_interface_tool(ip_id: str) -> dict[str, Any]:
        """Return the port/parameter interface for an IP. No source code."""
        return ip_get_interface(ip_id)

    @mcp.tool()
    def ip_instantiate_tool(
        ip_id: str,
        instance_name: str,
        params: dict[str, Any] | None = None,
        port_map: dict[str, str] | None = None,
    ) -> str:
        """Render a Verilog instantiation snippet for the given IP."""
        return ip_instantiate(ip_id, instance_name, params, port_map)

    def main() -> None:
        mcp.run()

except Exception:  # pragma: no cover - fallback path
    mcp = None  # type: ignore[assignment]

    def main() -> None:
        catalog = _load_catalog()
        print("[silicon-mind-ip-search] FastMCP unavailable; printing catalog.")
        for e in catalog:
            print(f"  - {e['id']:<14} {e['category']:<8} {e['description']}")


if __name__ == "__main__":
    main()
