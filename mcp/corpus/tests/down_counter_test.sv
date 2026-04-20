`timescale 1ns/1ps
module down_counter_test;
    localparam W = 8;
    reg  clk = 0;
    reg  rst = 1;
    reg  load = 0;
    reg  en   = 0;
    reg  [W-1:0] din;
    wire [W-1:0] count;
    wire         zero;

    down_counter #(.WIDTH(W)) dut (
        .clk(clk), .rst(rst), .load(load), .en(en),
        .din(din), .count(count), .zero(zero)
    );

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    integer i;

    initial begin
        // reset
        rst = 1; load = 0; en = 0; din = 0;
        @(posedge clk); @(posedge clk); #1;
        total = total + 1;
        if (count !== 0 || zero !== 1'b1) begin $display("MISMATCH(reset): count=%0d zero=%b", count, zero); mism = mism + 1; end

        // load 5
        @(negedge clk); rst = 0; load = 1; din = 8'd5;
        @(posedge clk); #1;
        @(negedge clk); load = 0;
        total = total + 1;
        if (count !== 8'd5 || zero !== 1'b0) begin $display("MISMATCH(load): count=%0d zero=%b", count, zero); mism = mism + 1; end

        // count down 5 times: 5 -> 4 -> 3 -> 2 -> 1 -> 0
        @(negedge clk); en = 1;
        for (i = 4; i >= 0; i = i - 1) begin
            @(posedge clk); #1;
            total = total + 1;
            if (count !== i[W-1:0]) begin
                $display("MISMATCH(count i=%0d): count=%0d", i, count);
                mism = mism + 1;
            end
        end
        // count is 0 now and zero high
        total = total + 1;
        if (zero !== 1'b1) begin $display("MISMATCH(zero flag): zero=%b count=%0d", zero, count); mism = mism + 1; end

        // disable; count should hold at 0 (or wrap if en stays on, but en=0 holds)
        @(negedge clk); en = 0;
        @(posedge clk); #1;
        total = total + 1;
        if (count !== 0) begin $display("MISMATCH(hold): count=%0d", count); mism = mism + 1; end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
