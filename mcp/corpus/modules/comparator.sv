// comparator: combinational signed/unsigned magnitude compare.
// SIGNED=1 -> treat operands as two's-complement; SIGNED=0 -> unsigned.
module comparator #(
    parameter WIDTH  = 8,
    parameter SIGNED = 0
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire             gt,
    output wire             eq,
    output wire             lt
);
    wire signed [WIDTH-1:0] sa = a;
    wire signed [WIDTH-1:0] sb = b;

    assign eq = (a == b);
    assign gt = (SIGNED != 0) ? (sa >  sb) : (a >  b);
    assign lt = (SIGNED != 0) ? (sa <  sb) : (a <  b);
endmodule
