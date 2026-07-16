from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.tools.dc import syn_asic as dc_syn_asic


class DCASICFlow(ASICFlow):
    """Experimental ASIC flow using Design Compiler and OpenROAD.

    This flow inherits the standard SiliconCompiler ASICFlow, removes
    the separate Slang elaboration step, and replaces Yosys synthesis
    with Synopsys Design Compiler. All OpenROAD physical-design stages
    remain unchanged.
    """

    def __init__(self, name: str = "dcasicflow"):
        # Keep all parallelism at one while validating the integration.
        super().__init__(
            name=name,
            syn_np=1,
            floorplan_np=1,
            place_np=1,
            cts_np=1,
            route_np=1
        )

        # Design Compiler reads and elaborates RTL internally.
        self.remove_node("elaborate")

        # Remove the Yosys synthesis node.
        self.remove_node("synthesis")

        # Insert the Design Compiler synthesis task.
        self.node(
            "synthesis",
            dc_syn_asic.ASICSynthesis(),
            index=0
        )

        # Connect DC output directly to the standard OpenROAD flow.
        self.edge(
            "synthesis",
            "floorplan.init",
            tail_index=0,
            head_index=0
        )

        self.get_graph_node("synthesis", 0).add_goal("errors", 0)


##################################################
if __name__ == "__main__":
    flow = DCASICFlow()
    flow.write_flowgraph(f"{flow.name}.png")
