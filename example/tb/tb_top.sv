`default_nettype wire
`timescale 1ns / 1ps
module tb_top;
  reg clk;
  reg rst_n;
  reg [7:0] act_in_0;
  reg [7:0] act_in_1;
  reg [7:0] act_in_2;
  reg [7:0] wgt_in_0;
  reg [7:0] wgt_in_1;
  reg [7:0] wgt_in_2;
  wire [31:0] psum_out_0;
  wire [31:0] psum_out_1;
  wire [31:0] psum_out_2;

  initial begin clk = 0; forever #5 clk = ~clk; end

  initial begin rst_n = 0; #20 rst_n = 1; end

  add3_top dut (
    .clk(clk),
    .rst_n(rst_n),
    .act_in_0(act_in_0),
    .act_in_1(act_in_1),
    .act_in_2(act_in_2),
    .wgt_in_0(wgt_in_0),
    .wgt_in_1(wgt_in_1),
    .wgt_in_2(wgt_in_2),
    .psum_out_0(psum_out_0),
    .psum_out_1(psum_out_1),
    .psum_out_2(psum_out_2)
  );

 // 测试激励
  initial begin
   // === 1. 启用波形记录（FST 更高效）===
    $dumpfile("waveform.vcd");
    $dumpvars(0, tb_top);  // 转储整个设计层次
    rst_n = 0;
    act_in_0 = 0; act_in_1 = 0; act_in_2 = 0;
    wgt_in_0 = 0; wgt_in_1 = 0; wgt_in_2 = 0;
    #20 rst_n = 1;

    // Test 1: 全正数
    act_in_0 = 10;   wgt_in_0 = 20;   // 30
    act_in_1 = 50;   wgt_in_1 = 60;   // 110
    act_in_2 = 127;  wgt_in_2 = 1;    // 128
    #20;

    // Test 2: 全负数 ← 重点修改这里！
    act_in_0 = -10;   wgt_in_0 = -20;   // -30
    act_in_1 = -50;   wgt_in_1 = -60;   // -110
    act_in_2 = -128;  wgt_in_2 = -1;    // -129
    #20;

    // Test 3: 正负混合
    act_in_0 = 127;   wgt_in_0 = -128;  // -1
    act_in_1 = -128;  wgt_in_1 = 127;   // -1
    act_in_2 = 0;     wgt_in_2 = 0;      // 0
    #20;

    // Test 4: 边界值
    act_in_0 = 127;  wgt_in_0 = 127;   // 254
    act_in_1 = -128; wgt_in_1 = -128;  // -256
    act_in_2 = 100;  wgt_in_2 = -100;  // 0
    #20;

    $display("3 int8 add test completed.");
    $finish;
  end
   always @(posedge clk) begin
  if (rst_n) begin
    $display("psum = [%0d, %0d, %0d]",
        $signed(psum_out_0),
        $signed(psum_out_1),
        $signed(psum_out_2)
    );
  end
end
endmodule

