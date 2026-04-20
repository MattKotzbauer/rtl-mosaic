`timescale 1ns/1ps
module subtractor_test;
    localparam W = 8;
    reg  [W-1:0] a, b;
    wire [W-1:0] diff;
    wire         borrow_out;

    subtractor #(.WIDTH(W)) dut (.a(a), .b(b), .diff(diff), .borrow_out(borrow_out));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W:0] expected;

    initial begin
        // directed
        a = 8'd10; b = 8'd3; #1;
        expected = {1'b0, a} - {1'b0, b};
        total = total + 1;
        if ({borrow_out, diff} !== expected) begin $display("MISMATCH: %0d-%0d={%b,%0d} exp {%b,%0d}", a, b, borrow_out, diff, expected[W], expected[W-1:0]); mism = mism + 1; end

        a = 8'd0; b = 8'd1; #1;
        expected = {1'b0, a} - {1'b0, b};
        total = total + 1;
        if ({borrow_out, diff} !== expected) begin $display("MISMATCH: %0d-%0d={%b,%0d} exp {%b,%0d}", a, b, borrow_out, diff, expected[W], expected[W-1:0]); mism = mism + 1; end

        a = 8'd5; b = 8'd5; #1;
        expected = {1'b0, a} - {1'b0, b};
        total = total + 1;
        if ({borrow_out, diff} !== expected) begin $display("MISMATCH: %0d-%0d={%b,%0d} exp {%b,%0d}", a, b, borrow_out, diff, expected[W], expected[W-1:0]); mism = mism + 1; end

        // random
        for (i = 0; i < 15; i = i + 1) begin
            a = $urandom & 8'hFF;
            b = $urandom & 8'hFF;
            expected = {1'b0, a} - {1'b0, b};
            #1;
            total = total + 1;
            if ({borrow_out, diff} !== expected) begin
                $display("MISMATCH: %0d-%0d={%b,%0d} exp {%b,%0d}", a, b, borrow_out, diff, expected[W], expected[W-1:0]);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
