"""Prepare local RF target cycles to untangle ring-protected paths."""
from pathlib import Path
import json
from geodesic_rf_assignment import remap

HERE = Path(__file__).resolve().parent
plan = json.loads((HERE / 'dc_routed_candidate.json').read_text())
base = {2: 2, 5: 9, 9: 5, 11: 12, 12: 15, 13: 11, 15: 13,
        16: 16, 21: 21, 24: 28, 28: 24, 30: 30,
        31: 34, 32: 31, 34: 32, 35: 35}
for suffix, cycle in [('a', {30: 31, 32: 32, 34: 30}),
                      ('b', {30: 32, 32: 30, 34: 31})]:
    mapping = dict(base, **{})
    mapping.update(cycle)
    candidate = remap(plan, mapping)
    (HERE / f'placement_rf_ring_cycle_{suffix}.json').write_text(json.dumps(candidate, indent=2))
warm = json.loads((HERE / 'rf_ring_clear_progress.json').read_text())
(HERE / 'rf_ring_cycle_warm_snapshot.json').write_text(json.dumps(warm, indent=2))
print('Prepared cycle A/B, warm iteration', warm['iteration'])
