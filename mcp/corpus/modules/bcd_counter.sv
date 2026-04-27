// bcd_counter: mod-10 decimal counter with carry-out
module bcd_counter (
    input  wire       clk,
    input  wire       rst,
    input  wire       en,
    output reg  [3:0] q,
    output wire       co
);
    assign co = en && (q == 4'd9);
    always @(posedge clk) begin
        if (rst)        q <= 4'd0;
        else if (en)    q <= (q == 4'd9) ? 4'd0 : q + 4'd1;
    end
endmodule
