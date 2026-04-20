# IP Corpus Plan — 50 Modules

## Status (intermediate, 2026-04-19)

| Bucket            | Count |
|-------------------|-------|
| Mocked for demo   | 5     |
| Planned (this doc)| 50    |
| Actually ingested | 0     |

The 5 mocked entries are hand-written stubs in `mcp/corpus/catalog.json` (sync FIFO, UART tx, mux2, single-port RAM, ripple adder) with toy port lists so the harness end-to-end works for tomorrow's demo. Everything below is the real plan to get to ~50 by week 3.

---

## 1. Sources Table

All URLs verified via `gh api` on 2026-04-19. License column reflects what the repo's `LICENSE` file actually says (the GitHub-detected SPDX is sometimes "NOASSERTION" because the file is hand-formatted Solderpad/Apache text).

| Source | URL | License | Lang | Usable small modules (rough) |
|--------|-----|---------|------|------------------------------|
| OpenTitan `prim_*` | https://github.com/lowRISC/opentitan/tree/master/hw/ip/prim/rtl | Apache-2.0 | SystemVerilog | ~50 prim files; ~25 are small/general (FIFOs, LFSR, edge_detector, CDC, arbiter, packer, onehot, count, CRC32) |
| OpenTitan `prim_generic` | https://github.com/lowRISC/opentitan/tree/master/hw/ip/prim_generic/rtl | Apache-2.0 | SystemVerilog | ~30 (RAM 1p/2p/1r1w, ROM, flop_2sync, rst_sync, clock_div, clock_mux2, gates) — these are the no-vendor versions |
| OpenTitan peripherals | https://github.com/lowRISC/opentitan/tree/master/hw/ip/{uart,i2c,spi_device}/rtl | Apache-2.0 | SystemVerilog | ~5 small leaf files (`uart_rx.sv`, `uart_tx.sv`, `spi_p2s.sv`, `spi_s2p.sv`); the `*_core.sv` and `*_reg_top.sv` are too big/registered for our purpose |
| pulp-platform `common_cells` | https://github.com/pulp-platform/common_cells | Solderpad-0.51 (option to be treated as Apache-2.0) | SystemVerilog | ~80 files in `src/`; ~40 small (fifo_v3, lfsr_8bit/16bit, gray<->binary, lzc, popcount, edge_detect, counter, shift_reg, spill_register, cdc_2phase, cdc_fifo_gray, rstgen, stream_mux/demux, onehot_to_bin) |
| pulp-platform `apb_uart` / `apb_spi_master` / `apb_i2c` | https://github.com/pulp-platform/apb_uart etc. | Solderpad | Verilog/SV | 1-3 leaf modules each; APB-wrapped, may need stripping |
| OH! library (Adapteva) | https://github.com/aolofsson/oh | MIT | Verilog-2005 | ~150 modules total. `stdlib/rtl/` has ~140 — most are tiny gates (`oh_and2`, `oh_mux2`...). Useful larger ones: `oh_fifo_sync`, `oh_fifo_async`, `oh_fifo_cdc`, `oh_lfsr`, `oh_dpram`, `oh_ram`, `oh_regfile`, `oh_par2ser`, `oh_ser2par`, `oh_clockdiv`, `oh_debouncer`, `oh_edge2pulse`, `oh_bin2gray`, `oh_gray2bin`, `oh_arbiter`, `oh_pll`, `oh_dsync`, `oh_rsync`, `oh_csa32/42` (carry-save adders), `oh_mult`, `oh_shift`. README warns "main branch is WIP, use Tag V1.0" — pin to that tag. |
| OH! peripherals | https://github.com/aolofsson/oh/tree/main/{spi,gpio,axi,emailbox} | MIT | Verilog | `spi_master.v`, `spi_slave.v`, `axi_spi.v`, `gpio.v`, `emaxi.v` (axi master), `esaxi.v` (axi slave), `emailbox.v` |
| Alex Forencich `verilog-uart` | https://github.com/alexforencich/verilog-uart | MIT | Verilog | 3 files: `uart.v`, `uart_rx.v`, `uart_tx.v` — clean, parameterized, no vendor deps |
| Alex Forencich `verilog-i2c` | https://github.com/alexforencich/verilog-i2c | MIT | Verilog | `i2c_master.v`, `i2c_slave.v`, plus AXIL/WB wrappers |
| Alex Forencich `verilog-axi` | https://github.com/alexforencich/verilog-axi | MIT | Verilog | ~50 files; useful small ones: `axi_register.v`, `axi_fifo.v`, `axi_ram.v`, `arbiter.v`, plus full crossbars (too big) |
| Alex Forencich `verilog-ethernet` | https://github.com/alexforencich/verilog-ethernet | MIT | Verilog | MAC/framing — pull `eth_mac_1g.v` or `eth_mac_phy_10g.v` style leaf only |
| dawsonjon FPU | https://github.com/dawsonjon/fpu | MIT | Verilog | One module per dir: `adder/adder.v`, `multiplier/multiplier.v`, `divider/`, `int_to_float/`, `float_to_int/`, `double_*` variants. Each a single file, ~200-400 lines. |
| secworks (Joachim Strömbergson) | https://github.com/secworks/{uart,sha256,aes,...} | BSD-2-Clause | Verilog | Audited, well-tested. `uart`, `aes`, `sha256`, `chacha`, `siphash`. |
| ZipCPU `wb2axip` | https://github.com/ZipCPU/wb2axip | (no LICENSE in root — Gisselquist Technology mixed; check per-file headers) | Verilog | Skip unless we confirm per-file license. Plenty of alternatives. |
| Chipyard | https://github.com/ucb-bar/chipyard | BSD-3-Clause | **Chisel** (mostly) | **EXCLUDE** — Chisel/Scala source. We need SystemVerilog/Verilog source, not generated SV. Generated SV is gnarly and not human-readable. |
| FreeChips / freecores GitHub mirrors | https://github.com/freecores | Mixed (mostly missing LICENSE files in mirror — `null`); originals on opencores.org carry LGPL/GPL/BSD per project | Verilog | Use cautiously. Check `COPYING.txt` per-project on opencores.org, not the GitHub mirror. |
| OpenCores (asicworld curated) | https://opencores.org | Mixed: GPL / LGPL / BSD / CERN-OHL | Verilog | 120 arithmetic, 223 comm, 52 memory projects. Filter to BSD/MIT/CERN-OHL-P only. |

