// dual_port_ram: independent synchronous read and write ports.
// DEPTH should be a power of 2. Read port is registered (1-cycle latency).
module dual_port_ram #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input  wire                     wr_clk,
    input  wire                     we,
    input  wire [$clog2(DEPTH)-1:0] waddr,
    input  wire [WIDTH-1:0]         wdata,

    input  wire                     rd_clk,
    input  wire                     re,
    input  wire [$clog2(DEPTH)-1:0] raddr,
    output reg  [WIDTH-1:0]         rdata
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    integer i;
    initial begin
        for (i = 0; i < DEPTH; i = i + 1) mem[i] = {WIDTH{1'b0}};
        rdata = {WIDTH{1'b0}};
    end

    always @(posedge wr_clk) begin
        if (we) mem[waddr] <= wdata;
    end

    always @(posedge rd_clk) begin
        if (re) rdata <= mem[raddr];
    end
endmodule
