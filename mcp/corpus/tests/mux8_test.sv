`timescale 1ns/1ps
module mux8_test;
    localparam W = 8;
    reg  [W-1:0] in [0:7];
    reg  [2:0]   sel;
    wire [W-1:0] out;

    mux8 #(.WIDTH(W)) dut (
        .in0(in[0]), .in1(in[1]), .in2(in[2]), .in3(in[3]),
        .in4(in[4]), .in5(in[5]), .in6(in[6]), .in7(in[7]),
        .sel(sel), .out(out)
    );

    integer mism = 0;
    integer total = 0;
    integer i;

    initial begin
        for (i = 0; i < 8; i = i + 1) in[i] = (i + 1) * 8'h11;
        for (i = 0; i < 8; i = i + 1) begin
            sel = i[2:0];
            #1;
            total = total + 1;
            if (out !== in[i]) begin
                $display("MISMATCH: sel=%0d out=%h exp=%h", sel, out, in[i]);
                mism = mism + 1;
            end
        end
        // randomized passes
        for (i = 0; i < 8; i = i + 1) begin
            in[i] = $urandom & 8'hFF;
        end
        for (i = 0; i < 8; i = i + 1) begin
            sel = i[2:0];
            #1;
            total = total + 1;
            if (out !== in[i]) begin
                $display("MISMATCH(rand): sel=%0d out=%h exp=%h", sel, out, in[i]);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
