`default_nettype wire
`timescale 1ns / 1ps

module add3_top (
  input  clk,
  input  rst_n,
  input [7:0] act_in_0,
  input [7:0] act_in_1,
  input [7:0] act_in_2,
  input [7:0] wgt_in_0,
  input [7:0] wgt_in_1,
  input [7:0] wgt_in_2,
  output[31:0] psum_out_0,
  output[31:0] psum_out_1,
  output[31:0] psum_out_2
);

  // ==================================================================
  // 📌 请在此处实例化你的子模块（如 PE 阵列、FIFO、控制器等）
  // 示例：
  //   my_pe_array u_pe (
  //     .clk(clk),
  //     .rst_n(rst_n),
  //     .act_in(act_in_0),
  //     ...
  //   );
  // ==================================================================
   add3_cell u_add3_cell (
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
  // TODO: Replace this comment with your module instantiations or logic.

endmodule
