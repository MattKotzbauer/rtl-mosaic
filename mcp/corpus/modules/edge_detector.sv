// edge_detector: 1-cycle pulses on rise/fall edges of `sig`.
// rst_n is active-low async reset. Outputs are registered so they
// align cleanly to the clock cycle following the detected edge.
module edge_detector (
    input  wire clk,
    input  wire rst_n,
    input  wire sig,
    output reg  rise,
    output reg  fall
);
    reg sig_d;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sig_d <= 1'b0;
            rise  <= 1'b0;
            fall  <= 1'b0;
        end else begin
            sig_d <= sig;
            rise  <= ( sig & ~sig_d);
            fall  <= (~sig &  sig_d);
        end
    end
endmodule
