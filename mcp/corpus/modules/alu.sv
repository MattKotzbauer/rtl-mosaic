// alu: 32-bit RISC-V style combinational ALU
module alu #(
    parameter WIDTH = 32
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    input  wire [3:0]       op,
    output reg  [WIDTH-1:0] y,
    output wire             zero
);
    always @(*) begin
        case (op)
            4'd0: y = a + b;
            4'd1: y = a - b;
            4'd2: y = a & b;
            4'd3: y = a | b;
            4'd4: y = a ^ b;
            4'd5: y = a << b[$clog2(WIDTH)-1:0];
            4'd6: y = a >> b[$clog2(WIDTH)-1:0];
            4'd7: y = ($signed(a) < $signed(b)) ? {{(WIDTH-1){1'b0}},1'b1} : {WIDTH{1'b0}};
            4'd8: y = (a < b) ? {{(WIDTH-1){1'b0}},1'b1} : {WIDTH{1'b0}};
            default: y = {WIDTH{1'b0}};
        endcase
    end
    assign zero = (y == {WIDTH{1'b0}});
endmodule
