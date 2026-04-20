`timescale 1ns/1ps
module decoder_3to8_test;
    reg       en;
    reg [2:0] in;
    wire [7:0] out;

    decoder_3to8 dut (.en(en), .in(in), .out(out));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [7:0] exp;

    initial begin
        // disabled: always 0
        en = 0;
        for (i = 0; i < 8; i = i + 1) begin
            in = i[2:0];
            #1;
            total = total + 1;
            if (out !== 8'b0) begin
                $display("MISMATCH(en=0): in=%0d out=%b", in, out);
                mism = mism + 1;
            end
        end
        // enabled: one-hot for in
        en = 1;
        for (i = 0; i < 8; i = i + 1) begin
            in = i[2:0];
            exp = 8'b0;
            exp[i] = 1'b1;
            #1;
            total = total + 1;
            if (out !== exp) begin
                $display("MISMATCH(en=1): in=%0d out=%b exp=%b", in, out, exp);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
