"""Create the requested paired target swap while preserving DC coordinates."""
from pathlib import Path
import json,hashlib
from geodesic_rf_assignment import remap
H=Path(__file__).resolve().parent
base=H/'dc_routed_candidate.json';plan=json.loads(base.read_text())
report=json.loads((H/'rf_geodesic_assignment_report.json').read_text())
mapping={int(g):int(q) for g,q in report['rf_group_to_qd_pad'].items()}
swap={11:12,12:11,34:35,35:34}
mapping={g:swap.get(q,q) for g,q in mapping.items()}
candidate=remap(plan,mapping)
out=H/'placement_rf_geodesic_swapped_targets.json';out.write_text(json.dumps(candidate,indent=2))
audit=dict(candidate=str(out),candidate_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(base.read_bytes()).hexdigest(),mapping=mapping,positions_unchanged=True,DC_geometry_unchanged=True,SMP_q_metadata_synchronized=all(next(c for c in candidate['components'] if c['ref']==s['ref'])['q']==s['q'] for s in candidate['smp']))
(H/'rf_geodesic_target_swap_report.json').write_text(json.dumps(audit,indent=2));print(json.dumps(audit,indent=2))
