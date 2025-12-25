#!/usr/bin/env python3
"""
FPGA 项目生成器 —— 仅需一个 config.txt

用法:
  python create_fpga_project.py config.txt

config.txt 必须包含 [project] 和 [module] 段。
"""

import os
import sys
import re
import textwrap


def parse_config(config_path):
    if not os.path.isfile(config_path):
        sys.exit(f"❌ 错误: 配置文件 '{config_path}' 不存在")

    content = {}
    current_section = None

    # 👇 关键修改：使用 utf-8-sig 自动处理 BOM
    with open(config_path, encoding="utf-8-sig") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                content[current_section] = {}
                continue

            if current_section is None:
                sys.exit(f"❌ 第 {line_num} 行：不在任何段中")

            if ":" in line and current_section == "port":
                # 端口行: name : direction : width
                parts = [p.strip() for p in re.split(r":", line, maxsplit=2)]
                if len(parts) != 3:
                    sys.exit(f"❌ 第 {line_num} 行端口格式错误: 应为 'name : dir : width'")
                name, direction, width_str = parts
                try:
                    width = int(width_str)
                except ValueError:
                    sys.exit(f"❌ 第 {line_num} 行：宽度必须是整数")
                if direction not in ("input", "output", "inout"):
                    sys.exit(f"❌ 第 {line_num} 行：方向必须是 input/output/inout")
                if "ports" not in content[current_section]:
                    content[current_section]["ports"] = []
                content[current_section]["ports"].append({
                    "name": name, "direction": direction, "width": width
                })
            elif "=" in line:
                key, val = [x.strip() for x in line.split("=", 1)]
                content[current_section][key] = val
            else:
                sys.exit(f"❌ 第 {line_num} 行：无法解析")

    # 校验必要字段
    if "project" not in content:
        sys.exit("❌ 缺少 [project] 段")
    if "module" not in content:
        sys.exit("❌ 缺少 [module] 段")

    proj = content["project"]
    mod = content["module"]

    if "name" not in proj:
        sys.exit("❌ [project] 中缺少 'name = ...'")
    if "board" not in proj:
        sys.exit("❌ [project] 中缺少 'board = ...'")
    if proj["board"] not in ("basys3", "nexys_a7"):
        sys.exit("❌ board 必须是 basys3 或 nexys_a7")
    if "name" not in mod:
        sys.exit("❌ [module] 中缺少 'name = ...'")
    if "ports" not in mod:
        sys.exit("❌ [port] 段未定义任何端口")

    return {
        "project_name": proj["name"],
        "board": proj["board"],
        "top_module": mod["name"],
        "ports": mod["ports"]
    }


def generate_tb_top(module_name, ports):
    has_clk = any(p["name"] == "clk" and p["direction"] == "input" for p in ports)
    has_rst_n = any(p["name"] == "rst_n" and p["direction"] == "input" for p in ports)

    decl_lines = []
    for p in ports:
        vec = f"[{p['width']-1}:0] " if p["width"] > 1 else ""
        sig_type = "reg" if p["direction"] == "input" else "wire"
        decl_lines.append(f"  {sig_type} {vec}{p['name']};")

    clk_logic = ""
    rst_logic = ""
    if has_clk:
        clk_logic = "  initial begin clk = 0; forever #5 clk = ~clk; end\n"
    if has_rst_n:
        rst_logic = "  initial begin rst_n = 0; #20 rst_n = 1; end\n"

    port_inst = ",\n".join(f"    .{p['name']}({p['name']})" for p in ports)

    stimulus = ""
    inputs = [p for p in ports if p["direction"] == "input" and p["name"] not in ("clk", "rst_n")]
    if inputs:
        assigns = "\n".join(f"    {p['name']} = {p['width']}'d0;" for p in inputs)
        stimulus = f"{assigns}\n    #100;"

    return textwrap.dedent(f"""\
`timescale 1ns / 1ps
module tb_top;
{chr(10).join(decl_lines)}

{clk_logic}
{rst_logic}
  {module_name} dut (
{port_inst}
  );

  initial begin
{stimulus}
    $display("✅ 仿真完成");
    $finish;
  end
endmodule
""")


