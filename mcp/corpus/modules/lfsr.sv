// lfsr: Galois-style LFSR with parameterizable taps
module lfsr #(
    parameter WIDTH = 8,
    parameter [WIDTH-1:0] TAPS = 8'hB8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg  [WIDTH-1:0] q
);
    wire feedback = q[0];
    always @(posedge clk) begin
        if (rst)        q <= {{(WIDTH-1){1'b0}}, 1'b1};
        else if (en)    q <= feedback ? ((q >> 1) ^ TAPS) : (q >> 1);
    end
endmodule
