"""Check the geometric plan independently; this is not a saved-board signoff."""
from pathlib import Path
import json,sys,math,collections,struct
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.affinity import rotate,translate
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
from native_metadata_helpers import binary_records,UNIT
n=json.loads((H/'planned_native.json').read_text());p=json.loads((H/'plan.json').read_text());errors=[]
def padshape(pad):
    if pad['shape']==1:return Point(pad['x'],pad['y']).buffer(pad['size_x']/2,quad_segs=64)
    return translate(rotate(box(-pad['size_x']/2,-pad['size_y']/2,pad['size_x']/2,pad['size_y']/2),pad['rotation'],origin=(0,0)),pad['x'],pad['y'])
cap_xy={(round(t['x']/UNIT),round(t['y']/UNIT)) for t in n['pads'] if t['component'] and t['component'].startswith('C')}
n['vias']=[v for v in n['vias'] if (round(v['x']/UNIT),round(v['y']/UNIT)) not in cap_xy]
for v in p['shield_vias']:n['vias'].append(v)
primitives=[]
for pad in n['pads']:primitives.append((f"{pad['component']}.{pad['number']}",pad['net'],{1,2,3,4,5,32} if pad['layer']==74 else {pad['layer']},padshape(pad)))
for i,v in enumerate(n['vias']):primitives.append((f'via{i}',v['net'],{5,32} if v['net']=='GND' else {1,2,3,4,5,32},Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)))
for i,t in enumerate(n['tracks']):
    dx,dy=abs(t['x2']-t['x1']),abs(t['y2']-t['y1'])
    if min(dx,dy,abs(dx-dy))>6*UNIT:errors.append(f'Non-45-degree track {i}')
    primitives.append((f'track{i}',t['net'],{t['layer']},LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2,quad_segs=32)))
for i,a in enumerate(n['arcs']):
    sweep=(a['end_angle']-a['start_angle'])%360;num=math.ceil(sweep/.1)
    path=LineString([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/num)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/num))) for j in range(num+1)])
    primitives.append((f'arc{i}',a['net'],{a['layer']},path.buffer(a['width']/2,quad_segs=32)))
minimum=1e9;near=[]
for i,(label,net,layers,g) in enumerate(primitives):
    for label2,net2,layers2,g2 in primitives[:i]:
        if net==net2 and net:continue
        shared=layers&layers2
        if not shared:continue
        gap=g.distance(g2);required=.2 if 'GND' in (net,net2) and 32 in shared else .15
        minimum=min(minimum,gap)
        if gap<required-6*UNIT:near.append(dict(a=label,b=label2,gap_mm=gap,required_mm=required))
qd=[padshape(t) for t in n['pads'] if t['component']=='Q1'];cavity=shape(p['cavity']['geometry'])
cavity_gap=min(g.distance(cavity) for g in qd)
if cavity_gap<.2-5*UNIT:errors.append('Cavity pad clearance below 0.2 mm')
if near:errors.append(f'{len(near)} planned copper clearance conflicts')
s=snapshot(H/'before.PcbDoc');mechanical={}
for stream,kind in [('Tracks6/Data',4),('Arcs6/Data',1),('Fills6/Data',6),('Texts6/Data',5)]:
    if stream=='Texts6/Data':continue
    mechanical[stream]=dict(collections.Counter(row['body'][0] for row in binary_records(s[stream],kind) if 57<=row['body'][0]<=72))
report=dict(passed=not errors,errors=errors,planned_capacitor_vias_removed=12,planned_vias=len(n['vias']),planned_shield_vias=len(p['shield_vias']),cavity_pad_gap_mm=cavity_gap,minimum_different_net_gap_mm=minimum,clearance_conflicts=near,existing_mechanical_objects=mechanical,not_saved_board_validation=True)
(H/'plan_preflight.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
for index in (66,239):
    net=n['tracks'][index]['net'];print('INVESTIGATE',index,net)
    for i,t in enumerate(n['tracks']):
        if t['net']==net:print(i,t)
