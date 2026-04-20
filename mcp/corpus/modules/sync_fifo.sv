// sync_fifo: parameterizable synchronous FIFO
// WIDTH = data width, DEPTH = number of entries (power of 2 recommended)
module sync_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             wr_en,
    input  wire             rd_en,
    input  wire [WIDTH-1:0] din,
    output reg  [WIDTH-1:0] dout,
    output wire             full,
    output wire             empty
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];
    reg [AW:0]      wr_ptr;
    reg [AW:0]      rd_ptr;

    assign empty = (wr_ptr == rd_ptr);
    assign full  = (wr_ptr[AW] != rd_ptr[AW]) &&
                   (wr_ptr[AW-1:0] == rd_ptr[AW-1:0]);

    always @(posedge clk) begin
        if (rst) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            dout   <= 0;
        end else begin
            if (wr_en && !full) begin
                mem[wr_ptr[AW-1:0]] <= din;
                wr_ptr <= wr_ptr + 1'b1;
            end
            if (rd_en && !empty) begin
                dout   <= mem[rd_ptr[AW-1:0]];
                rd_ptr <= rd_ptr + 1'b1;
            end
        end
    end
endmodule
