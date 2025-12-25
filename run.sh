# 进入项目目录
cd /mnt/d/projects/uvm_test/example

# 清理并重建
rm -rf build && mkdir build && cd build

# 配置（注意：VIVADO_PATH 必须是 WSL 路径！）
cmake .. -DVIVADO_PATH=/mnt/e/Xilinx/Vivado/2024.1 -DBOARD=basys3

# 运行仿真
cmake --build . --target simulate