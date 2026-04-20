// shift_register: synchronous SISO with parallel tap.
// On each clock with en=1, shift WIDTH-bit chunks toward the output:
//   stage[0] <= sin
//   stage[i] <= stage[i-1]  for i in 1..DEPTH-1
// sout is the last stage. parallel_out is the full {stage[DEPTH-1], ..., stage[0]}.
module shift_register #(
    parameter WIDTH = 1,
    parameter DEPTH = 4
) (
    input  wire                       clk,
    input  wire                       rst,
    input  wire                       en,
    input  wire [WIDTH-1:0]           sin,
    output wire [WIDTH-1:0]           sout,
    output wire [WIDTH*DEPTH-1:0]     parallel_out
);
    reg [WIDTH-1:0] stage [0:DEPTH-1];

    integer i;
    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < DEPTH; i = i + 1)
                stage[i] <= {WIDTH{1'b0}};
        end else if (en) begin
            stage[0] <= sin;
            for (i = 1; i < DEPTH; i = i + 1)
                stage[i] <= stage[i-1];
        end
    end

    assign sout = stage[DEPTH-1];

    genvar j;
    generate
        for (j = 0; j < DEPTH; j = j + 1) begin : g_pack
            assign parallel_out[(j+1)*WIDTH-1 : j*WIDTH] = stage[j];
        end
    endgenerate
endmodule
