// single_port_ram: synchronous single-port RAM.
// On a clock edge: if we, mem[addr] <= din. Read is combinational from mem.
// Write-then-read on same address returns the new value (write-first behavior).
module single_port_ram #(
    parameter WIDTH = 8,
    parameter DEPTH = 16
) (
    input  wire                     clk,
    input  wire                     we,
    input  wire [$clog2(DEPTH)-1:0] addr,
    input  wire [WIDTH-1:0]         din,
    output wire [WIDTH-1:0]         dout
);
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    integer i;
    initial begin
        for (i = 0; i < DEPTH; i = i + 1) mem[i] = {WIDTH{1'b0}};
    end

    always @(posedge clk) begin
        if (we) mem[addr] <= din;
    end

    assign dout = mem[addr];
endmodule