**Key license takeaway:** OpenTitan (Apache-2.0), OH! (MIT), Forencich (MIT), dawsonjon (MIT), secworks (BSD-2) cover almost all of our needs with permissive licenses. PULP common_cells is Solderpad-0.51, which the license text itself says can be treated as Apache-2.0 — also fine. Avoid GPL/LGPL OpenCores mirrors unless we cite carefully.

---

## 2. Curated 50-module Shortlist

For each row: candidate file (verified to exist as of 2026-04-19), source repo, why it's a good pick. "verified" means the file name was confirmed via `gh api .../contents`. Where I'm not 100% sure of exact path inside a repo's nested structure, I say "look for X in repo Y".

### Memory / storage (12)

| # | Module | Source | Why pick |
|---|--------|--------|----------|
| 1 | sync FIFO | `pulp-platform/common_cells/src/fifo_v3.sv` | The canonical pulp FIFO. Parameterized depth/width. Solderpad. |
| 2 | sync FIFO (alt) | `lowRISC/opentitan/hw/ip/prim/rtl/prim_fifo_sync.sv` | Apache-2.0, pure SV, no vendor primitives. |
| 3 | async FIFO | `lowRISC/opentitan/hw/ip/prim/rtl/prim_fifo_async.sv` | Gray-coded CDC FIFO, Apache-2.0. |
| 4 | async FIFO (alt) | `pulp-platform/common_cells/src/cdc_fifo_gray.sv` | Backup if OpenTitan version pulls too many deps. |
| 5 | dual-port RAM | `lowRISC/opentitan/hw/ip/prim_generic/rtl/prim_ram_2p.sv` | Generic (no vendor) inferrable BRAM. |
| 6 | single-port RAM | `lowRISC/opentitan/hw/ip/prim_generic/rtl/prim_ram_1p.sv` | Same — no `XPM`/`altsyncram`. |
| 7 | 1R1W RAM | `lowRISC/opentitan/hw/ip/prim_generic/rtl/prim_ram_1r1w.sv` | Common pattern, one read + one write port. |
| 8 | register file | `aolofsson/oh/stdlib/rtl/oh_regfile.v` | Tiny, MIT. |
| 9 | LIFO / stack | Build from `prim_ram_1p` + counter, OR look in `pulp/common_cells` for a `stack`/`ring_buffer.sv` (verified: `ring_buffer.sv` exists). | Closest off-the-shelf option. |
| 10 | shift register | `pulp-platform/common_cells/src/shift_reg.sv` | Parameterized depth, Solderpad. |
| 11 | ROM | `lowRISC/opentitan/hw/ip/prim_generic/rtl/prim_rom.sv` | Parameterized depth. Note: needs init array — flag this in catalog. |
| 12 | CAM (content-addressable mem) | OpenCores has small CAMs; specifically search opencores.org "small_cam" or "tcam" projects under BSD. Otherwise hand-write — CAMs are short. | Will check before ingest. Mark TODO. |

