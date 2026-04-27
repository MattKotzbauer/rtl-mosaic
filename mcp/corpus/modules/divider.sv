// divider: unsigned combinational integer divider
module divider #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output wire [WIDTH-1:0] q,
    output wire [WIDTH-1:0] r
);
    assign q = (b == 0) ? {WIDTH{1'b1}} : a / b;
    assign r = (b == 0) ? a              : a % b;
endmodule
