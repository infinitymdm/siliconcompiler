from siliconcompiler.tools.dc import syn_asic
from siliconcompiler.tools.builtin import minimum
from siliconcompiler import Flowgraph


class DCSynthesisFlow(Flowgraph):
    '''
    A configurable ASIC synthesis flow based on Synopsys Design Compiler.

    This flow translates RTL designs into a gate-level netlist using
    Synopsys Design Compiler (dc_shell). Unlike the Yosys-based
    SynthesisFlow, no separate elaboration step is required because
    Design Compiler performs analyze/elaborate internally.

    The flow consists of the following steps:

        * **synthesis**: Translates RTL into a gate-level netlist
                         using Synopsys Design Compiler.

    The class is designed to be extensible: a timing (STA) step can be
    added later without changing the public API.
    '''

    def __init__(self, name: str = "dc_synflow", syn_np: int = 1):
        """
        Initializes the DCSynthesisFlow.

        Args:
            * name (str): The name of the flow.
            * syn_np (int): The number of parallel synthesis jobs to launch.
                If greater than 1, a 'minimum' step is added to select the
                best result.
        """
        super().__init__()
        self.set_name(name)

        if syn_np > 1:
            self.node("synmin", minimum.MinimumTask())

        for n in range(syn_np):
            self.node("synthesis", syn_asic.ASICSynthesis(), index=n)
            if syn_np > 1:
                self.edge("synthesis", "synmin", tail_index=n)
            for metric in ('errors',):
                self.get_graph_node("synthesis", n).add_goal(metric, 0)

    @classmethod
    def make_docs(cls):
        return DCSynthesisFlow(syn_np=3)


##################################################
if __name__ == "__main__":
    flow = DCSynthesisFlow(syn_np=3)
    flow.write_flowgraph(f"{flow.name}.png")
