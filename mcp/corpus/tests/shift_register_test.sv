`timescale 1ns/1ps
module shift_register_test;
    localparam W = 1;
    localparam D = 4;
    reg  clk = 0;
    reg  rst = 1;
    reg  en  = 0;
    reg  [W-1:0] sin;
    wire [W-1:0] sout;
    wire [W*D-1:0] parallel_out;

    shift_register #(.WIDTH(W), .DEPTH(D)) dut (
        .clk(clk), .rst(rst), .en(en),
        .sin(sin), .sout(sout), .parallel_out(parallel_out)
    );

    always #5 clk = ~clk;

    integer mism = 0;
    integer total = 0;
    reg [D-1:0] golden;
    integer i;
    reg [W-1:0] bit_to_send;

    initial begin
        // reset
        rst = 1; en = 0; sin = 0;
        @(posedge clk); @(posedge clk);
        rst = 0;
        golden = 4'b0000;

        // shift in pattern 1, 0, 1, 1
        en = 1;
        for (i = 0; i < 8; i = i + 1) begin
            case (i)
                0: bit_to_send = 1'b1;
                1: bit_to_send = 1'b0;
                2: bit_to_send = 1'b1;
                3: bit_to_send = 1'b1;
                4: bit_to_send = 1'b0;
                5: bit_to_send = 1'b1;
                6: bit_to_send = 1'b0;
                7: bit_to_send = 1'b0;
                default: bit_to_send = 1'b0;
            endcase
            sin = bit_to_send;
            // golden: the soon-to-be-stored bit goes into stage[0]; the
            // existing stage[D-1] gets discarded. sout will be the OLD stage[D-1].
            @(posedge clk);
            #1;
            total = total + 1;
            // After clk, stage[0] = bit_to_send, stage[k] = old stage[k-1]
            // So sout (= stage[D-1]) = old stage[D-2] = golden[D-2]
            // Easier: shift golden left by 1 and drop top bit, insert new at LSB.
            golden = {golden[D-2:0], bit_to_send};
            // sout should equal golden[D-1]
            if (sout !== golden[D-1]) begin
                $display("MISMATCH cycle %0d: sout=%b golden=%b (golden[D-1]=%b)", i, sout, golden, golden[D-1]);
                mism = mism + 1;
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