### Arithmetic (12)

| # | Module | Source | Why pick |
|---|--------|--------|----------|
| 13 | ripple-carry adder | `aolofsson/oh/stdlib/rtl/oh_add.v` | Plain, MIT. |
| 14 | carry-lookahead adder | OpenCores `cla_adder` projects, BSD-licensed only. Or hand-roll — CLA is ~50 lines. | Multiple BSD CLA cores exist on opencores. |
| 15 | carry-save adder | `aolofsson/oh/stdlib/rtl/oh_csa32.v` (3:2 CSA) and `oh_csa42.v` (4:2) | MIT, drop-in. |
| 16 | Booth multiplier | OpenCores "booth multiplier" (filter for BSD). Several available. | Mark TODO until ingestion. |
| 17 | Wallace-tree multiplier | OpenCores "wallace tree". Or hand-roll from `oh_csa42` ladder. | TODO. |
| 18 | basic multiplier | `aolofsson/oh/stdlib/rtl/oh_mult.v` | MIT, simple. |
| 19 | divider (integer) | OpenCores `serial_divider` (BSD), or PULP `pulp-platform/serdiv` if license OK. | Verify license. |
| 20 | sqrt | OpenCores `sqrt` projects (various, mostly LGPL — careful) | Filter or hand-roll Newton. |
| 21 | FP adder | `dawsonjon/fpu/adder/adder.v` | MIT, single file, IEEE-754 single. |
| 22 | FP multiplier | `dawsonjon/fpu/multiplier/multiplier.v` | MIT, same family. |
| 23 | int-to-float | `dawsonjon/fpu/int_to_float/int_to_float.v` | MIT. |
| 24 | log2 / leading-zero count | `pulp-platform/common_cells/src/lzc.sv` | Solderpad, parameterized width. |

### Comm / serial (10)

| # | Module | Source | Why pick |
|---|--------|--------|----------|
| 25 | UART tx | `alexforencich/verilog-uart/rtl/uart_tx.v` | MIT, ~100 lines, parameterized prescaler. |
| 26 | UART rx | `alexforencich/verilog-uart/rtl/uart_rx.v` | MIT. |
| 27 | UART tx (alt) | `lowRISC/opentitan/hw/ip/uart/rtl/uart_tx.sv` | Apache-2.0 backup; uses OT register conventions, slight glue needed. |
| 28 | SPI master | `aolofsson/oh/spi/hdl/spi_master.v` | MIT, well-structured. |
| 29 | SPI slave | `aolofsson/oh/spi/hdl/spi_slave.v` | MIT, matches the master above. |
| 30 | I2C master | `alexforencich/verilog-i2c/rtl/i2c_master.v` | MIT, clean. |
| 31 | I2C slave | `alexforencich/verilog-i2c/rtl/i2c_slave.v` | MIT, matches. |
| 32 | AXI-Lite slave | `alexforencich/verilog-axi/rtl/axi_register.v` (AXI4 register slice; works as minimal slave) | MIT. For pure AXI-Lite, check `axil_*.v` files in same repo. |
| 33 | AXI-Lite master | `aolofsson/oh/axi/hdl/emaxi.v` (epiphany-mesh AXI master) | MIT. Slightly opinionated naming, but small. |
| 34 | Ethernet MAC framing | `alexforencich/verilog-ethernet` — leaf framer (e.g. `eth_axis_rx.v`/`eth_axis_tx.v`) | MIT. Pick smallest leaf, not full MAC. |

(USB: skipping. The freecores `usb1_funct` mirror has no LICENSE detected and the original opencores project is LGPL. Not worth the headache for this corpus. If we need USB, document gap and replace with a 10th comm module like `axis_async_fifo.v` from Forencich.)

### Control / datapath (10)

