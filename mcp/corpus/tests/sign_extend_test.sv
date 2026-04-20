`timescale 1ns/1ps
module sign_extend_test;
    localparam IN  = 8;
    localparam OUT = 16;
    reg  [IN-1:0]  in;
    wire [OUT-1:0] out;

    sign_extend #(.IN_WIDTH(IN), .OUT_WIDTH(OUT)) dut (.in(in), .out(out));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg signed [IN-1:0]  s_in;
    reg signed [OUT-1:0] expected;

    initial begin
        // directed
        in = 8'h00; #1; expected = 16'sh0000;
        total = total + 1;
        if (out !== expected) begin $display("MISMATCH(0): out=%h exp=%h", out, expected); mism = mism + 1; end

        in = 8'h7F; #1; expected = 16'sh007F;
        total = total + 1;
        if (out !== expected) begin $display("MISMATCH(+max): out=%h exp=%h", out, expected); mism = mism + 1; end

        in = 8'h80; #1; expected = 16'shFF80;
        total = total + 1;
        if (out !== expected) begin $display("MISMATCH(-min): out=%h exp=%h", out, expected); mism = mism + 1; end

        in = 8'hFF; #1; expected = 16'shFFFF;
        total = total + 1;
        if (out !== expected) begin $display("MISMATCH(-1): out=%h exp=%h", out, expected); mism = mism + 1; end

        // random
        for (i = 0; i < 12; i = i + 1) begin
            in = $urandom & 8'hFF;
            s_in = in;
            expected = s_in;
            #1;
            total = total + 1;
            if (out !== expected) begin
                $display("MISMATCH(rand in=%h): out=%h exp=%h", in, out, expected);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
