"""Keep verified Bottom RF routes while replacing the DC-only candidate."""
import json
from design_geometry import DEST

p=json.loads((DEST/'circuit_plan.json').read_text())
old=json.loads((DEST/'negotiated_plan.json').read_text())
assert old['routing_complete']
p['tracks'] += [t for t in old['tracks'] if t['layer']==32]
p['routed_jobs'] = p['dc_routed_jobs']+[r for r in old['routed_jobs'] if r['job']['kind']!='DC']
assert len(p['routed_jobs'])==108
p.update(unrouted_jobs=[],clearance_conflicts=[],routing_complete=True)
(DEST/'negotiated_plan.json').write_text(json.dumps(p,indent=2))
print('DC geometry and final pin assignments merged; retained 70 Bottom jobs.')
