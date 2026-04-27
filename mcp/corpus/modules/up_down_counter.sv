// up_down_counter: bidirectional synchronous counter
module up_down_counter #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    input  wire             up,
    output reg  [WIDTH-1:0] q
);
    always @(posedge clk) begin
        if (rst)      q <= {WIDTH{1'b0}};
        else if (en)  q <= up ? q + 1'b1 : q - 1'b1;
    end
endmodule
