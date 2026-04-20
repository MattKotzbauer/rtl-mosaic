# IP-Search MCP Server

Part of the SiliconMind harness. The system-level agent decomposes a chip
spec into subblocks and decides per subblock whether to reuse an off-the-shelf
IP or generate fresh Verilog with the LLM. This MCP server is the only way
the agent learns about the IP corpus.

## Tools exposed

- `ip_search(spec_text)` -> up to 5 candidate `{id, name, description, score, hint}`.
  Simple TF-style keyword scoring over name, description, category, and curated
  per-IP keywords. No embeddings.
- `ip_get_interface(ip_id)` -> `{name, id, category, description, params, ports,
  example_instantiation, license}`. **Never returns Verilog source.**
- `ip_instantiate(ip_id, instance_name, params, port_map)` -> Verilog
  instantiation snippet that the integrator pastes into the top-level wrapper.

## How the agent uses it

1. For each subblock spec, call `ip_search`.
2. If a strong candidate exists, call `ip_get_interface` to read its ports.
3. Call `ip_instantiate` with concrete params and port wiring.
4. The harness concatenates the matching `corpus/modules/<id>.sv` file into
   the build separately. The agent **never** receives the source.

## Why source is hidden

- **Interface cleanliness**: forces the agent to reason about ports/params,
  not implementation details. Mirrors how engineers consume vendor IP.
- **Scope**: keeps the agent's context focused on integration, not re-deriving
  internal logic that already passes verification.
- **Security/licensing**: in a real flow, IPs may be encrypted or under NDA.
  The MCP boundary models that constraint from day one.

## Running

```
python3 server.py        # FastMCP stdio server (or catalog dump fallback)
pytest test_mcp.py       # smoke tests
```

Catalog: `corpus/catalog.json`. Sources: `corpus/modules/*.sv` (loaded by the
harness, not by this server).
