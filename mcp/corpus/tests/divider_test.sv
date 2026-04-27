`timescale 1ns/1ps
module divider_test;
    reg  [7:0] a, b;
    wire [7:0] q, r;
    divider #(.WIDTH(8)) dut (.a(a),.b(b),.q(q),.r(r));
    integer mism=0,total=0;
    initial begin
        a=8'd20; b=8'd4;  #1; total=total+1; if (q !== 8'd5  || r !== 8'd0) begin $display("MISMATCH 20/4"); mism=mism+1; end
        a=8'd23; b=8'd5;  #1; total=total+1; if (q !== 8'd4  || r !== 8'd3) begin $display("MISMATCH 23/5"); mism=mism+1; end
        a=8'd1;  b=8'd1;  #1; total=total+1; if (q !== 8'd1  || r !== 8'd0) begin $display("MISMATCH 1/1"); mism=mism+1; end
        a=8'd100;b=8'd7;  #1; total=total+1; if (q !== 8'd14 || r !== 8'd2) begin $display("MISMATCH 100/7"); mism=mism+1; end
        a=8'd5;  b=8'd0;  #1; total=total+1; if (q !== 8'hFF || r !== 8'd5) begin $display("MISMATCH /0 sentinel"); mism=mism+1; end
        if (mism==0) $display("PASS divider_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL divider_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
