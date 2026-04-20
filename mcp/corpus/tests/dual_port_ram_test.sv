`timescale 1ns/1ps
module dual_port_ram_test;
    localparam W = 8;
    localparam D = 16;
    reg  wr_clk = 0, rd_clk = 0;
    reg  we = 0, re = 0;
    reg  [$clog2(D)-1:0] waddr, raddr;
    reg  [W-1:0] wdata;
    wire [W-1:0] rdata;

    dual_port_ram #(.WIDTH(W), .DEPTH(D)) dut (
        .wr_clk(wr_clk), .we(we), .waddr(waddr), .wdata(wdata),
        .rd_clk(rd_clk), .re(re), .raddr(raddr), .rdata(rdata)
    );

    // Use shared clock for simplicity
    always #5 wr_clk = ~wr_clk;
    always @(*) rd_clk = wr_clk;

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W-1:0] expected_mem [0:D-1];

    initial begin
        // write all D entries; drive on negedge so values are stable at posedge
        @(negedge wr_clk); we = 1; re = 0;
        for (i = 0; i < D; i = i + 1) begin
            waddr = i[$clog2(D)-1:0];
            wdata = ((i * 8'h11) ^ 8'hA5);
            expected_mem[i] = wdata;
            @(posedge wr_clk);
            @(negedge wr_clk);
        end
        we = 0;

        // read them back (registered, 1-cycle latency)
        re = 1;
        for (i = 0; i < D; i = i + 1) begin
            raddr = i[$clog2(D)-1:0];
            @(posedge rd_clk); #1;
            total = total + 1;
            if (rdata !== expected_mem[i]) begin
                $display("MISMATCH addr=%0d rdata=%h exp=%h", i, rdata, expected_mem[i]);
                mism = mism + 1;
            end
            @(negedge rd_clk);
        end
        re = 0;

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
