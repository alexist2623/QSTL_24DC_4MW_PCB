"""Adopt independently checked through-via DC routes, preserving RF routes."""
from pathlib import Path
import csv
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT/'QSTL_QD4_2SET_38PAD'
p = json.loads((H/'through_dc_plan_passed.json').read_text())
summary = json.loads((H/'through_dc_summary.json').read_text())
assert p['dc_routing_validation']['routes'] == 38
assert p['dc_routing_validation']['crossings'] == 0
assert p['dc_routing_validation']['minimum_clearance_mm'] >= .15
assert all(v['low']==1 and v['high']==32 for v in p['vias'])
backup=H/'before_through_correction'
backup.mkdir(exist_ok=True)
for name in ['circuit_plan.json','negotiated_plan.json','full_copper_candidate.json',
             'pin_mapping.csv','QSTL_QD4_2SET_38PAD.SchDoc','schematic_validation.json']:
    target=backup/name
    assert not target.exists(), 'Do not replace the pre-correction backup'
    shutil.copy2(DEST/name,target)
for v in p['vias']:
    q=int(v['net'][2:])
    v['routing_layer']=p['dc_endpoints'][str(q)]['layer']
(DEST/'circuit_plan.json').write_text(json.dumps(p,indent=2))
with (DEST/'pin_mapping.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(p['pinmap'][0]));w.writeheader();w.writerows(p['pinmap'])
print('Adopted full-through DC plan; RF merge and native validation remain pending.')