def main():
    if len(sys.argv) != 2:
        sys.exit("用法: python create_fpga_project.py <config.txt>")

    config_file = sys.argv[1]
    cfg = parse_config(config_file)

    proj_name = cfg["project_name"]
    board = cfg["board"]
    top_module = cfg["top_module"]
    ports = cfg["ports"]

    # 创建项目目录
    os.makedirs(proj_name, exist_ok=True)
    os.chdir(proj_name)

    # 创建目录结构
    for d in ["rtl", "tb", "constraints", "scripts"]:
        os.makedirs(d, exist_ok=True)

    # 生成 tb_top.sv
    with open("tb/tb_top.sv", "w", encoding="utf-8") as f:
        f.write(generate_tb_top(top_module, ports))

    # 生成约束文件
    with open(f"constraints/{board}.xdc", "w", encoding="utf-8") as f:
        f.write(f"# {board} 引脚约束文件 - 请根据实际需求编辑\n")

    # 生成 .gitignore
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write("/build/\n/tb/sim/\n.vscode/\n*.swp\n*~\n")

    # 生成 CMakeLists.txt
    part = "xc7a35tcpg236-1" if board == "basys3" else "xc7a100tcsg324-1"
    cmake_content = textwrap.dedent(f'''\
cmake_minimum_required(VERSION 3.20)
project({proj_name} LANGUAGES NONE)
set(VIVADO_PATH "E:/Xilinx/Vivado/2024.1" CACHE STRING "Vivado 安装路径")
set(XSIM_DIR "${{VIVADO_PATH}}/bin")
set(BOARD "{board}")
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

file(GLOB_RECURSE SOURCES LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/rtl/*.sv" "${{CMAKE_SOURCE_DIR}}/rtl/*.v")
file(GLOB_RECURSE TESTBENCH LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/tb/*.sv" "${{CMAKE_SOURCE_DIR}}/tb/*.v")

set(ABS_SOURCES "") ; foreach(f ${{SOURCES}}) list(APPEND ABS_SOURCES "${{CMAKE_SOURCE_DIR}}/${{f}}") endforeach()
set(ABS_TESTBENCH "") ; foreach(f ${{TESTBENCH}}) list(APPEND ABS_TESTBENCH "${{CMAKE_SOURCE_DIR}}/${{f}}") endforeach()

if(BOARD STREQUAL "basys3")
  set(PART "xc7a35tcpg236-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/basys3.xdc")
else()
  set(PART "xc7a100tcsg324-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/nexys_a7.xdc")
endif()

set(WINDOWS_SOURCES "") ; foreach(f ${{ABS_SOURCES}}) wsl_to_win_path("${{f}}" WIN_F) list(APPEND WINDOWS_SOURCES "${{WIN_F}}") endforeach()
set(WINDOWS_TESTBENCH "") ; foreach(f ${{ABS_TESTBENCH}}) wsl_to_win_path("${{f}}" WIN_F) list(APPEND WINDOWS_TESTBENCH "${{WIN_F}}") endforeach()
if(CONSTRAINTS) wsl_to_win_path("${{CONSTRAINTS}}" WINDOWS_CONSTRAINTS) endif()
wsl_to_win_path("${{CMAKE_SOURCE_DIR}}" CMAKE_SOURCE_DIR_WIN)

set(SIM_WORK_DIR "${{CMAKE_SOURCE_DIR}}/tb/sim")
file(MAKE_DIRECTORY ${{SIM_WORK_DIR}})
wsl_to_win_path("${{SIM_WORK_DIR}}" SIM_WORK_DIR_WIN)

set(SYNTH_DIR "${{CMAKE_BINARY_DIR}}/synth")
file(MAKE_DIRECTORY ${{SYNTH_DIR}})
wsl_to_win_path("${{SYNTH_DIR}}" SYNTH_DIR_WIN)

if(WINDOWS_CONSTRAINTS)
  set(CONSTRAINT_ARG "\\\\\\"${{WINDOWS_CONSTRAINTS}}\\\\\\"")
else()
  set(CONSTRAINT_ARG "")
endif()

add_custom_target(simulate
  COMMAND ${{CMAKE_COMMAND}} -E remove_directory ${{SIM_WORK_DIR_WIN}}/xsim.dir
  COMMAND ${{CMAKE_COMMAND}} -E remove ${{SIM_WORK_DIR_WIN}}/sim1.wdb ${{SIM_WORK_DIR_WIN}}/sim1.wcfg ${{SIM_WORK_DIR_WIN}}/xsim.log
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xvlog.bat --sv ${{WINDOWS_SOURCES}} ${{WINDOWS_TESTBENCH}}"
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xelab.bat tb_top -snapshot sim1 -debug all"
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR}}/xsim.bat sim1 -runall"
  COMMENT "▶️ 正在 tb/sim/ 中运行仿真..."
)

add_custom_target(bitstream
  COMMAND cmd.exe /c "${{VIVADO_PATH}}/bin/vivado.bat -mode batch -source ${{CMAKE_SOURCE_DIR_WIN}}/scripts/build_bitstream.tcl -tclargs {proj_name} ${{PART}} ${{CMAKE_SOURCE_DIR_WIN}}/rtl ${{CONSTRAINT_ARG}} ${{SYNTH_DIR_WIN}}"
  WORKING_DIRECTORY ${{CMAKE_BINARY_DIR}}
  COMMENT "⚙️ 正在 build/synth/ 中生成比特流..."
)
''')
    with open("CMakeLists.txt", "w", encoding="utf-8") as f:
        f.write(cmake_content)

    # 生成 Tcl 脚本
    tcl_content = textwrap.dedent(f'''\
if {{$argc < 4}} {{ error "参数不足" }}
set proj_name [lindex $argv 0]
set part [lindex $argv 1]
set rtl_dir [lindex $argv 2]
set xdc_file [expr {{$argc >= 5 ? [lindex $argv 3] : ""}}]
set proj_dir [expr {{$argc >= 5 ? [lindex $argv 4] : "."}}]

create_project $proj_name $proj_dir -part $part

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

if {{$xdc_file != "" && [file exists $xdc_file]}} {{
    add_files -fileset constrs_1 -norecurse $xdc_file
}}

set_property top {top_module} [current_fileset]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -jobs 4
wait_on_run impl_1

write_bitstream -force ${{proj_dir}}/${{proj_name}}.bit
puts "✅ 比特流已生成"
''')
    with open("scripts/build_bitstream.tcl", "w", encoding="utf-8") as f:
        f.write(tcl_content)

    print(f"✅ 项目 '{proj_name}' 创建成功！")
    print(f" 顶层模块: {top_module}")
    print(f" 开发板: {board}")
    print(f"\n📁 请将你的 RTL 文件放入: {proj_name}/rtl/")
    print(f"🚀 构建命令:")
    print(f"  cd {proj_name}")
    print(f"  mkdir build && cd build")
    print(f"  cmake .. -DBOARD={board}")
    print(f"  cmake --build . --target simulate")


if __name__ == "__main__":
    main()