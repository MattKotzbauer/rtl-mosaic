"""Smoke tests for the IP-search MCP server."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from server import (
    ip_get_interface,
    ip_instantiate,
    ip_search,
)

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"


def test_search_async_fifo_for_cdc():
    results = ip_search("a fifo for crossing clock domains")
    assert results, "expected at least one search hit"
    ids = [r["id"] for r in results]
    assert "async_fifo" in ids
    # async_fifo should outrank sync_fifo for this query
    assert ids.index("async_fifo") <= ids.index("sync_fifo") if "sync_fifo" in ids else True


def test_search_returns_at_most_five():
    results = ip_search("memory buffer counter mux register fifo")
    assert len(results) <= 5
    for r in results:
        assert {"id", "name", "description", "score", "hint"} <= set(r)


def test_get_interface_no_source_leak():
    iface = ip_get_interface("sync_fifo")
    assert iface["id"] == "sync_fifo"
    assert "ports" in iface and isinstance(iface["ports"], list)
    assert iface["ports"], "ports should be non-empty"
    # Hard requirement: no source code keys
    forbidden = {"verilog", "source", "source_code", "rtl", "body"}
    assert not (forbidden & set(iface.keys())), f"interface leaked source keys: {iface.keys()}"
    # And no full module body in any string value
    for v in iface.values():
        if isinstance(v, str):
            assert "endmodule" not in v
            assert "always @" not in v


def test_get_interface_unknown_id():
    with pytest.raises(KeyError):
        ip_get_interface("does_not_exist")


def test_instantiate_format_sync_fifo():
    snippet = ip_instantiate(
        "sync_fifo",
        "u_fifo",
        params={"WIDTH": 8, "DEPTH": 16},
        port_map={
            "clk": "clk", "rst": "rst",
            "wr_en": "fifo_wr", "rd_en": "fifo_rd",
            "din": "fifo_din", "dout": "fifo_dout",
            "full": "fifo_full", "empty": "fifo_empty",
        },
    )
    # Basic shape checks
    assert snippet.startswith("sync_fifo #(")
    assert ".WIDTH(8)" in snippet
    assert ".DEPTH(16)" in snippet
    assert "u_fifo" in snippet
    assert snippet.rstrip().endswith(");")
    # Each port wired
    for port in ("clk", "rst", "wr_en", "rd_en", "din", "dout", "full", "empty"):
        assert re.search(rf"\.{port}\(", snippet), f"port {port} missing in snippet"


def test_instantiate_defaults_omitted_ports():
    snippet = ip_instantiate("up_counter", "u_cnt", params={"WIDTH": 4}, port_map={"q": "count"})
    assert ".q(count)" in snippet
    # omitted ports should map to same-name nets
    assert ".clk(clk)" in snippet
    assert ".rst(rst)" in snippet
    assert ".en(en)" in snippet


def test_instantiate_rejects_unknown_param_or_port():
    with pytest.raises(ValueError):
        ip_instantiate("mux4", "u_m", params={"NOPE": 1})
    with pytest.raises(ValueError):
        ip_instantiate("mux4", "u_m", port_map={"not_a_port": "x"})


def test_catalog_files_exist():
    catalog = json.loads((CORPUS_DIR / "catalog.json").read_text())["ips"]
    assert len(catalog) == 5
    for entry in catalog:
        sv_path = CORPUS_DIR / entry["source_file"]
        assert sv_path.exists(), f"missing source file {sv_path}"
        text = sv_path.read_text()
        assert f"module {entry['id']}" in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
