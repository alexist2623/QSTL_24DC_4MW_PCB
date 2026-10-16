"""Prepare topology-aware left assignment and a private inline-safe router."""
from pathlib import Path
import json
from geodesic_rf_assignment import remap

HERE = Path(__file__).resolve().parent
plan = json.loads((HERE / 'dc_routed_candidate.json').read_text())
mapping = {2: 2, 5: 9, 9: 5, 11: 11, 12: 15, 13: 12, 15: 13,
           16: 16, 21: 21, 24: 28, 28: 24, 30: 30,
           31: 34, 32: 31, 34: 32, 35: 35}
candidate = remap(plan, mapping)
(HERE / 'placement_rf_ordered_assignment.json').write_text(json.dumps(candidate, indent=2))
previous = json.loads((HERE / 'rf_corner_repaired_candidate.json').read_text())
(HERE / 'rf_ordered_warm_snapshot.json').write_text(json.dumps({'routes': previous['rf_routed_jobs']}, indent=2))
source = (HERE / 'route_rf_rotated.py').read_text()
old = '''            live_forbidden=unary_union([forbidden[net]]+same_stems)
            live_hard=hard[net] | mask(unary_union(same_stems).buffer(REQUIRED+WIDTH/2+GUARD,quad_segs=12)) if same_stems else hard[net]'''
new = '''            # The QD-to-R path must not enter its own C2 terminal, which
            # would create a capacitor loop despite same-net DRC clearance.
            extra_keepouts=list(same_stems)
            if jobs[ix]['kind']=='RF_QD':
                extra_keepouts += [pgeom(p) for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('C') and p['pin']=='2' and p['net']==net]
            live_forbidden=unary_union([forbidden[net]]+extra_keepouts)
            live_hard=hard[net] | mask(unary_union(extra_keepouts).buffer(REQUIRED+WIDTH/2+GUARD,quad_segs=12)) if extra_keepouts else hard[net]'''
assert old in source
(HERE / 'route_rf_inline_safe.py').write_text(source.replace(old, new))
print('Prepared ordered assignment and private inline-safe router.')
