`timescale 1ns/1ps
module up_counter_test;
    localparam W = 8;
    reg  clk = 0;
    reg  rst = 1;
    reg  en  = 0;
    wire [W-1:0] q;

    up_counter #(.WIDTH(W)) dut (.clk(clk), .rst(rst), .en(en), .q(q));

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    integer i;

    initial begin
        rst = 1; en = 0;
        @(posedge clk); @(posedge clk);
        #1;
        total = total + 1;
        if (q !== 0) begin $display("MISMATCH(reset): q=%0d", q); mism = mism + 1; end

        // count for 10 cycles
        rst = 0; en = 1;
        for (i = 1; i <= 10; i = i + 1) begin
            @(posedge clk);
            #1;
            total = total + 1;
            if (q !== i[W-1:0]) begin
                $display("MISMATCH(i=%0d): q=%0d", i, q);
                mism = mism + 1;
            end
        end

        // disable; q should hold
        en = 0;
        @(posedge clk);
        #1;
        total = total + 1;
        if (q !== 8'd10) begin $display("MISMATCH(hold): q=%0d", q); mism = mism + 1; end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
