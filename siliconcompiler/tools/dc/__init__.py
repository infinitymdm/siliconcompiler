from siliconcompiler import Task
from siliconcompiler import StdCellLibrary



class DCStdCellLibrary(StdCellLibrary):
    def __init__(self):
        super().__init__()

        self.define_tool_parameter("dc", "target_library", "file",
                                   "Synopsys .db target library for Design Compiler.")
        self.define_tool_parameter("dc", "driver_cell", "str",
                                   "The driving cell name for Design Compiler.")
        self.define_tool_parameter("dc", "driver_pin", "str",
                                   "The output pin of the driving cell for Design Compiler.")
        self.define_tool_parameter("dc", "load_pin", "str",
                                   "The library pin used as output load for Design Compiler.")

    def set_dc_target_library(self, lib: str):
        self.set("tool", "dc", "target_library", lib)

    def set_dc_driver_cell(self, cell: str):
        self.set("tool", "dc", "driver_cell", cell)

    def set_dc_driver_pin(self, pin: str):
        self.set("tool", "dc", "driver_pin", pin)

    def set_dc_load_pin(self, pin: str):
        self.set("tool", "dc", "load_pin", pin)


class DCTask(Task):
    def tool(self):
        return "dc"

    def setup(self):
        super().setup()

        self.set_exe("dc_shell", vswitch="-version", format="tcl")
        self.add_commandline_option("-f")

        self.set_dataroot("siliconcompiler-dc", __file__)
        with self.active_dataroot("siliconcompiler-dc"):
            self.set_refdir("scripts")

        self.add_regex("errors", r"^Error:")
        self.add_regex("warnings", r"^Warning:")

    def parse_version(self, stdout):
        for line in stdout.splitlines():
            if "dc_shell version" in line:
                return line.split()[-1]
        return stdout.split()[-1]
