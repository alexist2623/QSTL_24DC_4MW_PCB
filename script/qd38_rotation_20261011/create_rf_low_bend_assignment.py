"""Resolve the remaining left detour by ordering the two nearby RF targets."""
from pathlib import Path
import json
import hashlib
from geodesic_rf_assignment import remap

HERE = Path(__file__).resolve().parent
source = HERE / 'dc_routed_candidate.json'
plan = json.loads(source.read_text())
mapping = {2: 2, 5: 9, 9: 5, 11: 11, 12: 15, 13: 13, 15: 12,
           16: 16, 21: 21, 24: 28, 28: 24, 30: 30,
           31: 34, 32: 31, 34: 32, 35: 35}
candidate = remap(plan, mapping)
target = HERE / 'placement_rf_low_bend_assignment.json'
target.write_text(json.dumps(candidate, indent=2))
previous = json.loads((HERE / 'rf_corner_repaired_candidate.json').read_text())
(HERE / 'rf_low_bend_warm_snapshot.json').write_text(json.dumps({'routes': previous['rf_routed_jobs']}, indent=2))
print(json.dumps({'mapping': mapping, 'candidate': str(target),
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}, indent=2))
