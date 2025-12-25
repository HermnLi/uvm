if {$argc < 5} {
    error "用法: build_bitstream.tcl <proj_name> <part> <rtl_dir> <xdc_file> <proj_dir>"
}

set proj_name [lindex $argv 0]
set part [lindex $argv 1]
set rtl_dir [lindex $argv 2]
set xdc_file [lindex $argv 3]
set proj_dir [lindex $argv 4]

create_project $proj_name $proj_dir -part $part

proc add_rtl_files {dir} {
    foreach f [glob -nocomplain -directory $dir *] {
        if {[file isdirectory $f]} {
            add_rtl_files $f
        } elseif {[string match -nocase "*.v" $f] || [string match -nocase "*.sv" $f]} {
            add_files -norecurse $f
        }
    }
}

add_rtl_files $rtl_dir

if {$xdc_file != "" && [file exists $xdc_file]} {
    add_files -fileset constrs_1 -norecurse $xdc_file
}

set_property top add3_top [current_fileset]

launch_runs synth_1 -jobs 4
wait_on_run synth_1
launch_runs impl_1 -jobs 4
wait_on_run impl_1

write_bitstream -force ${proj_dir}/${proj_name}.bit
puts "✅ 比特流已生成: ${proj_dir}/${proj_name}.bit"
