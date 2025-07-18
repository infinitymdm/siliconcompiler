#!/usr/bin/env python3

import siliconcompiler

import os
import sys
from siliconcompiler.targets import skywater130_demo


def main():
    '''GCD example with custom floorplan and signoff steps.'''
    root = os.path.dirname(__file__)

    # Create instance of Chip class
    chip = siliconcompiler.Chip("gcd")

    chip.input(os.path.join(root, "gcd.v"))
    chip.set('option', 'quiet', True)

    chip.clock('clk', period=20)

    chip.use(skywater130_demo)

    chip.set('datasheet', 'pin', 'vdd', 'type', 'global', 'supply')
    chip.set('datasheet', 'pin', 'vss', 'type', 'global', 'ground')

    # 1) RTL2GDS

    # Disabled due to segfault in sky130
    # def_path = make_floorplan(chip)
    # chip.set('input', 'asic', 'floorplan.def', def_path)

    chip.set('option', 'jobname', 'rtl2gds')
    chip.run()
    chip.summary()

    gds_path = chip.find_result('gds', step='write.gds')
    vg_path = chip.find_result('vg', step='write.views')

    # 2) Signoff

    chip.set('option', 'jobname', 'signoff')
    chip.set('option', 'flow', 'signoffflow')

    chip.input(gds_path)
    chip.input(vg_path)

    chip.run()
    chip.summary()

    # 3) Checklist
    # Manual reports
    spec_path = os.path.join(os.path.dirname(__file__), 'spec.txt')
    chip.add('checklist', 'oh_tapeout', 'spec', 'report', spec_path)
    waiver_path = os.path.join(os.path.dirname(__file__), 'route_waiver.txt')

    chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'waiver', 'warnings', waiver_path)

    chip.set('checklist', 'oh_tapeout', 'drc_clean', 'task', ('signoff', 'drc', '0'))
    chip.set('checklist', 'oh_tapeout', 'lvs_clean', 'task', ('signoff', 'lvs', '0'))
    chip.set('checklist', 'oh_tapeout', 'setup_time', 'task', ('rtl2gds', 'write.views', '0'))

    for step in chip.getkeys('flowgraph', 'asicflow'):
        for index in chip.getkeys('flowgraph', 'asicflow', step):
            tool = chip.get('flowgraph', 'asicflow', step, index, 'tool')
            if tool != 'builtin':
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'task',
                         ('rtl2gds', step, index))
    for step in chip.getkeys('flowgraph', 'signoffflow'):
        for index in chip.getkeys('flowgraph', 'signoffflow', step):
            tool = chip.get('flowgraph', 'signoffflow', step, index, 'tool')
            if tool != 'builtin':
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'task',
                         ('signoff', step, index))

    status = chip.check_checklist('oh_tapeout', require_reports=False)
    if not status:
        return 1

    # Mark 'ok'
    for item in chip.getkeys('checklist', 'oh_tapeout'):
        chip.set('checklist', 'oh_tapeout', item, 'ok', True)

    status = chip.check_checklist('oh_tapeout', check_ok=True, require_reports=False)
    if not status:
        return 1

    chip.write_manifest('gcd.checked.pkg.json')

    return 0


if __name__ == '__main__':
    sys.exit(main())
