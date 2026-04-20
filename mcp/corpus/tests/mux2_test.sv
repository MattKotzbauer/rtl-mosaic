`timescale 1ns/1ps
module mux2_test;
    localparam W = 8;
    reg  [W-1:0] in0, in1;
    reg          sel;
    wire [W-1:0] out;

    mux2 #(.WIDTH(W)) dut (.in0(in0), .in1(in1), .sel(sel), .out(out));

    integer mism = 0;
    integer total = 0;
    reg [W-1:0] expected;

    task check;
        input [W-1:0] exp;
        begin
            total = total + 1;
            #1;
            if (out !== exp) begin
                $display("MISMATCH: in0=%0d in1=%0d sel=%0d -> out=%0d exp=%0d", in0, in1, sel, out, exp);
                mism = mism + 1;
            end
        end
    endtask

    initial begin
        in0 = 8'hAA; in1 = 8'h55;
        sel = 0; check(8'hAA);
        sel = 1; check(8'h55);
        in0 = 8'h00; in1 = 8'hFF;
        sel = 0; check(8'h00);
        sel = 1; check(8'hFF);
        in0 = 8'h12; in1 = 8'h34;
        sel = 0; check(8'h12);
        sel = 1; check(8'h34);
        in0 = 8'hDE; in1 = 8'hAD;
        sel = 0; check(8'hDE);
        sel = 1; check(8'hAD);

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
