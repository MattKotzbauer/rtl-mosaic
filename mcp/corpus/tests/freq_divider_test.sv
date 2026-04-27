`timescale 1ns/1ps
module freq_divider_test;
    reg clk=0,rst=1;
    wire dout;
    freq_divider #(.N(4)) dut (.clk_in(clk),.rst(rst),.clk_out(dout));
    always #5 clk=~clk;
    integer mism=0,total=0,toggles=0;
    reg prev;
    initial begin
        rst=1; @(posedge clk); @(posedge clk);
        rst=0;
        prev=dout;
        repeat (16) begin
            @(posedge clk);
            #1;
            if (dout !== prev) toggles=toggles+1;
            prev=dout;
        end
        total=1;
        // 16 cycles, divide by 4 -> 4 toggles
        if (toggles !== 4) begin $display("MISMATCH toggles=%0d",toggles); mism=mism+1; end
        if (mism==0) $display("PASS freq_divider_test (%0d/%0d)",total-mism,total);
        else         $display("FAIL freq_divider_test (%0d/%0d)",mism,total);
        $finish;
    end
endmodule
