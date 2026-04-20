// sign_extend: sign-extend a signed IN_WIDTH input to OUT_WIDTH.
// If OUT_WIDTH <= IN_WIDTH, the input is truncated (low bits kept).
module sign_extend #(
    parameter IN_WIDTH  = 16,
    parameter OUT_WIDTH = 32
) (
    input  wire [IN_WIDTH-1:0]  in,
    output wire [OUT_WIDTH-1:0] out
);
    generate
        if (OUT_WIDTH > IN_WIDTH) begin : g_extend
            assign out = { {(OUT_WIDTH-IN_WIDTH){in[IN_WIDTH-1]}}, in };
        end else begin : g_truncate
            assign out = in[OUT_WIDTH-1:0];
        end
    endgenerate
endmodule
