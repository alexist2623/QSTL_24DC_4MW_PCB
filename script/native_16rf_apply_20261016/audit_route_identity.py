"""Check every saved route against the accepted native candidate, after cleanup."""
from pathlib import Path
import sys,json,math,collections
import numpy as np
from shapely.geometry import LineString
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];D=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
p=json.loads((H/'candidate.json').read_text());s=json.loads((D/'schematic_validation.json').read_text())
pads,regions,tracks,vias,outline=read_snapshot(D/'QSTL_QD4_2SET_38PAD.PcbDoc',s)
want=collections.defaultdict(list);got=collections.defaultdict(list);issues=[]
for t in p['tracks']:want[(t['net'],t['layer'])].append(LineString([t['a'],t['b']]))
for a in p['arcs']:
    sweep=(a['end_angle']-a['start_angle'])%360 or 360;r=a['radius'];step=2*math.acos(max(-1,1-0.00004/r));n=max(3,math.ceil(math.radians(sweep)/step));ang=np.deg2rad(np.linspace(a['start_angle'],a['start_angle']+sweep,n+1))
    want[(a['net'],a['layer'])].append(LineString(np.c_[a['cx']+r*np.cos(ang),a['cy']+r*np.sin(ang)]))
for t in tracks:
    if t['net'] and t['layer'] in (1,2,3,4,5,32):got[(t['net'],t['layer'])].append(t['geometry'])
    if t['net'] and t['net'].startswith('DC') and t['layer'] in (2,3):
        a,b=list(t['geometry'].coords)[::len(t['geometry'].coords)-1];dx=abs(a[0]-b[0]);dy=abs(a[1]-b[1]);
        if min(dx,dy,abs(dx-dy))>1e-5 or abs(t['width']-.125)>1e-5:issues.append(['DC_angle_or_width',t['net'],dx,dy,t['width']])
    if t['net'] and t['net'].startswith(('MW','S')) and abs(t['width']-.11)>1e-5:issues.append(['RF_width',t['net'],t['width']])
if set(want)!=set(got):issues.append(['route_net_layer_set',list(set(want)^set(got))])
rows=[]
for k,gg in want.items():
    distance=unary_union(gg).hausdorff_distance(unary_union(got.get(k,[])));rows.append(dict(net=k[0],layer=k[1],hausdorff_mm=distance))
    if distance>.00013:issues.append(['route_diff',k,distance])
report=dict(passed=not issues,issues=issues,max_route_centreline_difference_mm=max(r['hausdorff_mm'] for r in rows),arcs_tessellation_bound_mm=.00010,rows=rows)
(H/'route_identity_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
