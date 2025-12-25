#!/usr/bin/env python3
"""
FPGA 项目一键生成脚本（支持 Vivado + CMake + WSL）
功能：
- 自动生成符合现代验证结构的项目目录
- 仿真输出限定在 tb/sim/（与综合分离）
- 支持 Basys3 / Nexys A7 开发板
- 生成 CMakeLists.txt、Tcl 脚本、.gitignore 等
- 所有路径自动适配 WSL → Windows（用于调用 Vivado）

使用示例：
  python create_fpga_project.py my_add --top my_add_top --board basys3
"""

import os
import argparse
import textwrap


def main():
    # === 命令行参数解析 ===
    parser = argparse.ArgumentParser(description="创建结构化的 FPGA 项目（Vivado + CMake）")
    parser.add_argument("project_name", help="项目名称（如 my_add）")
    parser.add_argument("--top", required=True, help="顶层 RTL 模块名（如 my_add_top）")
    parser.add_argument(
        "--board",
        choices=["basys3", "nexys_a7"],
        default="basys3",
        help="目标开发板（默认：basys3）"
    )
    args = parser.parse_args()

    proj_name = args.project_name
    top_module = args.top
    board = args.board

    # === 创建项目根目录并进入 ===
    os.makedirs(proj_name, exist_ok=True)
    os.chdir(proj_name)

    # === 创建标准目录结构 ===
    dirs = [
        "rtl",          # RTL 源码（支持子目录）
        "tb",           # 测试平台根目录
        "constraints",  # 约束文件 (.xdc)
        "scripts",      # Vivado Tcl 脚本
        "tb/env",       # 验证环境组件（可选）
        "tb/seq",       # 序列（sequences）
        "tb/tc",        # 测试用例（testcases）
        "tb/tl"         # 事务层（transaction level）
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # === 生成占位文件 ===
    # rtl/ 中的示例顶层模块
    with open("rtl/example.sv", "w", encoding="utf-8") as f:
        f.write(f"module {top_module}();\n // TODO: 在此处编写你的 RTL 代码\nendmodule\n")

    # tb/ 中的顶层测试平台
    with open("tb/tb_top.sv", "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(f"""\
module tb_top;
  {top_module} dut (); // 实例化 DUT

  initial begin
    $display("正在运行 {top_module} 的测试平台...");
    #100; // 简单延时
    $finish; // 结束仿真
  end
endmodule
"""))

    # === 生成约束文件（.xdc）===
    if board == "basys3":
        xdc_content = "# Basys3 引脚约束文件 - 请根据实际需求编辑\n"
    else:
        xdc_content = "# Nexys A7 引脚约束文件 - 请根据实际需求编辑\n"
    with open(f"constraints/{board}.xdc", "w", encoding="utf-8") as f:
        f.write(xdc_content)

    # === 生成 .gitignore ===
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""\
# 构建与仿真输出目录（不提交到 Git）
/build/
/tb/sim/

# 编辑器临时文件
.vscode/
*.swp
*~
"""))

    # === 生成 CMakeLists.txt ===
    cmake_content = generate_cmake(proj_name, top_module, board)
    with open("CMakeLists.txt", "w", encoding="utf-8") as f:
        f.write(cmake_content)

    # === 生成 Vivado Tcl 脚本 ===
    tcl_content = generate_tcl(top_module)
    with open("scripts/build_bitstream.tcl", "w", encoding="utf-8") as f:
        f.write(tcl_content)

    # === 打印成功信息 ===
    print(f"✅ 项目 '{proj_name}' 创建成功！")
    print(f" 顶层模块: {top_module}")
    print(f" 目标开发板: {board}")
    print("\n📁 项目结构:")
    print(f" {proj_name}/")
    print(f" ├── rtl/             # RTL 源代码（支持子目录）")
    print(f" ├── tb/              # 测试平台（仿真输出在 tb/sim/）")
    print(f" ├── constraints/     # 引脚约束文件 (.xdc)")
    print(f" ├── scripts/         # Vivado 自动化脚本")
    print(f" └── CMakeLists.txt   # 构建配置文件")
    print("\n🚀 下一步操作:")
    print(f" cd {proj_name}")
    print(f" mkdir build && cd build")
    print(f" cmake .. -DBOARD={board}")
    print(f" cmake --build . --target simulate   # 在 tb/sim/ 中运行仿真")
    print(f" cmake --build . --target bitstream  # 在 build/synth/ 中生成比特流")


