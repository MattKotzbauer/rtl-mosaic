`timescale 1ns/1ps
module up_down_counter_test;
    localparam W=8;
    reg clk=0,rst=1,en=0,up=1;
    wire [W-1:0] q;
    up_down_counter #(.WIDTH(W)) dut (.clk(clk),.rst(rst),.en(en),.up(up),.q(q));
    always #5 clk=~clk;
    integer mism=0,total=0,i;
    initial begin
        rst=1; en=0; up=1; @(posedge clk); @(posedge clk);
        #1; total=total+1; if (q !== 0) begin $display("MISMATCH reset"); mism=mism+1; end
        rst=0; en=1; up=1;
        for (i=1;i<=5;i=i+1) begin @(posedge clk); #1; total=total+1; if (q !== i[W-1:0]) begin $display("MISMATCH up i=%0d q=%0d",i,q); mism=mism+1; end end
        up=0;
        for (i=4;i>=0;i=i-1) begin @(posedge clk); #1; total=total+1; if (q !== i[W-1:0]) begin $display("MISMATCH down i=%0d q=%0d",i,q); mism=mism+1; end end
        if (mism==0) $display("PASS up_down_counter_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL up_down_counter_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
