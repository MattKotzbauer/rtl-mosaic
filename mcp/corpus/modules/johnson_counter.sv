// johnson_counter: twisted-ring counter
module johnson_counter #(
    parameter WIDTH = 4
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg  [WIDTH-1:0] q
);
    always @(posedge clk) begin
        if (rst)      q <= {WIDTH{1'b0}};
        else if (en)  q <= {q[WIDTH-2:0], ~q[WIDTH-1]};
    end
endmodule
