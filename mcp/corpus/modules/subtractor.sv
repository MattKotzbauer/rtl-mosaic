// subtractor: N-bit subtractor (diff = a - b). borrow_out = 1 when a < b (unsigned).
module subtractor #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire [WIDTH-1:0] diff,
    output wire             borrow_out
);
    wire [WIDTH:0] result;
    assign result     = {1'b0, a} - {1'b0, b};
    assign diff       = result[WIDTH-1:0];
    assign borrow_out = result[WIDTH];
endmodule
