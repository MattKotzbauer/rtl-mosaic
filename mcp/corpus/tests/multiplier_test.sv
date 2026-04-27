`timescale 1ns/1ps
module multiplier_test;
    reg  [15:0] a, b;
    wire [31:0] p;
    multiplier #(.WIDTH(16)) dut (.a(a),.b(b),.product(p));
    integer mism=0,total=0;
    initial begin
        a=16'd0;     b=16'd5;     #1; total=total+1; if (p !== 0)             begin $display("MISMATCH 0*5"); mism=mism+1; end
        a=16'd1;     b=16'd1;     #1; total=total+1; if (p !== 1)             begin $display("MISMATCH 1*1"); mism=mism+1; end
        a=16'd123;   b=16'd456;   #1; total=total+1; if (p !== 32'd56088)     begin $display("MISMATCH 123*456"); mism=mism+1; end
        a=16'hFFFF;  b=16'hFFFF;  #1; total=total+1; if (p !== 32'hFFFE0001)  begin $display("MISMATCH max*max"); mism=mism+1; end
        a=16'd2;     b=16'd3;     #1; total=total+1; if (p !== 6)             begin $display("MISMATCH 2*3"); mism=mism+1; end
        if (mism==0) $display("PASS multiplier_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL multiplier_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
