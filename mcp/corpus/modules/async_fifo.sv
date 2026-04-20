// async_fifo: dual-clock FIFO using gray-coded pointers for CDC.
// Stub-quality: small, synthesizable, suitable for harness demo.
module async_fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input  wire             wr_clk,
    input  wire             wr_rst,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] din,
    output wire             full,

    input  wire             rd_clk,
    input  wire             rd_rst,
    input  wire             rd_en,
    output reg  [WIDTH-1:0] dout,
    output wire             empty
);
    localparam AW = $clog2(DEPTH);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Write side: binary + gray pointers
    reg  [AW:0] wr_bin, wr_gray;
    wire [AW:0] wr_bin_next  = wr_bin + (wr_en && !full);
    wire [AW:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;

    // Read side: binary + gray pointers
    reg  [AW:0] rd_bin, rd_gray;
    wire [AW:0] rd_bin_next  = rd_bin + (rd_en && !empty);
    wire [AW:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;

    // Synchronizers (2-FF) for the opposite-clock gray pointer
    reg [AW:0] rd_gray_sync_w0, rd_gray_sync_w1;
    reg [AW:0] wr_gray_sync_r0, wr_gray_sync_r1;

    // Write clock domain
    always @(posedge wr_clk) begin
        if (wr_rst) begin
            wr_bin  <= 0;
            wr_gray <= 0;
            rd_gray_sync_w0 <= 0;
            rd_gray_sync_w1 <= 0;
        end else begin
            if (wr_en && !full) mem[wr_bin[AW-1:0]] <= din;
            wr_bin  <= wr_bin_next;
            wr_gray <= wr_gray_next;
            rd_gray_sync_w0 <= rd_gray;
            rd_gray_sync_w1 <= rd_gray_sync_w0;
        end
    end

    // Read clock domain
    always @(posedge rd_clk) begin
        if (rd_rst) begin
            rd_bin  <= 0;
            rd_gray <= 0;
            wr_gray_sync_r0 <= 0;
            wr_gray_sync_r1 <= 0;
            dout    <= 0;
        end else begin
            if (rd_en && !empty) dout <= mem[rd_bin[AW-1:0]];
            rd_bin  <= rd_bin_next;
            rd_gray <= rd_gray_next;
            wr_gray_sync_r0 <= wr_gray;
            wr_gray_sync_r1 <= wr_gray_sync_r0;
        end
    end

    // Standard async-FIFO full/empty conditions on gray pointers
    assign empty = (rd_gray == wr_gray_sync_r1);
    assign full  = (wr_gray_next == {~rd_gray_sync_w1[AW:AW-1], rd_gray_sync_w1[AW-2:0]});
endmodule
