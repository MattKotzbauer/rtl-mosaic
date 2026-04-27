`timescale 1ns/1ps
module t_flipflop_test;
    reg clk=0,rst=1,t=0;
    wire q;
    t_flipflop dut (.clk(clk),.rst(rst),.t(t),.q(q));
    always #5 clk=~clk;
    integer mism=0,total=0;
    initial begin
        rst=1; t=0; @(posedge clk); @(posedge clk);
        #1; total=total+1; if (q !== 0) begin $display("MISMATCH reset"); mism=mism+1; end
        rst=0; t=1;
        @(posedge clk); #1; total=total+1; if (q !== 1) begin $display("MISMATCH toggle1"); mism=mism+1; end
        @(posedge clk); #1; total=total+1; if (q !== 0) begin $display("MISMATCH toggle2"); mism=mism+1; end
        t=0;
        @(posedge clk); #1; total=total+1; if (q !== 0) begin $display("MISMATCH hold"); mism=mism+1; end
        if (mism==0) $display("PASS t_flipflop_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL t_flipflop_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
