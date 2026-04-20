`timescale 1ns/1ps
module async_fifo_test;
    localparam W = 8;
    localparam D = 8;
    reg  wr_clk = 0, rd_clk = 0;
    reg  wr_rst = 1, rd_rst = 1;
    reg  wr_en = 0, rd_en = 0;
    reg  [W-1:0] din;
    wire [W-1:0] dout;
    wire full, empty;

    async_fifo #(.WIDTH(W), .DEPTH(D)) dut (
        .wr_clk(wr_clk), .wr_rst(wr_rst), .wr_en(wr_en), .din(din), .full(full),
        .rd_clk(rd_clk), .rd_rst(rd_rst), .rd_en(rd_en), .dout(dout), .empty(empty)
    );

    // Different clock periods to exercise CDC
    always #5 wr_clk = ~wr_clk;
    always #7 rd_clk = ~rd_clk;

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W-1:0] expected [0:D-1];

    initial begin
        #50000;
        $display("TIMEOUT");
        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end

    initial begin
        wr_rst = 1; rd_rst = 1; wr_en = 0; rd_en = 0; din = 0;
        repeat (4) @(posedge wr_clk);
        @(negedge wr_clk); wr_rst = 0;
        repeat (4) @(posedge rd_clk);
        @(negedge rd_clk); rd_rst = 0;

        // write 4 values (well below capacity) so full never asserts and
        // we avoid any combinational-loop conditions on the write side.
        @(negedge wr_clk); wr_en = 1;
        for (i = 0; i < 4; i = i + 1) begin
            din = (i + 1) * 8'h11;
            expected[i] = din;
            @(posedge wr_clk);
            @(negedge wr_clk);
        end
        wr_en = 0;

        // wait for synchronizers to propagate empty -> 0 in read domain
        repeat (8) @(posedge rd_clk);

        // read them back
        @(negedge rd_clk); rd_en = 1;
        for (i = 0; i < 4; i = i + 1) begin
            @(posedge rd_clk); #1;
            total = total + 1;
            if (dout !== expected[i]) begin
                $display("MISMATCH(read i=%0d): dout=%h exp=%h", i, dout, expected[i]);
                mism = mism + 1;
            end
        end
        @(negedge rd_clk); rd_en = 0;

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