| # | Module | Source | Why pick |
|---|--------|--------|----------|
| 35 | mux2 | `aolofsson/oh/stdlib/rtl/oh_mux2.v` | MIT, trivial. |
| 36 | mux4 | `aolofsson/oh/stdlib/rtl/oh_mux4.v` | MIT. |
| 37 | mux8 | `aolofsson/oh/stdlib/rtl/oh_mux8.v` | MIT. |
| 38 | demux / 1-to-N stream demux | `pulp-platform/common_cells/src/stream_demux.sv` | Solderpad. Slightly more than a pure demux (handshake), but parameterized. |
| 39 | priority encoder / arbiter | `pulp-platform/common_cells/src/rr_arb_tree.sv` (round-robin) and `lowRISC/opentitan/.../prim_arbiter_tree.sv` | Both well-tested. |
| 40 | binary decoder | `aolofsson/oh/stdlib/rtl/oh_bin2onehot.v` | MIT. |
| 41 | comparator | Hand-roll or use `pulp/common_cells` `addr_decode.sv` (does range comparison). | `==`/`<` modules are usually trivial. |
| 42 | barrel shifter | `aolofsson/oh/stdlib/rtl/oh_shift.v` | MIT. |
| 43 | edge detector | `lowRISC/opentitan/hw/ip/prim/rtl/prim_edge_detector.sv` | Apache-2.0. Or `oh_edge2pulse.v` (MIT) as alt. |
| 44 | debouncer | `aolofsson/oh/stdlib/rtl/oh_debouncer.v` | MIT. |
| 45 | FSM template | Hand-write a 3-state Moore template + 3-state Mealy template. No good "generic FSM" module exists — these are bespoke per-design. Catalog as code skeletons rather than IP. | N/A |
| 46 | glitch filter | `pulp-platform/common_cells/src/serial_deglitch.sv` | Solderpad. |

### Misc (6)

| # | Module | Source | Why pick |
|---|--------|--------|----------|
| 47 | clock divider | `aolofsson/oh/stdlib/rtl/oh_clockdiv.v` | MIT. Pure RTL divider (divides by integer), no PLL. |
| 48 | PLL wrapper stub | `aolofsson/oh/stdlib/rtl/oh_pll.v` | MIT. **Stub only** — real PLLs are vendor IP; this is a sim-only behavioral model. Mark explicitly in catalog. |
| 49 | sync-CDC reset / rst gen | `pulp-platform/common_cells/src/rstgen.sv` | Solderpad. Async-assert sync-deassert reset generator. |
| 50 | gray-code counter | `pulp-platform/common_cells/src/binary_to_gray.sv` + `gray_to_binary.sv` (build the counter from these + `counter.sv`). Or `aolofsson/oh/stdlib/rtl/oh_bin2gray.v`. | MIT/Solderpad. |
| 51 | LFSR | `lowRISC/opentitan/hw/ip/prim/rtl/prim_lfsr.sv` (Apache-2.0, parameterized poly width) and `pulp-platform/common_cells/src/lfsr.sv` as alt | Two strong choices. |
| 52 | CRC | `lowRISC/opentitan/hw/ip/prim/rtl/prim_crc32.sv` | Apache-2.0, fixed CRC-32. For other polynomials, OpenCores has BSD-licensed CRC generators. |

That's 52 — gives 2 of slack for ones that fall out during ingest review (CAM and the FSM template are the most likely casualties).

---

## 3. Filter Criteria

A module gets into `catalog.json` only if all of these hold:

