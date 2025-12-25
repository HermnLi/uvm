`default_nettype wire
`timescale 1ns / 1ps

module add3_cell (
  input        clk,
  input        rst_n,
  // 三路激活输入（int8）
  input  [7:0] act_in_0,
  input  [7:0] act_in_1,
  input  [7:0] act_in_2,
  // 三路权重输入（int8）
  input  [7:0] wgt_in_0,
  input  [7:0] wgt_in_1,
  input  [7:0] wgt_in_2,
  // 三路部分和输出（int32）
  output [31:0] psum_out_0,
  output [31:0] psum_out_1,
  output [31:0] psum_out_2
);

  // 第0组：act_in_0 + wgt_in_0
  assign psum_out_0 = $signed({{24{act_in_0[7]}}, act_in_0}) +
                      $signed({{24{wgt_in_0[7]}}, wgt_in_0});

  // 第1组：act_in_1 + wgt_in_1
  assign psum_out_1 = $signed({{24{act_in_1[7]}}, act_in_1}) +
                      $signed({{24{wgt_in_1[7]}}, wgt_in_1});

  // 第2组：act_in_2 + wgt_in_2
  assign psum_out_2 = $signed({{24{act_in_2[7]}}, act_in_2}) +
                      $signed({{24{wgt_in_2[7]}}, wgt_in_2});

endmodule