#!/usr/bin/env python3
"""
FPGA 项目生成器 —— 仅需一个 config.txt

用法:
  python create_fpga_project.py config.txt

config.txt 必须包含 [project]、[module] 和 [port] 段。

示例 config.txt (3x3 int8 脉动阵列):
[project]
name = systolic_array_3x3
board = basys3

[module]
name = systolic_array_3x3_top

[port]
clk        : input  : 1
rst_n      : input  : 1
act_in_0   : input  : 8
act_in_1   : input  : 8
act_in_2   : input  : 8
wgt_in_0   : input  : 8
wgt_in_1   : input  : 8
wgt_in_2   : input  : 8
psum_out_0 : output : 32
psum_out_1 : output : 32
psum_out_2 : output : 32
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

            if current_section == "port":
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

    required_sections = ["project", "module", "port"]
    for sec in required_sections:
        if sec not in content:
            sys.exit(f"❌ 缺少 [{sec}] 段")

    proj = content["project"]
    mod = content["module"]
    port_sec = content["port"]

    for key in ["name", "board"]:
        if key not in proj:
            sys.exit(f"❌ [project] 中缺少 '{key} = ...'")
    if proj["board"] not in ("basys3", "nexys_a7"):
        sys.exit("❌ board 必须是 basys3 或 nexys_a7")

    if "name" not in mod:
        sys.exit("❌ [module] 中缺少 'name = ...'")

    if "ports" not in port_sec or not port_sec["ports"]:
        sys.exit("❌ [port] 段未定义任何端口")

    return {
        "project_name": proj["name"],
        "board": proj["board"],
        "top_module": mod["name"],
        "ports": port_sec["ports"]
    }


def generate_rtl_top(module_name, ports):
    input_ports = [p for p in ports if p["direction"] == "input"]
    output_ports = [p for p in ports if p["direction"] == "output"]
    inout_ports = [p for p in ports if p["direction"] == "inout"]

    def port_decl(p):
        vec = f"[{p['width']-1}:0]" if p["width"] > 1 else ""
        direction = p["direction"]
        spacing = " " * (6 - len(direction))
        return f"  {direction}{spacing}{vec} {p['name']}"

    all_decls = []
    if input_ports:
        all_decls.extend(port_decl(p) for p in input_ports)
    if inout_ports:
        all_decls.extend(port_decl(p) for p in inout_ports)
    if output_ports:
        all_decls.extend(port_decl(p) for p in output_ports)

    port_list = ",\n".join(all_decls)

    return textwrap.dedent(f"""\
`default_nettype wire
`timescale 1ns / 1ps

