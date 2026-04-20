// down_counter: synchronous down counter with sync reset, load, enable.
// Priority: rst > load > en. zero=1 when count==0 (combinational).
module down_counter #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             load,
    input  wire             en,
    input  wire [WIDTH-1:0] din,
    output reg  [WIDTH-1:0] count,
    output wire             zero
);
    always @(posedge clk) begin
        if (rst)        count <= {WIDTH{1'b0}};
        else if (load)  count <= din;
        else if (en)    count <= count - 1'b1;
    end

    assign zero = (count == {WIDTH{1'b0}});
endmodule
