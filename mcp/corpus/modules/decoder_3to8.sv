// decoder_3to8: one-hot 3-to-8 decoder with active-high enable
module decoder_3to8 (
    input  wire       en,
    input  wire [2:0] in,
    output reg  [7:0] out
);
    always @(*) begin
        if (!en) out = 8'b0;
        else begin
            out = 8'b0;
            out[in] = 1'b1;
        end
    end
endmodule