module {module_name} (
{port_list}
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

  // TODO: Replace this comment with your module instantiations or logic.

endmodule
""")


def generate_tb_top(module_name, ports):
    has_clk = any(p["name"] == "clk" and p["direction"] == "input" for p in ports)
    has_rst_n = any(p["name"] == "rst_n" and p["direction"] == "input" for p in ports)

    decl_lines = []
    for p in ports:
        vec = f"[{p['width']-1}:0] " if p["width"] > 1 else ""
        sig_type = "reg" if p["direction"] == "input" else "wire"
        decl_lines.append(f"  {sig_type} {vec}{p['name']};")

    clk_logic = "  initial begin clk = 0; forever #5 clk = ~clk; end\n" if has_clk else ""
    rst_logic = "  initial begin rst_n = 0; #20 rst_n = 1; end\n" if has_rst_n else ""

    port_inst = ",\n".join(f"    .{p['name']}({p['name']})" for p in ports)

    inputs = [p for p in ports if p["direction"] == "input" and p["name"] not in ("clk", "rst_n")]
    stimulus = ""
    if inputs:
        assigns = "\n".join(f"    {p['name']} = {p['width']}'d0;" for p in inputs)
        stimulus = f"{assigns}\n    #100;"

    return textwrap.dedent(f"""\
`default_nettype wire
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
    $display("okkk");
    $finish;
  end
endmodule
""")


def main():
    if len(sys.argv) != 2:
        print(__doc__.strip())
        sys.exit(1)

    config_file = sys.argv[1]
    cfg = parse_config(config_file)

    proj_name = cfg["project_name"]
    board = cfg["board"]
    top_module = cfg["top_module"]
    ports = cfg["ports"]

    # 创建项目目录
    os.makedirs(proj_name, exist_ok=True)
    os.chdir(proj_name)

    # 创建标准目录结构（含 tb/sim）
    os.makedirs("rtl", exist_ok=True)
    os.makedirs("tb", exist_ok=True)
    os.makedirs("tb/sim", exist_ok=True)
    os.makedirs("constraints", exist_ok=True)
    os.makedirs("scripts", exist_ok=True)

    # 防止 tb/sim 中的仿真产物被提交
    with open("tb/sim/.gitignore", "w", encoding="utf-8") as f:
        f.write("*\n!.gitignore\n")

    # 生成 RTL 顶层（仅当不存在时）
    rtl_top_path = f"rtl/{top_module}.sv"
    if not os.path.exists(rtl_top_path):
        with open(rtl_top_path, "w", encoding="utf-8") as f:
            f.write(generate_rtl_top(top_module, ports))
    else:
        print(f"⚠️  RTL 顶层模块已存在，跳过生成: {rtl_top_path}")

    # 生成测试平台
    with open("tb/tb_top.sv", "w", encoding="utf-8") as f:
        f.write(generate_tb_top(top_module, ports))

    # 生成约束文件
    with open(f"constraints/{board}.xdc", "w", encoding="utf-8") as f:
        f.write(f"# {board.upper()} 引脚约束模板 - 请根据实际需求编辑\n")

    # 生成根目录 .gitignore
    with open(".gitignore", "w", encoding="utf-8") as f:
        f.write(textwrap.dedent("""\
/build/
/tb/sim/
.vscode/
*.swp
*~
.vivado*
*.log
*.jou
*.str
xsim.dir/
"""))

    # 生成 CMakeLists.txt
    cmake_template = """cmake_minimum_required(VERSION 3.20)
project({proj_name} LANGUAGES NONE)

# ========================
# 用户输入参数
# ========================
set(VIVADO_PATH "" CACHE STRING "Vivado 安装路径（必须为 WSL 路径，例如 /mnt/e/Xilinx/Vivado/2024.1）")
if(NOT VIVADO_PATH)
  message(FATAL_ERROR "请通过 -DVIVADO_PATH=/mnt/... 指定 Vivado 路径")
endif()

set(BOARD "{board}" CACHE STRING "开发板型号 (basys3 或 nexys_a7)")

# ========================
# 工具路径（WSL 格式）
# ========================
set(XSIM_DIR "${{VIVADO_PATH}}/bin")

# ========================
# WSL 到 Windows 路径转换函数
# ========================
function(wsl_to_win_path LINUX_PATH WIN_PATH)
  if(LINUX_PATH MATCHES "^/mnt/[a-zA-Z]/")
    string(REGEX REPLACE "^/mnt/([a-zA-Z])/(.*)" "\\\\1:/\\\\2" WIN_TMP "${{LINUX_PATH}}")
    string(TOUPPER "${{WIN_TMP}}" WIN_TMP)
    set(${{WIN_PATH}} "${{WIN_TMP}}" PARENT_SCOPE)
  else()
    set(${{WIN_PATH}} "${{LINUX_PATH}}" PARENT_SCOPE)
  endif()
endfunction()

# ========================
# 收集源文件（相对路径）
# ========================
file(GLOB_RECURSE SOURCES LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/rtl/*.sv" "${{CMAKE_SOURCE_DIR}}/rtl/*.v")
file(GLOB_RECURSE TESTBENCH LIST_DIRECTORIES false RELATIVE "${{CMAKE_SOURCE_DIR}}" "${{CMAKE_SOURCE_DIR}}/tb/*.sv" "${{CMAKE_SOURCE_DIR}}/tb/*.v")

# 转为绝对路径（Linux/WSL 格式）
set(ABS_SOURCES "")
foreach(f IN LISTS SOURCES)
  list(APPEND ABS_SOURCES "${{CMAKE_SOURCE_DIR}}/${{f}}")
endforeach()

set(ABS_TESTBENCH "")
foreach(f IN LISTS TESTBENCH)
  list(APPEND ABS_TESTBENCH "${{CMAKE_SOURCE_DIR}}/${{f}}")
endforeach()

# ========================
# 板级配置
# ========================
if(BOARD STREQUAL "basys3")
  set(PART "xc7a35tcpg236-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/basys3.xdc")
elseif(BOARD STREQUAL "nexys_a7")
  set(PART "xc7a100tcsg324-1")
  set(CONSTRAINTS "${{CMAKE_SOURCE_DIR}}/constraints/nexys_a7.xdc")
else()
  message(FATAL_ERROR "不支持的开发板: ${{BOARD}}（请选择 basys3 或 nexys_a7）")
endif()

# ========================
# 转换为 Windows 路径（供 cmd.exe 使用）
# ========================
set(WINDOWS_SOURCES "")
foreach(f IN LISTS ABS_SOURCES)
  wsl_to_win_path("${{f}}" WIN_F)
  list(APPEND WINDOWS_SOURCES "${{WIN_F}}")
endforeach()

set(WINDOWS_TESTBENCH "")
foreach(f IN LISTS ABS_TESTBENCH)
  wsl_to_win_path("${{f}}" WIN_F)
  list(APPEND WINDOWS_TESTBENCH "${{WIN_F}}")
endforeach()

wsl_to_win_path("${{CONSTRAINTS}}" WINDOWS_CONSTRAINTS)
wsl_to_win_path("${{CMAKE_SOURCE_DIR}}" CMAKE_SOURCE_DIR_WIN)

# 仿真工作目录
set(SIM_WORK_DIR "${{CMAKE_SOURCE_DIR}}/tb/sim")
file(MAKE_DIRECTORY "${{SIM_WORK_DIR}}")  # 确保目录存在
wsl_to_win_path("${{SIM_WORK_DIR}}" SIM_WORK_DIR_WIN)

# 综合输出目录
set(SYNTH_DIR "${{CMAKE_BINARY_DIR}}/synth")
file(MAKE_DIRECTORY ${{SYNTH_DIR}})
wsl_to_win_path("${{SYNTH_DIR}}" SYNTH_DIR_WIN)

# Vivado 工具的 Windows 路径（关键！）
wsl_to_win_path("${{VIVADO_PATH}}" VIVADO_PATH_WIN)
wsl_to_win_path("${{XSIM_DIR}}" XSIM_DIR_WIN)

# ========================
# 将文件列表转为单个空格分隔字符串（关键！）
# ========================
string(REPLACE ";" " " WINDOWS_SOURCES_STR "${{WINDOWS_SOURCES}}")
string(REPLACE ";" " " WINDOWS_TESTBENCH_STR "${{WINDOWS_TESTBENCH}}")
set(ALL_SV_FILES_STR "${{WINDOWS_SOURCES_STR}} ${{WINDOWS_TESTBENCH_STR}}")

# ========================
# 仿真目标
# ========================
add_custom_target(simulate
  # 清理旧仿真数据
  COMMAND ${{CMAKE_COMMAND}} -E remove_directory "${{SIM_WORK_DIR_WIN}}/xsim.dir"
  COMMAND ${{CMAKE_COMMAND}} -E remove "${{SIM_WORK_DIR_WIN}}/sim1.wdb" "${{SIM_WORK_DIR_WIN}}/sim1.wcfg" "${{SIM_WORK_DIR_WIN}}/xsim.log"

  # 编译 SystemVerilog 文件
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR_WIN}}/xvlog.bat --sv ${{ALL_SV_FILES_STR}}"
  VERBATIM

  # 生成仿真快照
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR_WIN}}/xelab.bat tb_top -snapshot sim1 -debug all"
  VERBATIM

  # 运行仿真
  COMMAND cmd.exe /c "cd /d ${{SIM_WORK_DIR_WIN}} && ${{XSIM_DIR_WIN}}/xsim.bat sim1 -runall"
  VERBATIM

  COMMENT "▶️ 正在运行仿真..."
)

# ========================
# 比特流生成目标
# ========================
add_custom_target(bitstream
  COMMAND cmd.exe /c "${{VIVADO_PATH_WIN}}/bin/vivado.bat -mode batch -source ${{CMAKE_SOURCE_DIR_WIN}}/scripts/build_bitstream.tcl -tclargs {proj_name} ${{PART}} ${{CMAKE_SOURCE_DIR_WIN}}/rtl ${{WINDOWS_CONSTRAINTS}} ${{SYNTH_DIR_WIN}}"
  WORKING_DIRECTORY ${{CMAKE_BINARY_DIR}}
  VERBATIM
  COMMENT "⚙️ 正在生成比特流..."
)

# ========================
# 调试信息（可选）
# ========================
message(STATUS "Vivado (WSL):     ${{VIVADO_PATH}}")
message(STATUS "Vivado (Win):     ${{VIVADO_PATH_WIN}}")
message(STATUS "XSIM_DIR (Win):   ${{XSIM_DIR_WIN}}")
message(STATUS "Sim work dir:     ${{SIM_WORK_DIR_WIN}}")
"""

    cmake_content = cmake_template.format(proj_name=proj_name, board=board)
    with open("CMakeLists.txt", "w", encoding="utf-8") as f:
        f.write(cmake_content)

    # 生成 Tcl 构建脚本
    tcl_template = """if {{$argc < 5}} {{
    error "用法: build_bitstream.tcl <proj_name> <part> <rtl_dir> <xdc_file> <proj_dir>"
}}

set proj_name [lindex $argv 0]
set part [lindex $argv 1]
set rtl_dir [lindex $argv 2]
set xdc_file [lindex $argv 3]
set proj_dir [lindex $argv 4]

create_project $proj_name $proj_dir -part $part

proc add_rtl_files {{dir}} {{
    foreach f [glob -nocomplain -directory $dir *] {{
        if {{[file isdirectory $f]}} {{
            add_rtl_files $f
        }} elseif {{[string match -nocase "*.v" $f] || [string match -nocase "*.sv" $f]}} {{
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
puts "✅ 比特流已生成: ${{proj_dir}}/${{proj_name}}.bit"
"""

    tcl_content = tcl_template.format(top_module=top_module)
    with open("scripts/build_bitstream.tcl", "w", encoding="utf-8") as f:
        f.write(tcl_content)

    # 输出成功信息
    print(f"\n🎉 项目 '{proj_name}' 创建成功！")
    print(f"   • 顶层模块: {top_module}")
    print(f"   • 开发板:   {board}")
    print(f"\n📁 RTL 顶层: ./rtl/{top_module}.sv （可编辑）")
    print(f"🧪 测试平台: ./tb/tb_top.sv")
    print(f"📂 仿真输出: ./tb/sim/ （已预创建）")
    print(f"🔧 约束模板: ./constraints/{board}.xdc")
    print(f"\n🚀 快速开始仿真:")
    print(f"   cd {proj_name}")
    print(f"   mkdir build && cd build")
    print(f"   cmake .. -DVIVADO_PATH=/your/vivado/path -DBOARD={board}")
    print(f"   cmake --build . --target simulate")
    print(f"\n💡 提示: 实现你的设计后，可运行 'cmake --build . --target bitstream'")


if __name__ == "__main__":
    main()