- **Small**: under 300 lines of Verilog/SV. Big modules pull in too many sub-deps and the LLM struggles to use them as a unit.
- **No vendor primitives**: no `BUFG`, `XPM_*`, `altsyncram`, `IBUFDS`, `MMCME2_ADV`, etc. We want generic inferrable RTL.
- **No `$readmemh` for default behavior**: ROMs that need an init file are OK only if we can pass a synthesizable default array as a parameter.
- **Parameterized**: width, depth, polarity should be `parameter`s, not hardcoded — gives the harness flexibility when composing.
- **Single-purpose**: one clear function. A 280-line file that's "UART + register interface + DMA" gets rejected; pull just the UART core.
- **Permissive license**: MIT / BSD-2 / BSD-3 / Apache-2.0 / Solderpad-0.51 / CC0 only. No GPL, no LGPL (linking ambiguity in HDL is a mess), no CERN-OHL-S (strong reciprocal).
- **No internal `include` chains we can't resolve**: prefer self-contained files. If a file depends on `prim_assert.sv` or similar, document and bundle the dep.
- **Synthesizable for both Verilator and Yosys**: no `$random` in main logic, no `disable fork`, no `interface` (Yosys doesn't fully support SV interfaces).

---

## 4. Ingestion Plan

Pipeline from raw repo to catalog entry:

1. **Clone** each source repo into `corpus_raw/` (gitignored). Pin to a known-good commit/tag (e.g. OH! Tag V1.0, OpenTitan latest stable).
2. **Per-module extract**, scripted in `tools/ingest.py`:
   - Read the file. Parse the `module ... endmodule` block (regex on the module declaration; for SV interfaces, fall back to a real parser like `pyverilog` if needed).
   - Pull header comment block (everything between top-of-file and `module` keyword) — usually has author/license/description.
   - Parse the port list — names, directions, widths. Store as JSON.
   - Count lines, check filter criteria, flag failures.
3. **Generate one-line description**: send the header comment + port list to Claude Haiku 4.5 (charge to Claude Code credits, not direct API), prompt: "In one sentence, describe what this Verilog module does. Be concrete about its interface."
4. **Write entry** to `mcp/corpus/catalog.json`:
   ```json
   {
     "name": "prim_fifo_sync",
     "category": "memory",
     "source_repo": "lowRISC/opentitan",
     "source_path": "hw/ip/prim/rtl/prim_fifo_sync.sv",
     "license": "Apache-2.0",
     "description": "Synchronous FIFO with parameterized depth and width...",
     "ports": [...],
     "params": [...],
     "lines": 245,
     "deps": ["prim_assert.sv"]
   }
   ```
5. **Manual review** each entry: read description, check the LLM didn't hallucinate ports. ~5 min/module if the script does the heavy lifting; ~30 min/module if mostly manual.

**Estimate**: with the pipeline, one focused day to ingest all 50. Without, ~25 hours of manual review. Plan for the day-of-script effort.

---

## 5. Risks

- **Interface mismatch is the big one.** Real IP from different repos uses different handshake conventions: ready/valid (PULP), valid-only with backpressure elsewhere, AXI-Stream, Wishbone, custom epiphany-mesh. The harness will need an adapter layer. Plan: tag each module with its interface protocol in `catalog.json`, and have the harness reject compositions that mix protocols without an adapter. Document 3-4 standard adapters (valid/ready ↔ AXI-Lite, Wishbone ↔ valid/ready) as separate corpus entries.

- **Licensing landmines on OpenCores.** The github `freecores/*` mirrors mostly have their LICENSE field detected as `null` because the mirror dropped the file. Always check the original opencores.org project page's `COPYING.txt`. Many "open" cores are actually LGPL or GPL — would force us to release derivative chips under the same terms. Filter strictly to BSD/MIT/CC0/CERN-OHL-P. When in doubt, drop.

- **Simulator portability.** Some modules (especially older OpenCores stuff) assume Icarus quirks; some PULP code uses SV constructs Verilator chokes on (`always_comb` with `unique case` and missing default). We'll need a CI step that runs each module through Verilator with `--lint-only` before accepting into the corpus.

- **Vendor-locked primitives.** Xilinx XPM, Altera megafunctions, Lattice IP — exclude entirely. The OpenTitan tree is structured to make this easy: take from `prim_generic/rtl/`, NOT from `prim_xilinx/` or `prim_intel/`.

- **OH! main branch is broken.** README explicitly says "main is WIP, use Tag V1.0." Pin to that tag in our clone script.

- **Chisel-generated SV.** Chipyard, Rocket, BOOM are Chisel/Scala. Generated SV is human-hostile (mangled names, no comments). Excluded from corpus.

- **`prim_assert.sv` and friends.** OpenTitan's prim files include a small support package. Either bundle it into our corpus as a "pkg" entry, or strip the `` `include `` and provide stubs.

- **Dependency cycles.** A few common_cells modules depend on each other (`stream_fifo` uses `fifo_v3` uses `cf_math_pkg`). Track deps in catalog, ingest the leaves first.

---

## Quick checklist for tomorrow's intermediate slide

- "5 mocked, 50 planned, 0 ingested" — the truth, don't oversell.
- Show the sources table. The license column is the credibility lift.
- Show 2-3 example planned entries (sync FIFO from OpenTitan, UART tx from Forencich, FP add from dawsonjon) as proof we know exactly which files we want.
- Mention the interface-mismatch risk and that we'll need an adapter layer — HT will ask about this.
