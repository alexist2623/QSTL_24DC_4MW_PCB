"""Increase twelve capacitor-to-resistor body gaps without changing DC routing."""
from pathlib import Path
import copy,hashlib,json,math
H=Path(__file__).resolve().parent;DEST=H.parents[1]/'QSTL_QD4_2SET_38PAD'
MOVES={f'C{n:02}':.10 for n in [2,5,11,12,15,16]}|{f'C{n:02}':-.10 for n in [21,24,30,31,34,35]}
BACKUP=H/'through_dc_before_cap_gap_repair';BACKUP.mkdir(exist_ok=True)
report=[]
for name in ['circuit_plan.json','negotiated_plan.json']:
 path=DEST/name;data=path.read_bytes();backup=BACKUP/name
 if backup.exists():assert backup.read_bytes()==data,'Do not reapply the movement to an already changed plan'
 else:backup.write_bytes(data)
 before=json.loads(data);p=copy.deepcopy(before)
 oldpads=[d for d in before['physical_pads'] if d['ref'] in MOVES]
 for c in p['components']:
  if c['ref'] in MOVES:c['y']+=MOVES[c['ref']]
 for d in p['physical_pads']:
  if d['ref'] in MOVES:d['y']+=MOVES[d['ref']]
 def change_point(pt,net,limit):
  matches=[d for d in oldpads if d['net']==net and math.dist(pt,[d['x'],d['y']])<limit]
  if matches:
   assert len(matches)==1
   pt[1]+=MOVES[matches[0]['ref']]
   return 1
  return 0
 changed_tracks=0
 for t in p['tracks']:
  if t['layer']==32:
   changed_tracks+=change_point(t['a'],t['net'],.018)
   changed_tracks+=change_point(t['b'],t['net'],.018)
 for j in p['route_jobs']:
  if j['layer']==32:
   for key in ['a','b']:change_point(j[key],j['net'],1e-6)
 for r in p.get('routed_jobs',[]):
  j=r['job']
  if j['layer']==32:
   for key in ['a','b']:change_point(j[key],j['net'],1e-6)
   for pt in r['points']:change_point(pt,j['net'],.018)
 for before_t,t in zip(before['tracks'],p['tracks']):
  if before_t!=t:
   dx=abs(t['a'][0]-t['b'][0]);dy=abs(t['a'][1]-t['b'][1])
   assert min(dx,dy)<1e-8 or abs(dx-dy)<1e-8,'Moved RF segment lost orthogonal/45-degree routing'
   assert t['width']==.11 and t['layer']==32
 assert before['vias']==p['vias'] and before['pinmap']==p['pinmap'] and before['nets']==p['nets']
 assert [t for t in before['tracks'] if t['layer']!=32]==[t for t in p['tracks'] if t['layer']!=32]
 assert [c for c in before['components'] if c['ref'] not in MOVES]==[c for c in p['components'] if c['ref'] not in MOVES]
 p['capacitor_body_gap_repair']=dict(moved_components=MOVES,nominal_minimum_cr_body_gap_mm=.27,resistor_and_dc_geometry_unchanged=True)
 path.write_text(json.dumps(p,indent=2))
 report.append(dict(file=name,before_sha256=hashlib.sha256(data).hexdigest(),after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),moved_caps=12,moved_pads=len(oldpads),modified_rf_track_endpoints=changed_tracks))
(H/'through_dc_cap_gap_repair.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
