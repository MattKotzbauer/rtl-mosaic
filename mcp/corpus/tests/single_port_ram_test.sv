`timescale 1ns/1ps
module single_port_ram_test;
    localparam W = 8;
    localparam D = 16;
    reg  clk = 0;
    reg  we = 0;
    reg  [$clog2(D)-1:0] addr;
    reg  [W-1:0] din;
    wire [W-1:0] dout;

    single_port_ram #(.WIDTH(W), .DEPTH(D)) dut (
        .clk(clk), .we(we), .addr(addr), .din(din), .dout(dout)
    );

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    integer i;
    reg [W-1:0] expected_mem [0:D-1];

    initial begin
        // write all entries; drive inputs at negedge so they're stable before posedge
        @(negedge clk); we = 1;
        for (i = 0; i < D; i = i + 1) begin
            addr = i[$clog2(D)-1:0];
            din  = ((i * 8'h13) ^ 8'h5A);
            expected_mem[i] = din;
            @(posedge clk);
            @(negedge clk);
        end
        we = 0;

        // read them back (combinational read)
        for (i = 0; i < D; i = i + 1) begin
            addr = i[$clog2(D)-1:0];
            #1;
            total = total + 1;
            if (dout !== expected_mem[i]) begin
                $display("MISMATCH addr=%0d dout=%h exp=%h", i, dout, expected_mem[i]);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
