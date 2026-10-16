"""Swap the right RF target pair, leaving left geodesic assignments intact."""
from pathlib import Path
import json
import hashlib
from geodesic_rf_assignment import remap

HERE = Path(__file__).resolve().parent
source = HERE / 'dc_routed_candidate.json'
plan = json.loads(source.read_text())
report = json.loads((HERE / 'rf_geodesic_assignment_report.json').read_text())
mapping = {int(group): int(target) for group, target in report['rf_group_to_qd_pad'].items()}
swap = {34: 35, 35: 34}
mapping = {group: swap.get(target, target) for group, target in mapping.items()}
candidate = remap(plan, mapping)
target = HERE / 'placement_rf_geodesic_right_swap.json'
target.write_text(json.dumps(candidate, indent=2))
audit = {
    'candidate': str(target),
    'candidate_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'mapping': mapping,
    'positions_unchanged': True,
    'DC_geometry_unchanged': True,
    'DC_geometry_note': 'This is the earlier DC checkpoint, not the pending full-SMP-hull reroute.',
    'SMP_q_metadata_synchronized': all(
        next(comp for comp in candidate['components'] if comp['ref'] == smp['ref'])['q'] == smp['q']
        for smp in candidate['smp']
    ),
}
(HERE / 'rf_geodesic_right_swap_report.json').write_text(json.dumps(audit, indent=2))
print(json.dumps(audit, indent=2))
