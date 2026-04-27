// multiplier: unsigned WIDTH x WIDTH -> 2*WIDTH combinational multiply
module multiplier #(
    parameter WIDTH = 16
) (
    input  wire [WIDTH-1:0]   a,
    input  wire [WIDTH-1:0]   b,
    output wire [2*WIDTH-1:0] product
);
    assign product = a * b;
endmodule
