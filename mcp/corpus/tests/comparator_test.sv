`timescale 1ns/1ps
module comparator_test;
    localparam W = 8;
    reg  [W-1:0] a, b;
    wire u_gt, u_eq, u_lt;
    wire s_gt, s_eq, s_lt;

    comparator #(.WIDTH(W), .SIGNED(0)) u_cmp (.a(a), .b(b), .gt(u_gt), .eq(u_eq), .lt(u_lt));
    comparator #(.WIDTH(W), .SIGNED(1)) s_cmp (.a(a), .b(b), .gt(s_gt), .eq(s_eq), .lt(s_lt));

    integer mism = 0;
    integer total = 0;
    integer i;
    reg eu_gt, eu_eq, eu_lt;
    reg es_gt, es_eq, es_lt;
    reg signed [W-1:0] sa, sb;

    initial begin
        for (i = 0; i < 16; i = i + 1) begin
            a = $urandom & 8'hFF;
            b = $urandom & 8'hFF;
            sa = a; sb = b;

            eu_gt = (a >  b);
            eu_eq = (a == b);
            eu_lt = (a <  b);
            es_gt = (sa >  sb);
            es_eq = (sa == sb);
            es_lt = (sa <  sb);

            #1;
            total = total + 1;
            if (u_gt !== eu_gt || u_eq !== eu_eq || u_lt !== eu_lt) begin
                $display("MISMATCH(unsigned a=%0d b=%0d): got %b%b%b exp %b%b%b", a, b, u_gt, u_eq, u_lt, eu_gt, eu_eq, eu_lt);
                mism = mism + 1;
            end
            total = total + 1;
            if (s_gt !== es_gt || s_eq !== es_eq || s_lt !== es_lt) begin
                $display("MISMATCH(signed a=%0d b=%0d): got %b%b%b exp %b%b%b", sa, sb, s_gt, s_eq, s_lt, es_gt, es_eq, es_lt);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
