`timescale 1ns/1ps
module lfsr_test;
    reg clk=0,rst=1,en=0;
    wire [7:0] q;
    lfsr #(.WIDTH(8),.TAPS(8'hB8)) dut (.clk(clk),.rst(rst),.en(en),.q(q));
    always #5 clk=~clk;
    integer mism=0,total=0,i,zeroes=0,ones=0;
    initial begin
        rst=1; en=0; @(posedge clk); @(posedge clk);
        #1; total=total+1; if (q !== 8'h01) begin $display("MISMATCH seed=%h",q); mism=mism+1; end
        rst=0; en=1;
        for (i=0;i<32;i=i+1) begin @(posedge clk); #1; if (q==0) zeroes=zeroes+1; else ones=ones+1; end
        total=total+1;
        // LFSR must never hit all-zero state
        if (zeroes !== 0) begin $display("MISMATCH all-zero seen"); mism=mism+1; end
        if (mism==0) $display("PASS lfsr_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL lfsr_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
