`timescale 1ns/1ps
module ripple_adder_test;
    localparam W = 8;
    reg  [W-1:0] a, b;
    reg          cin;
    wire [W-1:0] sum;
    wire         cout;

    ripple_adder #(.WIDTH(W)) dut (.a(a), .b(b), .cin(cin), .sum(sum), .cout(cout));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W:0] expected;

    initial begin
        // directed corner cases
        a = 0; b = 0; cin = 0; #1;
        expected = a + b + cin;
        total = total + 1;
        if ({cout, sum} !== expected) begin $display("MISMATCH: %0d+%0d+%0d=%0d exp %0d", a, b, cin, {cout,sum}, expected); mism = mism + 1; end

        a = 8'hFF; b = 8'h01; cin = 0; #1;
        expected = a + b + cin;
        total = total + 1;
        if ({cout, sum} !== expected) begin $display("MISMATCH: %0d+%0d+%0d=%0d exp %0d", a, b, cin, {cout,sum}, expected); mism = mism + 1; end

        a = 8'hFF; b = 8'hFF; cin = 1; #1;
        expected = a + b + cin;
        total = total + 1;
        if ({cout, sum} !== expected) begin $display("MISMATCH: %0d+%0d+%0d=%0d exp %0d", a, b, cin, {cout,sum}, expected); mism = mism + 1; end

        // random
        for (i = 0; i < 15; i = i + 1) begin
            a   = $urandom & 8'hFF;
            b   = $urandom & 8'hFF;
            cin = $urandom & 1'b1;
            expected = a + b + cin;
            #1;
            total = total + 1;
            if ({cout, sum} !== expected) begin
                $display("MISMATCH: %0d+%0d+%0d={%b,%0d} exp %0d", a, b, cin, cout, sum, expected);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
