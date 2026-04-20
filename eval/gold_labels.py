"""Hand-labeled gold ground truth for routing-eval on the ChipBench cpu_ip set.

For each of the 9 RISC-V CPU IP problems, we record:
  - expected_subblocks : list[str]
        IP IDs (from `mcp/corpus/catalog.json`) that a sensible planner+router
        ought to reuse from the corpus.  May be empty when nothing in the corpus
        actually fits.
  - expected_kinds : dict[str, str]
        Maps a *role label* (a short, human-readable subblock name) to either
        "REUSE_IP" or "GENERATE".  This is what we compare against the planner's
        own kind decisions, by best-effort name matching (see test_routing.py).
  - rationale : str
        One-line explanation of why the labels look the way they do.

The labels reference IP ids drawn from the *full* 20-IP corpus described in the
project plan, not just the 5 currently in the catalog.  As the catalog grows,
the same labels will start scoring better -- there's no need to edit this file.
The current target ID set (alphabetical):
    async_fifo, barrel_shifter, cla_adder, comparator, decoder_3to8,
    down_counter, dual_port_ram, edge_detector, mux2, mux4, mux8,
    priority_encoder, register_file, ripple_adder, shift_register,
    sign_extend, single_port_ram, subtractor, sync_fifo, up_counter
"""

from typing import TypedDict


class GoldEntry(TypedDict):
    expected_subblocks: list[str]
    expected_kinds: dict[str, str]
    rationale: str


GOLD: dict[str, GoldEntry] = {
    "Prob001_controller": {
        # 7-bit opcode -> ~9 control signals. The decoding shape doesn't match
        # decoder_3to8 (3->8) so honestly nothing in the 20-IP corpus fits.
        "expected_subblocks": [],
        "expected_kinds": {
            "opcode_decoder":  "GENERATE",
            "control_signals": "GENERATE",
        },
        "rationale": "controller decodes 7-bit opcode into ~9 control signals -- pure combinational case logic, mostly bespoke; the corpus decoder_3to8 doesn't fit a 7->N shape so nothing reusable.",
    },

    "Prob002_alu": {
        # 32-bit ALU with ADD, SUB, shifts, comparisons, logical ops, mux out.
        "expected_subblocks": [
            "cla_adder", "subtractor", "barrel_shifter", "comparator", "mux8",
        ],
        "expected_kinds": {
            "adder":          "REUSE_IP",
            "subtractor":     "REUSE_IP",
            "shifter":        "REUSE_IP",
            "comparator":     "REUSE_IP",
            "result_mux":     "REUSE_IP",
            "logical_ops":    "GENERATE",
            "control_decode": "GENERATE",
        },
        "rationale": "ALU naturally factors into adder + subtractor + barrel_shifter + comparator with a wide output mux; AND/OR/EQUAL-style ops are trivial bespoke logic.",
    },

    "Prob003_RegFile": {
        # 32x32 register file with 2R+1W. Corpus register_file is 16x32 with
        # 4-bit addresses so widths don't match exactly, but the IP is clearly
        # the right architectural fit and a planner should identify it.
        "expected_subblocks": ["register_file"],
        "expected_kinds": {
            "register_file": "REUSE_IP",
        },
        "rationale": "32-entry 32-bit 2R/1W register file -- corpus register_file is the same architecture (just 16-entry default), planner should pick it and width/depth params should grow.",
    },

    "Prob004_Branch_Unit": {
        # PC+Imm, PC+4, mux on JalrSel between AluResult and PC_Imm.
        "expected_subblocks": ["ripple_adder", "cla_adder", "mux2"],
        "expected_kinds": {
            "pc_plus_imm":   "REUSE_IP",
            "pc_plus_four":  "REUSE_IP",
            "br_target_mux": "REUSE_IP",
            "pc_sel_logic":  "GENERATE",
        },
        "rationale": "branch unit is two 32-bit adders (PC+Imm, PC+4) plus a 2:1 mux selecting BrPC; the only bespoke piece is the trivial PcSel = Branch wire.",
    },

    "Prob005_ALU_Controller": {
        # ALUOp(2) + Funct7(7) + Funct3(3) -> Operation(4) is a custom case.
        "expected_subblocks": [],
        "expected_kinds": {
            "alu_op_decode": "GENERATE",
        },
        "rationale": "RISC-V ALU controller is a bespoke nested case on ALUOp/Funct3/Funct7 -- no off-the-shelf decoder shape in the corpus matches.",
    },

    "Prob006_PC_REG": {
        # 32-bit PC register with reset/stall/flush/branch source mux.
        "expected_subblocks": ["mux4"],
        "expected_kinds": {
            "pc_source_mux": "REUSE_IP",
            "pc_register":   "GENERATE",
            "ce_logic":      "GENERATE",
        },
        "rationale": "PC update logic picks among {sequential PC+4, new_pc on flush, branch_target on branch, hold on stall} -- a 4:1 mux feeds a flop; the flop and ce/stall glue are bespoke.",
    },

    "Prob007_div": {
        # Sequential shift-and-subtract divider with FSM.
        "expected_subblocks": ["subtractor", "shift_register"],
        "expected_kinds": {
            "subtractor":      "REUSE_IP",
            "shift_register":  "REUSE_IP",
            "div_fsm":         "GENERATE",
            "sign_handling":   "GENERATE",
            "result_assemble": "GENERATE",
        },
        "rationale": "shift-and-subtract divider naturally uses a subtractor and a shift register inside a custom FSM; sign conversion and the {rem,quot} packing are bespoke.",
    },

    "Prob008_chapter12_ctrl": {
        # Pipeline stall/flush controller: pure combinational case logic.
        "expected_subblocks": [],
        "expected_kinds": {
            "exception_decode": "GENERATE",
            "stall_logic":      "GENERATE",
        },
        "rationale": "pipeline ctrl is a flat case on excepttype_i + stallreq_* signals producing fixed bit-patterns -- no corpus IP shape matches this kind of dispatch table.",
    },

    "Prob009_cp0_reg": {
        # CP0 register bank: a register file plus a free-running counter and a
        # count==compare equality check.
        "expected_subblocks": ["up_counter", "comparator", "register_file"],
        "expected_kinds": {
            "count_register":   "REUSE_IP",
            "timer_compare":    "REUSE_IP",
            "cp0_reg_bank":     "REUSE_IP",
            "exception_update": "GENERATE",
            "read_mux":         "GENERATE",
        },
        "rationale": "CP0 has a free-running count_o (up_counter), a count==compare check (comparator), and a small bank of named 32-bit registers (register_file-shaped); exception/ERET/IP-field updates are bespoke.",
    },
}


def all_problem_ids() -> list[str]:
    return list(GOLD.keys())


if __name__ == "__main__":
    import json
    print(json.dumps(GOLD, indent=2))
    print(f"\n{len(GOLD)} gold labels.")
