`timescale 1ns/1ps
module register_file_test;
    localparam W = 32;
    reg  clk = 0;
    reg  we = 0;
    reg  [3:0] waddr;
    reg  [W-1:0] wdata;
    reg  [3:0] raddr_a, raddr_b;
    wire [W-1:0] rdata_a, rdata_b;

    register_file #(.WIDTH(W)) dut (
        .clk(clk), .we(we), .waddr(waddr), .wdata(wdata),
        .raddr_a(raddr_a), .rdata_a(rdata_a),
        .raddr_b(raddr_b), .rdata_b(rdata_b)
    );

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W-1:0] expected [0:15];

    initial begin
        for (i = 0; i < 16; i = i + 1) expected[i] = 32'h0;

        // write all 16 registers
        @(negedge clk); we = 1;
        for (i = 0; i < 16; i = i + 1) begin
            waddr = i[3:0];
            wdata = (i + 1) * 32'h1111_1111;
            expected[i] = wdata;
            @(posedge clk);
            @(negedge clk);
        end
        we = 0;

        // read back via two ports (combinational)
        for (i = 0; i < 16; i = i + 1) begin
            raddr_a = i[3:0];
            raddr_b = (15 - i);
            #1;
            total = total + 1;
            if (rdata_a !== expected[i]) begin
                $display("MISMATCH(A i=%0d): rdata_a=%h exp=%h", i, rdata_a, expected[i]);
                mism = mism + 1;
            end
            total = total + 1;
            if (rdata_b !== expected[15-i]) begin
                $display("MISMATCH(B i=%0d): rdata_b=%h exp=%h", i, rdata_b, expected[15-i]);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
