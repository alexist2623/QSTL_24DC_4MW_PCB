"""Give the upper corner QD terminal to the nearby resistor, preserving geometry."""
from pathlib import Path
import json
import hashlib
from geodesic_rf_assignment import remap

HERE = Path(__file__).resolve().parent
source = HERE / 'dc_routed_candidate.json'
plan = json.loads(source.read_text())
mapping = {2: 2, 5: 9, 9: 5, 11: 12, 12: 15, 13: 13, 15: 11,
           16: 16, 21: 21, 24: 28, 28: 24, 30: 30,
           31: 34, 32: 31, 34: 32, 35: 35}
candidate = remap(plan, mapping)
target = HERE / 'placement_rf_corner_assignment.json'
target.write_text(json.dumps(candidate, indent=2))
progress = json.loads((HERE / 'rf_right_swap_progress.json').read_text())
(HERE / 'rf_corner_warm_snapshot.json').write_text(json.dumps(progress, indent=2))
print(json.dumps({'mapping': mapping, 'candidate': str(target),
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                  'warm_iteration': progress['iteration']}, indent=2))
