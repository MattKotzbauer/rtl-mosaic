`timescale 1ns/1ps
module edge_detector_test;
    reg clk = 0;
    reg rst_n = 0;
    reg sig = 0;
    wire rise, fall;

    edge_detector dut (.clk(clk), .rst_n(rst_n), .sig(sig), .rise(rise), .fall(fall));

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;

    task chk;
        input exp_rise;
        input exp_fall;
        input [127:0] tag;
        begin
            total = total + 1;
            if (rise !== exp_rise || fall !== exp_fall) begin
                $display("MISMATCH(%0s): rise=%b fall=%b exp %b/%b", tag, rise, fall, exp_rise, exp_fall);
                mism = mism + 1;
            end
        end
    endtask

    initial begin
        rst_n = 0; sig = 0;
        @(negedge clk);
        rst_n = 1;
        @(posedge clk); #1;
        chk(0, 0, "init");

        // drive sig=1 in the negedge before the posedge that should detect it
        @(negedge clk); sig = 1;
        @(posedge clk); #1;
        chk(1, 0, "rise");

        // hold high for one more cycle
        @(posedge clk); #1;
        chk(0, 0, "hold-high");

        // falling edge
        @(negedge clk); sig = 0;
        @(posedge clk); #1;
        chk(0, 1, "fall");

        @(posedge clk); #1;
        chk(0, 0, "hold-low");

        @(negedge clk); sig = 1;
        @(posedge clk); #1;
        chk(1, 0, "rise2");

        @(negedge clk); sig = 0;
        @(posedge clk); #1;
        chk(0, 1, "fall2");

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