def generate_cmake(proj_name: str, top_module: str, board: str) -> str:
    """生成 CMakeLists.txt 内容（带中文注释）"""
    part = "xc7a35tcpg236-1" if board == "basys3" else "xc7a100tcsg324-1"
    return textwrap.dedent(f'''\
# CMake 最低版本要求
cmake_minimum_required(VERSION 3.20)
project({proj_name} LANGUAGES NONE)

# ==============================
# 用户可配置项
# ==============================
set(VIVADO_PATH "E:/Xilinx/Vivado/2024.1" CACHE STRING "Vivado 安装路径")
set(XSIM_DIR "${{VIVADO_PATH}}/bin")

# 默认开发板（可通过 -DBOARD=... 覆盖）
set(BOARD "{board}" CACHE STRING "目标开发板（例如 basys3, nexys_a7）")
set_property(CACHE BOARD PROPERTY STRINGS "" "basys3" "nexys_a7")

# ==============================
# 路径转换函数：WSL → Windows
# （用于在 WSL 中调用 Windows 版 Vivado）
# ==============================
function(wsl_to_win_path LINUX_PATH WIN_PATH)
  if(LINUX_PATH MATCHES "^/mnt/([a-z])/")
    string(REGEX REPLACE "^/mnt/([a-z])/.+" "\\\\1" DRIVE_LETTER "${{LINUX_PATH}}")
    string(TOUPPER "${{DRIVE_LETTER}}" DRIVE_LETTER)
    string(REGEX REPLACE "^/mnt/[a-z]/" "${{DRIVE_LETTER}}:/" WIN_PATH_TMP "${{LINUX_PATH}}")
    set(${{WIN_PATH}} "${{WIN_PATH_TMP}}" PARENT_SCOPE)
  else()
    set(${{WIN_PATH}} "${{LINUX_PATH}}" PARENT_SCOPE)
  endif()
endfunction()

# ==============================
# 递归收集 RTL 和 TB 源文件（支持子目录）
# ==============================
file(GLOB_RECURSE SOURCES LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/rtl/*.sv" "${{CMAKE_SOURCE_DIR}}/rtl/*.v")
file(GLOB_RECURSE TESTBENCH LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/tb/*.sv" "${{CMAKE_SOURCE_DIR}}/tb/*.v")

# 转为绝对路径
set(ABS_SOURCES "")
set(ABS_TESTBENCH "")
foreach(f ${{SOURCES}})
  list(APPEND ABS_SOURCES "${{CMAKE_SOURCE_DIR}}/${{f}}")
endforeach()
foreach(f ${{TESTBENCH}})
  list(APPEND ABS_TESTBENCH "${{CMAKE_SOURCE_DIR}}/${{f}}")
endforeach()

# ==============================
# 根据开发板设置器件型号和约束文件
# ==============================
if(BOARD STREQUAL "basys3")
  set(PART "xc7a35tcpg236-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/basys3.xdc")
elseif(BOARD STREQUAL "nexys_a7")
  set(PART "xc7a100tcsg324-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/nexys_a7.xdc")
else()
  message(FATAL_ERROR "不支持的开发板: ${{BOARD}}")
endif()

# ==============================
# 将所有路径转换为 Windows 格式（供 Vivado 使用）
# ==============================
set(WINDOWS_SOURCES "")
foreach(f ${{ABS_SOURCES}})
  wsl_to_win_path("${{f}}" WIN_F)
  list(APPEND WINDOWS_SOURCES "${{WIN_F}}")
endforeach()

set(WINDOWS_TESTBENCH "")
foreach(f ${{ABS_TESTBENCH}})
  wsl_to_win_path("${{f}}" WIN_F)
  list(APPEND WINDOWS_TESTBENCH "${{WIN_F}}")
endforeach()

if(CONSTRAINTS)
  wsl_to_win_path("${{CONSTRAINTS}}" WINDOWS_CONSTRAINTS)
endif()
wsl_to_win_path("${{CMAKE_SOURCE_DIR}}" CMAKE_SOURCE_DIR_WIN)

# ==============================
# 仿真工作区：固定在 tb/sim/ 目录下
# ==============================
set(SIM_WORK_DIR "${{CMAKE_SOURCE_DIR}}/tb/sim")
file(MAKE_DIRECTORY ${{SIM_WORK_DIR}})
wsl_to_win_path("${{SIM_WORK_DIR}}" SIM_WORK_DIR_WIN)

# ==============================
# 综合工作区：位于 build/synth/
# ==============================
set(SYNTH_DIR "${{CMAKE_BINARY_DIR}}/synth")
file(MAKE_DIRECTORY ${{SYNTH_DIR}})
wsl_to_win_path("${{SYNTH_DIR}}" SYNTH_DIR_WIN)

# ==============================
# 约束文件参数（若存在）
# ==============================
if(WINDOWS_CONSTRAINTS)
  set(CONSTRAINT_ARG "\\\\\\"${{WINDOWS_CONSTRAINTS}}\\\\\\"")
else()
  set(CONSTRAINT_ARG "")
endif()

# ==============================
# 构建目标定义
# ==============================

# ▶️ 仿真目标：在 tb/sim/ 中执行 XSim
add_custom_target(simulate
  COMMAND ${{CMAKE_COMMAND}} -E remove_directory ${{SIM_WORK_DIR_WIN}}/xsim.dir
  COMMAND ${{CMAKE_COMMAND}} -E remove ${{SIM_WORK_DIR_WIN}}/sim1.wdb ${{SIM_WORK_DIR_WIN}}/sim1.wcfg ${{SIM_WORK_DIR_WIN}}/xsim.log
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xvlog.bat --sv ${{WINDOWS_SOURCES}} ${{WINDOWS_TESTBENCH}}"
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xelab.bat tb_top -snapshot sim1 -debug all"
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xsim.bat sim1 -runall"
  COMMENT "▶️ 正在 tb/sim/ 中运行仿真..."
)

# ⚙️ 比特流生成目标：在 build/synth/ 中运行 Vivado
add_custom_target(bitstream
  COMMAND cmd.exe /c "${{VIVADO_PATH}}/bin/vivado.bat -mode batch -source ${{CMAKE_SOURCE_DIR_WIN}}/scripts/build_bitstream.tcl -tclargs {proj_name} ${{PART}} ${{CMAKE_SOURCE_DIR_WIN}}/rtl ${{CONSTRAINT_ARG}} ${{SYNTH_DIR_WIN}}"
  WORKING_DIRECTORY ${{CMAKE_BINARY_DIR}}
  COMMENT "⚙️ 正在 build/synth/ 中生成比特流..."
)

# 🧹 清理仿真产物（仅 tb/sim/）
add_custom_target(clean_sim
  COMMAND ${{CMAKE_COMMAND}} -E remove_directory ${{SIM_WORK_DIR}}/xsim.dir
  COMMAND ${{CMAKE_COMMAND}} -E remove ${{SIM_WORK_DIR}}/sim1.wdb ${{SIM_WORK_DIR}}/sim1.wcfg ${{SIM_WORK_DIR}}/xsim.log
  COMMENT "🧹 清理 tb/sim/ 目录..."
)

# 🧹 清理综合产物（仅 build/synth/）
add_custom_target(clean_bitstream
  COMMAND ${{CMAKE_COMMAND}} -E remove_directory ${{SYNTH_DIR}}
  COMMENT "🧹 清理 build/synth/ 目录..."
)

# 🧹 清理全部产物
add_custom_target(clean_artifacts
  DEPENDS clean_sim clean_bitstream
  COMMENT "🧹 清理所有生成的中间文件..."
)

# 🔁 重建目标
add_custom_target(rebuild_sim
  DEPENDS clean_sim simulate
  COMMENT "🔁 重新构建并运行仿真..."
)
add_custom_target(rebuild_bitstream
  DEPENDS clean_bitstream bitstream
  COMMENT "🔁 重新生成比特流..."
)

# ==============================
# 构建时打印配置信息
# ==============================
message(STATUS "项目名称: {proj_name}")
message(STATUS "顶层模块: {top_module}")
message(STATUS "目标开发板: ${{BOARD}}")
message(STATUS "FPGA 器件型号: ${{PART}}")
''')


