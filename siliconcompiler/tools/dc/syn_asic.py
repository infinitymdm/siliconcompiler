import os
import re
import shutil
from pathlib import Path

from siliconcompiler import Task
from siliconcompiler.asic import ASICTask
from siliconcompiler.tools.dc import DCTask


class ASICSynthesis(ASICTask, DCTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("dc_target_library", "file", "Synopsys .db target library")
        self.add_parameter("dc_driver_cell", "str", "Optional driving cell name")
        self.add_parameter("dc_driver_pin", "str", "Optional driving cell output pin")
        self.add_parameter("dc_load_pin", "str", "Optional library pin used for output load")
        self.add_parameter("dc_clock_period", "float", "Fallback clock period in ns")
        self.add_parameter("dc_clock_name", "str", "Fallback clock port name")
        self.add_parameter("dc_sdc", "file", "Optional SDC constraint file")
        self.set("var", "dc_clock_period", 20.0)
        self.set("var", "dc_clock_name", "clk")

    def task(self):
        return "syn_asic"

    def setup(self):
        super().setup()
        self.set_script("sc_synth_asic.tcl")

        design = self.project.design
        fileset = self.project.get("option", "fileset")[0]
        self.add_required_key(design, "fileset", fileset, "file", "verilog")

        self.set("output", f"{self.design_topmodule}.vg")
        self.add("output", f"{self.design_topmodule}.sdc")
        self.add("output", f"{self.design_topmodule}.sdf")
        self.add("output", f"{self.design_topmodule}.ddc")

    def _get_dc_target_library(self):
        manual_db = self.get("var", "dc_target_library")
        if manual_db:
            if not os.path.isfile(manual_db):
                raise RuntimeError(
                    "The configured Design Compiler target library "
                    f"does not exist: {manual_db}")
            return manual_db

        mainlib = self.project.get_library(self.project.get("asic", "mainlib"))

        library_db = mainlib.get("tool", "dc", "target_library")
        if library_db:
            if not os.path.isfile(library_db):
                raise RuntimeError(
                    "The main library defines a Design Compiler target "
                    f"library, but the file does not exist: {library_db}")
            return library_db

        raise RuntimeError(
            "No Design Compiler target library (.db) is configured. "
            "Define one in the main standard-cell library with "
            "set_dc_target_library(), or set the dc_target_library "
            "task parameter.")

    def pre_process(self):
        super().pre_process()

        design = self.project.design
        fileset = self.project.get("option", "fileset")[0]
        rtl_files = design.find_files("fileset", fileset, "file", "verilog")

        os.makedirs("inputs", exist_ok=True)

        copied_rtl = []
        for rtl in rtl_files:
            src = Path(rtl)
            dst = Path("inputs") / src.name
            shutil.copy2(src, dst)
            copied_rtl.append(str(dst))

        with open("inputs/sc_rtl_files.tcl", "w") as f:
            f.write("set sc_rtl_files {\n")
            for rtl in copied_rtl:
                f.write(f"    {rtl}\n")
            f.write("}\n")

        dc_target_library = self._get_dc_target_library()
        with open("inputs/sc_dc_setup.tcl", "w") as f:
            f.write(f"set sc_target_library {{{dc_target_library}}}\n")
            f.write(f"set sc_link_library \"* {dc_target_library}\"\n")
            clock_name, clock_period = self.get_clock()
            if clock_name is None:
                clock_name = self.get("var", "dc_clock_name")
            if clock_period is None:
                clock_period = self.get("var", "dc_clock_period")

            f.write(f"set sc_clock_name {{{clock_name}}}\n")
            f.write(f"set sc_clock_period {clock_period}\n")
            mainlib = self.project.get_library(self.project.get("asic", "mainlib"))
            dc_driver_cell = mainlib.get("tool", "dc", "driver_cell") or ""
            dc_driver_pin = mainlib.get("tool", "dc", "driver_pin") or ""
            dc_load_pin = mainlib.get("tool", "dc", "load_pin") or ""

            f.write(f"set sc_driver_cell {{{dc_driver_cell}}}\n")
            f.write(f"set sc_driver_pin {{{dc_driver_pin}}}\n")
            f.write(f"set sc_load_pin {{{dc_load_pin}}}\n")

    def post_process(self):
        super().post_process()

        area_rpt = f"reports/{self.design_topmodule}_area.rpt"
        timing_rpt = f"reports/{self.design_topmodule}_timing.rpt"
        power_rpt = f"reports/{self.design_topmodule}_power.rpt"

        if os.path.exists(area_rpt):
            with open(area_rpt) as f:
                for line in f:
                    m = re.search(r"Total cell area:\s+([0-9.]+)", line)
                    if m:
                        self.record_metric("cellarea", float(m.group(1)),
                                           source_file=area_rpt, source_unit="um^2")
                        break

        if os.path.exists(timing_rpt):
            with open(timing_rpt) as f:
                for line in f:
                    m = re.search(r"slack \(MET\)\s+([0-9.\-]+)", line)
                    if m:
                        self.record_metric("setupslack", float(m.group(1)),
                                           source_file=timing_rpt, source_unit="ns")
                        break

        if os.path.exists(power_rpt):
            with open(power_rpt) as f:
                for line in f:
                    if line.strip().startswith("Total") and "=" not in line and "W" in line:
                        vals = re.findall(r"([0-9.eE+\-]+)\s*([numk]?W)", line)
                        if vals:
                            self.record_metric("peakpower", float(vals[-1][0]),
                                               source_file=power_rpt, source_unit=vals[-1][1])
                            break

            with open(power_rpt) as f:
                text = f.read()

            m = re.search(r"Cell Leakage Power\s*=\s*([0-9.eE+\-]+)\s*([numk]?W)", text)
            if m:
                self.record_metric("leakagepower", float(m.group(1)),
                                   source_file=power_rpt, source_unit=m.group(2))
