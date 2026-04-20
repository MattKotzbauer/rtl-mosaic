// barrel_shifter: combinational shifter, op selects operation:
//   op=2'b00 : SHL  (logical left)
//   op=2'b01 : SHR  (logical right)
//   op=2'b10 : SAR  (arithmetic right)
//   op=2'b11 : SHL  (default, same as 00)
// shift_amt is $clog2(WIDTH) bits wide.
module barrel_shifter #(
    parameter WIDTH = 8
) (
    input  wire [WIDTH-1:0]         in,
    input  wire [$clog2(WIDTH)-1:0] shift_amt,
    input  wire [1:0]               op,
    output reg  [WIDTH-1:0]         out
);
    wire signed [WIDTH-1:0] signed_in = in;

    always @(*) begin
        case (op)
            2'b00:   out = in << shift_amt;
            2'b01:   out = in >> shift_amt;
            2'b10:   out = signed_in >>> shift_amt;
            default: out = in << shift_amt;
        endcase
    end
endmodule
