"""IP router: turns a planner subblock into either an IP reuse or a generated
module. Talks to the (teammate's) MCP server via direct Python imports.

Falls back to a stub backed by `mcp/corpus/catalog.json` if `mcp.server` isn't
importable yet so we can still demo decomposition + IP routing.
"""
import json
import os
import re

from harness import codegen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, "mcp", "corpus")
CATALOG_PATH = os.path.join(CORPUS_DIR, "catalog.json")

# --- Try the teammate's MCP server first -----------------------------------
try:
    from mcp.server import ip_search, ip_get_interface, ip_instantiate  # type: ignore
    _USING_MCP = True
except Exception:
    _USING_MCP = False

    _CATALOG = None

    def _load_catalog():
        global _CATALOG
        if _CATALOG is None:
            try:
                with open(CATALOG_PATH) as f:
                    _CATALOG = json.load(f).get("ips", [])
            except Exception:
                _CATALOG = []
        return _CATALOG

    def _score(ip, query):
        q = query.lower()
        toks = set(re.findall(r"[a-z0-9]+", q))
        if not toks:
            return 0
        text = " ".join([
            ip.get("id", ""), ip.get("name", ""), ip.get("description", ""),
            " ".join(ip.get("keywords", [])), ip.get("category", ""),
        ]).lower()
        return sum(1 for t in toks if t in text)

    def ip_search(query: str):
        cat = _load_catalog()
        scored = [(ip, _score(ip, query)) for ip in cat]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"id": ip["id"], "name": ip.get("name", ip["id"]), "score": s}
                for ip, s in scored if s > 0]

    def ip_get_interface(ip_id: str):
        for ip in _load_catalog():
            if ip["id"] == ip_id:
                return {
                    "id": ip["id"],
                    "name": ip.get("name", ip["id"]),
                    "params": ip.get("params", []),
                    "ports": ip.get("ports", []),
                    "source_file": os.path.join(CORPUS_DIR, ip["source_file"]),
                }
        return None

    def ip_instantiate(ip_id: str, instance_name: str = None,
                       param_overrides: dict = None, port_map: dict = None):
        iface = ip_get_interface(ip_id)
        if iface is None:
            return None
        inst = instance_name or f"u_{ip_id}"
        params = []
        for p in iface.get("params", []):
            v = (param_overrides or {}).get(p["name"], p.get("default"))
            params.append(f".{p['name']}({v})")
        param_str = " #(" + ", ".join(params) + ")" if params else ""
        port_lines = []
        for p in iface.get("ports", []):
            wire = (port_map or {}).get(p["name"], p["name"])
            port_lines.append(f"    .{p['name']}({wire})")
        body = ",\n".join(port_lines)
        text = f"{ip_id}{param_str} {inst} (\n{body}\n);\n"
        return {
            "id": ip_id,
            "instance_name": inst,
            "instantiation": text,
            "source_file": iface["source_file"],
        }


# --- Public API -------------------------------------------------------------

def resolve_subblock(subblock: dict) -> dict:
    """Resolve one planner subblock to either an IP reuse or a generated module.

    Returns:
      {kind: "ip",  id, instantiation, source_file, name}   on REUSE_IP success
      {kind: "gen", name, source_text}                       otherwise
    """
    name = subblock.get("name", "sub")
    kind = subblock.get("suggested_kind", "GENERATE").upper()
    query = subblock.get("search_query") or subblock.get("role") or name

    if kind == "REUSE_IP":
        try:
            hits = ip_search(query) or []
        except Exception as e:
            print(f"[ip_router] ip_search failed for '{query}': {e}")
            hits = []
        if hits:
            top = hits[0]
            try:
                inst = ip_instantiate(top["id"], instance_name=f"u_{name}")
            except Exception as e:
                print(f"[ip_router] ip_instantiate failed: {e}")
                inst = None
            if inst:
                return {
                    "kind": "ip",
                    "name": name,
                    "id": top["id"],
                    "instantiation": inst["instantiation"],
                    "source_file": inst["source_file"],
                }
        # fall through to GENERATE
        print(f"[ip_router] no IP hit for '{query}'; generating instead")

    # GENERATE path
    spec = subblock.get("port_spec", "") + "\nRole: " + subblock.get("role", "")
    src = codegen.generate_module(name, spec)
    return {"kind": "gen", "name": name, "source_text": src}


def using_real_mcp() -> bool:
    return _USING_MCP


if __name__ == "__main__":
    import sys
    sb = json.loads(sys.argv[1])
    print(json.dumps(resolve_subblock(sb), indent=2))
