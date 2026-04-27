`timescale 1ns/1ps
module bcd_counter_test;
    reg clk=0,rst=1,en=0;
    wire [3:0] q;
    wire co;
    bcd_counter dut (.clk(clk),.rst(rst),.en(en),.q(q),.co(co));
    always #5 clk=~clk;
    integer mism=0,total=0,i;
    initial begin
        rst=1; en=0; @(posedge clk); @(posedge clk);
        #1; total=total+1; if (q !== 4'd0) begin $display("MISMATCH reset"); mism=mism+1; end
        rst=0; en=1;
        for (i=1;i<=12;i=i+1) begin
            @(posedge clk); #1;
            total=total+1;
            if (q !== (i % 10)) begin $display("MISMATCH count i=%0d q=%0d",i,q); mism=mism+1; end
        end
        if (mism==0) $display("PASS bcd_counter_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL bcd_counter_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
