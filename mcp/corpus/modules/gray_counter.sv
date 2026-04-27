// gray_counter: synchronous Gray-code up counter
module gray_counter #(
    parameter WIDTH = 4
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             en,
    output reg  [WIDTH-1:0] q
);
    reg [WIDTH-1:0] bin;
    always @(posedge clk) begin
        if (rst) begin
            bin <= {WIDTH{1'b0}};
            q   <= {WIDTH{1'b0}};
        end else if (en) begin
            bin <= bin + 1'b1;
            q   <= (bin + 1'b1) ^ ((bin + 1'b1) >> 1);
        end
    end
endmodule
