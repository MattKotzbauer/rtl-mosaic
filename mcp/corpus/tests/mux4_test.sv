`timescale 1ns/1ps
module mux4_test;
    localparam W = 8;
    reg  [W-1:0] in0, in1, in2, in3;
    reg  [1:0]   sel;
    wire [W-1:0] out;

    mux4 #(.WIDTH(W)) dut (.in0(in0), .in1(in1), .in2(in2), .in3(in3), .sel(sel), .out(out));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W-1:0] expected;

    initial begin
        in0 = 8'hA1; in1 = 8'hB2; in2 = 8'hC3; in3 = 8'hD4;
        for (i = 0; i < 4; i = i + 1) begin
            sel = i[1:0];
            #1;
            case (i)
                0: expected = in0;
                1: expected = in1;
                2: expected = in2;
                3: expected = in3;
            endcase
            total = total + 1;
            if (out !== expected) begin $display("MISMATCH(sel=%0d): out=%h exp=%h", sel, out, expected); mism = mism + 1; end
        end

        for (i = 0; i < 8; i = i + 1) begin
            in0 = $urandom & 8'hFF;
            in1 = $urandom & 8'hFF;
            in2 = $urandom & 8'hFF;
            in3 = $urandom & 8'hFF;
            sel = $urandom & 2'b11;
            #1;
            case (sel)
                2'd0: expected = in0;
                2'd1: expected = in1;
                2'd2: expected = in2;
                2'd3: expected = in3;
            endcase
            total = total + 1;
            if (out !== expected) begin $display("MISMATCH(rand sel=%0d): out=%h exp=%h", sel, out, expected); mism = mism + 1; end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