def generate_tcl(top_module: str) -> str:
    """生成 Vivado Tcl 脚本（支持递归添加 rtl/ 下所有 .v/.sv 文件）"""
    return textwrap.dedent(f'''\
# Vivado 批处理脚本：自动生成比特流
# 参数顺序: <proj_name> <part> <rtl_dir> [xdc_file] <proj_dir>

if {{$argc < 4}} {{
    error "用法: <proj_name> <part> <rtl_dir> \[xdc\] <proj_dir>"
}}

set proj_name [lindex $argv 0]
set part [lindex $argv 1]
set rtl_dir [lindex $argv 2]
set xdc_file [expr {{$argc >= 5 ? [lindex $argv 3] : ""}}]
set proj_dir [expr {{$argc >= 5 ? [lindex $argv 4] : "."}}]

# 创建工程
create_project $proj_name $proj_dir -part $part

# 递归添加所有 RTL 源文件（.v 和 .sv）
proc add_rtl_files {{dir}} {{
    foreach f [glob -nocomplain -directory $dir *] {{
        if {{[file isdirectory $f]}} {{
            add_rtl_files $f
        }} elseif {{[string match "*.v" $f] || [string match "*.sv" $f]}} {{
            add_files -norecurse $f
        }}
    }}
}}
add_rtl_files $rtl_dir

# 添加约束文件（如果提供）
if {{$xdc_file != "" && [file exists $xdc_file]}} {{
    add_files -fileset constrs_1 -norecurse $xdc_file
}}

# 设置顶层设计模块
set_property top {top_module} [current_fileset]

# 启动综合与实现流程
launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -jobs 4
wait_on_run impl_1

# 生成比特流文件
write_bitstream -force ${{proj_dir}}/${{proj_name}}.bit
puts "✅ 比特流已生成: ${{proj_dir}}/${{proj_name}}.bit"
''')


if __name__ == "__main__":
    main()