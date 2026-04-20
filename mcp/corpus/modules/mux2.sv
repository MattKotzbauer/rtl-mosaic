// mux2: combinational 2-to-1 multiplexer, parameterizable WIDTH
module mux2 #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0] in0,
    input  wire [WIDTH-1:0] in1,
    input  wire             sel,
    output wire [WIDTH-1:0] out
);
    assign out = sel ? in1 : in0;
endmodule
