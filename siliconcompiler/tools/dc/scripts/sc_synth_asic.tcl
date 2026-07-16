source ./sc_manifest.tcl

source inputs/sc_dc_setup.tcl

file mkdir outputs
file mkdir reports
file mkdir WORK

set target_library [list $sc_target_library]
set link_library "* $target_library"

define_design_lib WORK -path ./WORK

source inputs/sc_rtl_files.tcl

foreach rtl $sc_rtl_files {
    puts "Reading RTL file: $rtl"
    analyze -format sverilog -lib WORK $rtl
}

elaborate $sc_topmodule -lib WORK
current_design $sc_topmodule
link

if {[file exists inputs/sc_constraints.sdc]} {
    puts "Reading user SDC: inputs/sc_constraints.sdc"
    source inputs/sc_constraints.sdc
} else {
    puts "No SDC found. Creating fallback clock."
    create_clock -period $sc_clock_period [get_ports $sc_clock_name]
    set_input_delay 0.0 -max -clock $sc_clock_name [remove_from_collection [all_inputs] [get_ports $sc_clock_name]]
    set_output_delay 0.0 -max -clock $sc_clock_name [all_outputs]
}

set all_inputs_except_clk [remove_from_collection [all_inputs] [get_ports $sc_clock_name]]

if {[string length $sc_driver_cell] > 0 && [string length $sc_driver_pin] > 0} {
    puts "Applying driving cell: $sc_driver_cell / $sc_driver_pin"
    if {[sizeof_collection $all_inputs_except_clk] > 0} {
        set_driving_cell -lib_cell $sc_driver_cell -pin $sc_driver_pin $all_inputs_except_clk
    }
} else {
    puts "No driving cell specified. Skipping set_driving_cell."
}

if {[string length $sc_load_pin] > 0} {
    puts "Applying output load from: $sc_load_pin"
    set_load [expr [load_of $sc_load_pin] * 1] [all_outputs]
} else {
    puts "No load pin specified. Skipping set_load."
}

check_design > reports/check_design.rpt

compile_ultra

write_file -format verilog -hierarchy -output outputs/${sc_topmodule}.vg
write_sdc outputs/${sc_topmodule}.sdc
write_sdf outputs/${sc_topmodule}.sdf
write_file -format ddc -hierarchy -output outputs/${sc_topmodule}.ddc

redirect reports/${sc_topmodule}_timing.rpt { report_timing -capacitance -transition_time -nets -nworst 10 }
redirect reports/${sc_topmodule}_area.rpt { report_area -hierarchy -nosplit -physical -designware }
redirect reports/${sc_topmodule}_power.rpt { report_power }
redirect reports/${sc_topmodule}_cell.rpt { report_cell [get_cells -hier *] }

quit
