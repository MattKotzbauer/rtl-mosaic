`timescale 1ns/1ps
module gray_counter_test;
    localparam W=4;
    reg clk=0,rst=1,en=0;
    wire [W-1:0] q;
    gray_counter #(.WIDTH(W)) dut (.clk(clk),.rst(rst),.en(en),.q(q));
    always #5 clk=~clk;
    integer mism=0,total=0,i,bits,k;
    reg [W-1:0] prev, diff;
    initial begin
        rst=1; en=0; @(posedge clk); @(posedge clk);
        #1; total=total+1; if (q !== 0) begin $display("MISMATCH reset"); mism=mism+1; end
        rst=0; en=1;
        prev=0;
        for (i=1;i<=8;i=i+1) begin
            @(posedge clk); #1;
            total=total+1;
            diff = q ^ prev;
            // popcount manually (no $countones in iverilog -g2012)
            bits = 0;
            for (k=0; k<W; k=k+1) bits = bits + diff[k];
            if (bits != 1) begin
                $display("MISMATCH gray-transition prev=%b q=%b diff=%0d",prev,q,bits);
                mism=mism+1;
            end
            prev=q;
        end
        if (mism==0) $display("PASS gray_counter_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL gray_counter_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
