`timescale 1ns/1ps
module cla_adder_test;
    reg  [3:0] a, b;
    reg        cin;
    wire [3:0] sum;
    wire       cout;

    cla_adder dut (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));

    integer mism = 0;
    integer total = 0;
    integer ai, bi, ci;
    reg [4:0] expected;

    initial begin
        // exhaustive over all 4-bit + 4-bit + cin (512 cases is fine)
        for (ai = 0; ai < 16; ai = ai + 1) begin
            for (bi = 0; bi < 16; bi = bi + 1) begin
                for (ci = 0; ci < 2; ci = ci + 1) begin
                    a = ai[3:0]; b = bi[3:0]; cin = ci[0];
                    expected = a + b + cin;
                    #1;
                    total = total + 1;
                    if ({cout, sum} !== expected) begin
                        $display("MISMATCH: %0d+%0d+%0d={%b,%0d} exp %0d", a, b, cin, cout, sum, expected);
                        mism = mism + 1;
                    end
                end
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
