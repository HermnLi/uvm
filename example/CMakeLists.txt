cmake_minimum_required(VERSION 3.20)
project(example LANGUAGES NONE)

# ========================
# 用户输入参数
# ========================
set(VIVADO_PATH "" CACHE STRING "Vivado 安装路径（必须为 WSL 路径，例如 /mnt/e/Xilinx/Vivado/2024.1）")
if(NOT VIVADO_PATH)
  message(FATAL_ERROR "请通过 -DVIVADO_PATH=/mnt/... 指定 Vivado 路径")
endif()

set(BOARD "basys3" CACHE STRING "开发板型号 (basys3 或 nexys_a7)")

# ========================
# 工具路径（WSL 格式）
# ========================
set(XSIM_DIR "${VIVADO_PATH}/bin")

# ========================
# WSL 到 Windows 路径转换函数
# ========================
function(wsl_to_win_path LINUX_PATH WIN_PATH)
  if(LINUX_PATH MATCHES "^/mnt/[a-zA-Z]/")
    string(REGEX REPLACE "^/mnt/([a-zA-Z])/(.*)" "\\1:/\\2" WIN_TMP "${LINUX_PATH}")
    string(TOUPPER "${WIN_TMP}" WIN_TMP)
    set(${WIN_PATH} "${WIN_TMP}" PARENT_SCOPE)
  else()
    set(${WIN_PATH} "${LINUX_PATH}" PARENT_SCOPE)
  endif()
endfunction()

# ========================
# 收集源文件（相对路径）
# ========================
file(GLOB_RECURSE SOURCES LIST_DIRECTORIES false RELATIVE "${CMAKE_SOURCE_DIR}" "${CMAKE_SOURCE_DIR}/rtl/*.sv" "${CMAKE_SOURCE_DIR}/rtl/*.v")
file(GLOB_RECURSE TESTBENCH LIST_DIRECTORIES false RELATIVE "${CMAKE_SOURCE_DIR}" "${CMAKE_SOURCE_DIR}/tb/*.sv" "${CMAKE_SOURCE_DIR}/tb/*.v")

# 转为绝对路径（Linux/WSL 格式）
set(ABS_SOURCES "")
foreach(f IN LISTS SOURCES)
  list(APPEND ABS_SOURCES "${CMAKE_SOURCE_DIR}/${f}")
endforeach()

set(ABS_TESTBENCH "")
foreach(f IN LISTS TESTBENCH)
  list(APPEND ABS_TESTBENCH "${CMAKE_SOURCE_DIR}/${f}")
endforeach()

# ========================
# 板级配置
# ========================
if(BOARD STREQUAL "basys3")
  set(PART "xc7a35tcpg236-1")
  set(CONSTRAINTS "${CMAKE_SOURCE_DIR}/constraints/basys3.xdc")
elseif(BOARD STREQUAL "nexys_a7")
  set(PART "xc7a100tcsg324-1")
  set(CONSTRAINTS "${CMAKE_SOURCE_DIR}/constraints/nexys_a7.xdc")
else()
  message(FATAL_ERROR "不支持的开发板: ${BOARD}（请选择 basys3 或 nexys_a7）")
endif()

# ========================
# 转换为 Windows 路径（供 cmd.exe 使用）
# ========================
set(WINDOWS_SOURCES "")
foreach(f IN LISTS ABS_SOURCES)
  wsl_to_win_path("${f}" WIN_F)
  list(APPEND WINDOWS_SOURCES "${WIN_F}")
endforeach()

set(WINDOWS_TESTBENCH "")
foreach(f IN LISTS ABS_TESTBENCH)
  wsl_to_win_path("${f}" WIN_F)
  list(APPEND WINDOWS_TESTBENCH "${WIN_F}")
endforeach()

wsl_to_win_path("${CONSTRAINTS}" WINDOWS_CONSTRAINTS)
wsl_to_win_path("${CMAKE_SOURCE_DIR}" CMAKE_SOURCE_DIR_WIN)

# 仿真工作目录
set(SIM_WORK_DIR "${CMAKE_SOURCE_DIR}/tb/sim")
file(MAKE_DIRECTORY "${SIM_WORK_DIR}")  # 确保目录存在
wsl_to_win_path("${SIM_WORK_DIR}" SIM_WORK_DIR_WIN)

# 综合输出目录
set(SYNTH_DIR "${CMAKE_BINARY_DIR}/synth")
file(MAKE_DIRECTORY ${SYNTH_DIR})
wsl_to_win_path("${SYNTH_DIR}" SYNTH_DIR_WIN)

# Vivado 工具的 Windows 路径（关键！）
wsl_to_win_path("${VIVADO_PATH}" VIVADO_PATH_WIN)
wsl_to_win_path("${XSIM_DIR}" XSIM_DIR_WIN)

# ========================
# 将文件列表转为单个空格分隔字符串（关键！）
# ========================
string(REPLACE ";" " " WINDOWS_SOURCES_STR "${WINDOWS_SOURCES}")
string(REPLACE ";" " " WINDOWS_TESTBENCH_STR "${WINDOWS_TESTBENCH}")
set(ALL_SV_FILES_STR "${WINDOWS_SOURCES_STR} ${WINDOWS_TESTBENCH_STR}")

# ========================
# 仿真目标
# ========================
add_custom_target(simulate
  # 清理旧仿真数据
  COMMAND ${CMAKE_COMMAND} -E remove_directory "${SIM_WORK_DIR_WIN}/xsim.dir"
  COMMAND ${CMAKE_COMMAND} -E remove "${SIM_WORK_DIR_WIN}/sim1.wdb" "${SIM_WORK_DIR_WIN}/sim1.wcfg" "${SIM_WORK_DIR_WIN}/xsim.log"

  # 编译 SystemVerilog 文件
  COMMAND cmd.exe /c "cd /d ${SIM_WORK_DIR_WIN} && ${XSIM_DIR_WIN}/xvlog.bat --sv ${ALL_SV_FILES_STR}"
  VERBATIM

  # 生成仿真快照
  COMMAND cmd.exe /c "cd /d ${SIM_WORK_DIR_WIN} && ${XSIM_DIR_WIN}/xelab.bat tb_top -snapshot sim1 -debug all"
  VERBATIM

  # 运行仿真
  COMMAND cmd.exe /c "cd /d ${SIM_WORK_DIR_WIN} && ${XSIM_DIR_WIN}/xsim.bat sim1 -runall"
  VERBATIM

  COMMENT "▶️ 正在运行仿真..."
)

# ========================
# 比特流生成目标
# ========================
add_custom_target(bitstream
  COMMAND cmd.exe /c "${VIVADO_PATH_WIN}/bin/vivado.bat -mode batch -source ${CMAKE_SOURCE_DIR_WIN}/scripts/build_bitstream.tcl -tclargs example ${PART} ${CMAKE_SOURCE_DIR_WIN}/rtl ${WINDOWS_CONSTRAINTS} ${SYNTH_DIR_WIN}"
  WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
  VERBATIM
  COMMENT "⚙️ 正在生成比特流..."
)

# ========================
# 调试信息（可选）
# ========================
message(STATUS "Vivado (WSL):     ${VIVADO_PATH}")
message(STATUS "Vivado (Win):     ${VIVADO_PATH_WIN}")
message(STATUS "XSIM_DIR (Win):   ${XSIM_DIR_WIN}")
message(STATUS "Sim work dir:     ${SIM_WORK_DIR_WIN}")
