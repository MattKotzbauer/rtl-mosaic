// priority_encoder: encodes the index of the highest set bit of `in`.
// WIDTH = number of input bits. Output `out` has $clog2(WIDTH) bits.
// `valid` is 1 when any input bit is set.
module priority_encoder #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0]         in,
    output reg  [$clog2(WIDTH)-1:0] out,
    output reg                      valid
);
    integer i;
    always @(*) begin
        out   = {$clog2(WIDTH){1'b0}};
        valid = 1'b0;
        for (i = 0; i < WIDTH; i = i + 1) begin
            if (in[i]) begin
                out   = i[$clog2(WIDTH)-1:0];
                valid = 1'b1;
            end
        end
    end
endmodule
