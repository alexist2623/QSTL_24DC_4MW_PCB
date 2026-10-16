from pathlib import Path
import json
h=Path(__file__).resolve().parent
before=json.loads((h/'through_dc_input.json').read_text())
after=json.loads((h/'through_dc_plan_passed.json').read_text())
assert len(after['vias'])==76
assert all(v['low']==1 and v['high']==32 for v in after['vias'])
assert [(v['label'],v['x'],v['y'],v['diameter'],v['hole']) for v in before['vias']]==[(v['label'],v['x'],v['y'],v['diameter'],v['hole']) for v in after['vias']]
assert before['components']==after['components']
old={r['qd_pad']:r['zif_pin'] for r in before['pinmap']}
changed=[{'qd':r['qd_pad'],'before':old[r['qd_pad']],'after':r['zif_pin']} for r in after['pinmap'] if old[r['qd_pad']]!=r['zif_pin']]
report=dict(validation=after['dc_routing_validation'],signal_vias=76,span=[1,32],via_geometry_preserved=True,component_placement_preserved=True,zif_pin50_unused=all(r['zif_pin']!=50 for r in after['pinmap']),changed_zif_pins=changed)
(h/'through_dc_summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
