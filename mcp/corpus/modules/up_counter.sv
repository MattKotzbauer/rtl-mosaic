// up_counter: synchronous up counter with enable + sync reset
module up_counter #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg  [WIDTH-1:0] q
);
    always @(posedge clk) begin
        if (rst)      q <= {WIDTH{1'b0}};
        else if (en)  q <= q + 1'b1;
    end
endmodule
