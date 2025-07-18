# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
from siliconcompiler import NodeStatus

import pytest

from siliconcompiler.tools.openroad import global_placement
from siliconcompiler.tools.openroad import clock_tree_synthesis

from siliconcompiler.tools.builtin import nop
from siliconcompiler.tools.builtin import minimum
from siliconcompiler.flowgraph import RuntimeFlowgraph


@pytest.fixture
def gcd_with_metrics(gcd_chip):
    runtime = RuntimeFlowgraph(
        gcd_chip.schema.get("flowgraph", gcd_chip.get('option', 'flow'), field='schema'),
        from_steps=gcd_chip.get('option', 'from'),
        to_steps=gcd_chip.get('option', 'to'),
        prune_nodes=gcd_chip.get('option', 'prune'))

    steps = runtime.get_nodes()

    dummy_data = 0
    flow = gcd_chip.get('option', 'flow')
    for step in gcd_chip.getkeys('flowgraph', flow):
        dummy_data += 1
        for index in gcd_chip.getkeys('flowgraph', flow, step):
            for metric in gcd_chip.getkeys('metric'):
                gcd_chip.set('record', 'status', NodeStatus.SUCCESS, step=step, index=index)
                gcd_chip.set('metric', metric, str(dummy_data), step=step, index=index)
                for inputs in gcd_chip.get('flowgraph', flow, step, index, 'input'):
                    if inputs in steps:
                        gcd_chip.add('record', 'inputnode', inputs, step=step, index=index)

    return gcd_chip


def test_summary(gcd_with_metrics):
    gcd_with_metrics.summary()


def test_from_to(gcd_with_metrics, capfd):
    with capfd.disabled():
        gcd_with_metrics.set('option', 'from', ['syn'])
        gcd_with_metrics.set('option', 'to', ['syn'])

    gcd_with_metrics.summary()
    stdout, _ = capfd.readouterr()
    # Summary output is hidden by capfd, so we print it to aid in debugging
    print(stdout)

    assert 'import.veri...0' in stdout
    assert 'import.conv...0' in stdout
    assert 'import.chisel/0' in stdout
    assert 'import.c/0' in stdout
    assert 'import.blue...0' in stdout
    assert 'import.vhdl/0' in stdout
    assert 'syn/0' in stdout
    assert 'floorplan' not in stdout


def test_parallel_path(capfd):
    with capfd.disabled():
        chip = siliconcompiler.Chip('test')

        flow = 'test'
        chip.set('option', 'flow', flow)
        chip.node(flow, 'import', nop)
        chip.node(flow, 'ctsmin', minimum)

        chip.set('record', 'status', NodeStatus.SUCCESS, step='import', index='0')
        chip.set('record', 'status', NodeStatus.SUCCESS, step='ctsmin', index='0')
        chip.set('record', 'inputnode', ('cts', '1'), step='ctsmin', index='0')

        for i in ('0', '1', '2'):
            chip.node(flow, 'place', global_placement, index=i)
            chip.node(flow, 'cts', clock_tree_synthesis, index=i)

            chip.set('record', 'status', NodeStatus.SUCCESS, step='place', index=i)
            chip.set('record', 'status', NodeStatus.SUCCESS, step='cts', index=i)

            chip.edge(flow, 'place', 'cts', tail_index=i, head_index=i)
            chip.edge(flow, 'cts', 'ctsmin', tail_index=i)
            chip.edge(flow, 'import', 'place', head_index=i)

            chip.set('record', 'inputnode', ('import', '0'), step='place', index=i)
            chip.set('record', 'inputnode', ('place', i), step='cts', index=i)

            chip.set('metric', 'errors', 0, step='place', index=i)
            chip.set('metric', 'errors', 0, step='cts', index=i)

    chip.write_flowgraph('test_graph.png')

    chip.summary()
    stdout, _ = capfd.readouterr()
    # Summary output is hidden by capfd, so we print it to aid in debugging
    print(stdout)
    assert 'place/1' in stdout
    assert 'cts/1' in stdout
    assert 'place/0' not in stdout
    assert 'cts/0' not in stdout
    assert 'place/2' not in stdout
    assert 'cts/2' not in stdout
