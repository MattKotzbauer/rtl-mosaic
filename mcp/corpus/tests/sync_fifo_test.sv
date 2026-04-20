`timescale 1ns/1ps
module sync_fifo_test;
    localparam W = 8;
    localparam D = 8;
    reg  clk = 0;
    reg  rst = 1;
    reg  wr_en = 0, rd_en = 0;
    reg  [W-1:0] din;
    wire [W-1:0] dout;
    wire full, empty;

    sync_fifo #(.WIDTH(W), .DEPTH(D)) dut (
        .clk(clk), .rst(rst),
        .wr_en(wr_en), .rd_en(rd_en),
        .din(din), .dout(dout),
        .full(full), .empty(empty)
    );

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    integer i;

    initial begin
        rst = 1; wr_en = 0; rd_en = 0; din = 0;
        @(posedge clk); @(posedge clk);
        @(negedge clk); rst = 0;

        // empty should be high
        #1;
        total = total + 1;
        if (empty !== 1'b1 || full !== 1'b0) begin $display("MISMATCH(post-reset): full=%b empty=%b", full, empty); mism = mism + 1; end

        // write D values
        wr_en = 1;
        for (i = 0; i < D; i = i + 1) begin
            din = i[W-1:0] + 8'h10;
            @(posedge clk);
            @(negedge clk);
        end
        wr_en = 0;
        @(posedge clk); #1;
        total = total + 1;
        if (full !== 1'b1) begin $display("MISMATCH(full after %0d writes): full=%b", D, full); mism = mism + 1; end

        // read them back; dout is registered so it appears 1 cycle after rd_en sees an entry
        @(negedge clk); rd_en = 1;
        for (i = 0; i < D; i = i + 1) begin
            @(posedge clk); #1;
            total = total + 1;
            if (dout !== (i[W-1:0] + 8'h10)) begin
                $display("MISMATCH(read i=%0d): dout=%h exp=%h", i, dout, (i[W-1:0] + 8'h10));
                mism = mism + 1;
            end
        end
        @(negedge clk); rd_en = 0;
        @(posedge clk); #1;
        total = total + 1;
        if (empty !== 1'b1) begin $display("MISMATCH(empty after drain): empty=%b", empty); mism = mism + 1; end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
