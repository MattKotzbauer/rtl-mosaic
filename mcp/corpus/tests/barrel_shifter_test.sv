`timescale 1ns/1ps
module barrel_shifter_test;
    localparam W = 8;
    reg  [W-1:0] in;
    reg  [$clog2(W)-1:0] shift_amt;
    reg  [1:0]   op;
    wire [W-1:0] out;

    barrel_shifter #(.WIDTH(W)) dut (.in(in), .shift_amt(shift_amt), .op(op), .out(out));

    integer mism = 0;
    integer total = 0;
    integer i, s;
    reg [W-1:0] expected;
    reg signed [W-1:0] signed_in;

    initial begin
        // SHL across all shift amounts on a fixed pattern
        in = 8'b1010_0011;
        op = 2'b00;
        for (s = 0; s < W; s = s + 1) begin
            shift_amt = s[$clog2(W)-1:0];
            expected = in << shift_amt;
            #1;
            total = total + 1;
            if (out !== expected) begin
                $display("MISMATCH(SHL s=%0d): in=%h out=%h exp=%h", s, in, out, expected);
                mism = mism + 1;
            end
        end

        // SHR across all shift amounts
        op = 2'b01;
        for (s = 0; s < W; s = s + 1) begin
            shift_amt = s[$clog2(W)-1:0];
            expected = in >> shift_amt;
            #1;
            total = total + 1;
            if (out !== expected) begin
                $display("MISMATCH(SHR s=%0d): in=%h out=%h exp=%h", s, in, out, expected);
                mism = mism + 1;
            end
        end

        // SAR with sign bit set
        op = 2'b10;
        in = 8'b1010_0011;
        signed_in = in;
        for (s = 0; s < W; s = s + 1) begin
            shift_amt = s[$clog2(W)-1:0];
            expected  = signed_in >>> shift_amt;
            #1;
            total = total + 1;
            if (out !== expected) begin
                $display("MISMATCH(SAR s=%0d): in=%h out=%h exp=%h", s, in, out, expected);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
