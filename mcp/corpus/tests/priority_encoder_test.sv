`timescale 1ns/1ps
module priority_encoder_test;
    localparam W = 8;
    reg  [W-1:0] in;
    wire [$clog2(W)-1:0] out;
    wire valid;

    priority_encoder #(.WIDTH(W)) dut (.in(in), .out(out), .valid(valid));

    integer mism = 0;
    integer total = 0;
    integer i, j;
    reg [$clog2(W)-1:0] exp_out;
    reg exp_valid;

    function [$clog2(W)-1:0] golden_idx;
        input [W-1:0] v;
        integer k;
        begin
            golden_idx = 0;
            for (k = 0; k < W; k = k + 1)
                if (v[k]) golden_idx = k[$clog2(W)-1:0];
        end
    endfunction

    initial begin
        // zero
        in = 8'b0;
        #1;
        total = total + 1;
        if (valid !== 1'b0) begin
            $display("MISMATCH(zero): valid=%b", valid);
            mism = mism + 1;
        end

        // single-bit cases
        for (i = 0; i < W; i = i + 1) begin
            in = 8'b0;
            in[i] = 1'b1;
            #1;
            total = total + 1;
            exp_out   = i[$clog2(W)-1:0];
            exp_valid = 1'b1;
            if (out !== exp_out || valid !== exp_valid) begin
                $display("MISMATCH(single i=%0d): out=%0d valid=%b exp=%0d/%b", i, out, valid, exp_out, exp_valid);
                mism = mism + 1;
            end
        end

        // random multi-bit cases
        for (j = 0; j < 10; j = j + 1) begin
            in = $urandom & 8'hFF;
            #1;
            total = total + 1;
            exp_valid = (in != 0);
            exp_out   = golden_idx(in);
            if (exp_valid) begin
                if (out !== exp_out || valid !== 1'b1) begin
                    $display("MISMATCH(rand in=%h): out=%0d valid=%b exp=%0d", in, out, valid, exp_out);
                    mism = mism + 1;
                end
            end else begin
                if (valid !== 1'b0) begin
                    $display("MISMATCH(rand zero): valid=%b", valid);
                    mism = mism + 1;
                end
            end
        end

        $display("Mismatches: %0d in %0d samples", mism, total);
        $finish;
    end
endmodule
