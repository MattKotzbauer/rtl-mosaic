`timescale 1ns/1ps
module alu_test;
    reg  [31:0] a, b;
    reg  [3:0]  op;
    wire [31:0] y;
    wire        zero;
    alu #(.WIDTH(32)) dut (.a(a),.b(b),.op(op),.y(y),.zero(zero));
    integer mism = 0, total = 0;
    initial begin
        a=32'd10; b=32'd5;
        op=4'd0; #1; total=total+1; if (y !== 32'd15)       begin $display("MISMATCH ADD"); mism=mism+1; end
        op=4'd1; #1; total=total+1; if (y !== 32'd5)        begin $display("MISMATCH SUB"); mism=mism+1; end
        op=4'd2; #1; total=total+1; if (y !== (10 & 5))     begin $display("MISMATCH AND"); mism=mism+1; end
        op=4'd3; #1; total=total+1; if (y !== (10 | 5))     begin $display("MISMATCH OR");  mism=mism+1; end
        op=4'd4; #1; total=total+1; if (y !== (10 ^ 5))     begin $display("MISMATCH XOR"); mism=mism+1; end
        op=4'd5; #1; total=total+1; if (y !== (32'd10 << 5))begin $display("MISMATCH SLL"); mism=mism+1; end
        op=4'd6; #1; total=total+1; if (y !== (32'd10 >> 5))begin $display("MISMATCH SRL"); mism=mism+1; end
        op=4'd7; #1; total=total+1; if (y !== 32'd0)        begin $display("MISMATCH SLT"); mism=mism+1; end
        a=32'd5; b=32'd10;
        op=4'd7; #1; total=total+1; if (y !== 32'd1)        begin $display("MISMATCH SLT2"); mism=mism+1; end
        a=32'd5; b=32'd5;
        op=4'd1; #1; total=total+1; if (zero !== 1'b1)      begin $display("MISMATCH zero"); mism=mism+1; end
        if (mism == 0) $display("PASS alu_test (%0d/%0d)", total-mism, total);
        else           $display("FAIL alu_test (%0d/%0d mismatches)", mism, total);
        $finish;
    end
endmodule
