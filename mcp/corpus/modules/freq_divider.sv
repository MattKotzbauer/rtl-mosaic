// freq_divider: divide-by-N toggle divider (clk_out has period 2*N of clk_in)
module freq_divider #(
    parameter N = 4
) (
    input  wire clk_in,
    input  wire rst,
    output reg  clk_out
);
    localparam CW = (N <= 1) ? 1 : $clog2(N);
    reg [CW-1:0] cnt;
    always @(posedge clk_in) begin
        if (rst) begin
            cnt     <= 0;
            clk_out <= 1'b0;
        end else if (cnt == N-1) begin
            cnt     <= 0;
            clk_out <= ~clk_out;
        end else begin
            cnt <= cnt + 1'b1;
        end
    end
endmodule
