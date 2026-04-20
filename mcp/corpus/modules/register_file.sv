// register_file: 16-entry RF, dual read ports, single write port
module register_file #(
    parameter WIDTH = 32
) (
    input  wire             clk,
    input  wire             we,
    input  wire [3:0]       waddr,
    input  wire [WIDTH-1:0] wdata,
    input  wire [3:0]       raddr_a,
    output wire [WIDTH-1:0] rdata_a,
    input  wire [3:0]       raddr_b,
    output wire [WIDTH-1:0] rdata_b
);
    reg [WIDTH-1:0] regs [0:15];

    integer i;
    initial begin
        for (i = 0; i < 16; i = i + 1) regs[i] = {WIDTH{1'b0}};
    end

    always @(posedge clk) begin
        if (we) regs[waddr] <= wdata;
    end

    assign rdata_a = regs[raddr_a];
    assign rdata_b = regs[raddr_b];
endmodule
