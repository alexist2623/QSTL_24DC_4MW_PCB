"""Stage a synchronized schematic and canonical QD library for the 90-degree board.

This never overwrites the working project. The native PCB component is rotated
90 degrees, so the footprint library retains unrotated local coordinates.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = HERE.parent / 'qd38_carrier_20261010'
PROJECT = ROOT / 'QSTL_QD4_2SET_38PAD'
NAME = 'QSTL_QD4_2SET_38PAD'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.candidate.read_text())
    q1 = next(c for c in plan['components'] if c['ref'] == 'Q1')
    assert abs(q1['rotation'] - 90) < 1e-8
    dest = HERE / 'schematic_staging'
    dest.mkdir(exist_ok=True)
    (dest / 'circuit_plan.json').write_text(json.dumps(plan, indent=2))
    shutil.copy2(PROJECT / (NAME + '.PrjPcb'), dest / (NAME + '.PrjPcb'))
    shutil.copy2(OLD / 'baseline_schematic_records.json', HERE / 'baseline_schematic_records.json')
    spec = importlib.util.spec_from_file_location('qd38_schematic_base', OLD / 'build_schematic.py')
    module = importlib.util.module_from_spec(spec)
    source = (OLD / 'build_schematic.py').read_text()
    old_caption = 'Text=f"RF + DC: Q1-{n} / {plan[\'pads\'][n-1][\'net\']}"'
    new_caption = 'Text=f"RF + DC: Q1-{next(s[\'q\'] for s in plan[\'smp\'] if s[\'ref\']==f\'SMP{n:02}\')} / {plan[\'pads\'][next(s[\'q\'] for s in plan[\'smp\'] if s[\'ref\']==f\'SMP{n:02}\')-1][\'net\']}"'
    assert source.count(old_caption) == 1
    source = source.replace(old_caption, new_caption)
    exec(compile(source, str(OLD / 'build_schematic.py'), 'exec'), module.__dict__)
    module.H = HERE
    module.DEST = dest
    original_libraries = module.libraries

    def canonical_libraries(actual):
        canonical = copy.deepcopy(actual)
        for pad in canonical['pads']:
            x, y = pad['center']
            pad['center'] = [y, -x]
            pad['rotation'] = (pad['rotation'] - 90) % 360
        original_libraries(canonical)

    module.libraries = canonical_libraries
    module.main()


if __name__ == '__main__':
    main()
