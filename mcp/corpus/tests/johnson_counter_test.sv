`timescale 1ns/1ps
module johnson_counter_test;
    localparam W=4;
    reg clk=0,rst=1,en=0;
    wire [W-1:0] q;
    johnson_counter #(.WIDTH(W)) dut (.clk(clk),.rst(rst),.en(en),.q(q));
    always #5 clk=~clk;
    // Module shifts left + inverts old MSB. For W=4 starting from 0000:
    // 0000, 0001, 0011, 0111, 1111, 1110, 1100, 1000, 0000, ...
    reg [3:0] expected [0:7];
    integer mism=0,total=0,i;
    initial begin
        expected[0]=4'b0001; expected[1]=4'b0011; expected[2]=4'b0111; expected[3]=4'b1111;
        expected[4]=4'b1110; expected[5]=4'b1100; expected[6]=4'b1000; expected[7]=4'b0000;
        rst=1; en=0; @(posedge clk); @(posedge clk);
        rst=0; en=1;
        for (i=0;i<8;i=i+1) begin
            @(posedge clk); #1;
            total=total+1;
            if (q !== expected[i]) begin $display("MISMATCH i=%0d exp=%b got=%b",i,expected[i],q); mism=mism+1; end
        end
        if (mism==0) $display("PASS johnson_counter_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL johnson_counter_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
