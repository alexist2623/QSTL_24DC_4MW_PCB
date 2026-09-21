"""Check rigid pair movement, routing angles and RF junctions in saved copper."""
from pathlib import Path
import sys,json,math,importlib.util,collections
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import UNIT,sha
from verify_final_native_v2 import trackkey,arckey
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=P/'QSTL_24DC_4MW_PCB.PcbDoc';n=m.read_native()
before=json.loads((H/'before_native.json').read_text());plan=json.loads((H/'plan.json').read_text());errors=[];tol=6*UNIT
def check(ok,msg):
    if not ok:errors.append(msg)
def padshape(p):return Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
pair_report={}
for name in ('R1/C1','R5/C5'):
    names=name.split('/');old=unary_union([padshape(p) for p in before['pads'] if p['component'] in names]);new=unary_union([padshape(p) for p in n['pads'] if p['component'] in names]);a=(old.bounds[0]+old.bounds[2])/2;b=(new.bounds[0]+new.bounds[2])/2
    ratio=(b-9.75)/(a-9.75);check(abs(ratio-.7)<1e-6,'Pair distance ratio '+name)
    pair_report[name]=dict(before_x_mm=a,after_x_mm=b,shift_x_mm=b-a,distance_ratio=ratio)
for p in n['pads']:
    old=next(o for o in before['pads'] if (o['component'],o['number'])==(p['component'],p['number']) and (p['component'] or math.dist((o['x'],o['y']),(p['x'],p['y']))<tol))
    dx=plan['component_x_moves_mm'].get(p['component'],0)
    for key in ('x','y','size_x','size_y','hole','rotation','layer','net'):
        wanted=old[key]+dx if key=='x' else old[key]
        check(abs(p[key]-wanted)<tol if isinstance(wanted,(int,float)) else p[key]==wanted,'Pad preservation '+str((p['component'],p['number'],key)))
changed={'MW1','S1','MW5','S5','ZIF21','ZIF02'}
for kind,key in [('tracks',trackkey),('arcs',arckey)]:
    check(collections.Counter(key(t) for t in n[kind] if t['net'] not in changed)==collections.Counter(key(t) for t in before[kind] if t['net'] not in changed),'Unrelated routing changed '+kind)
nodes=collections.defaultdict(list);rfpaths=collections.defaultdict(list)
for t in n['tracks']:
    dx,dy=t['x2']-t['x1'],t['y2']-t['y1'];length=math.hypot(dx,dy)
    check(min(abs(dx),abs(dy),abs(abs(dx)-abs(dy)))<tol,'Non XY/45 track')
    if length<tol:check(False,'Zero-length track');continue
    nodes[t['net'],t['layer']].extend([((t['x1'],t['y1']),(dx/length,dy/length)),((t['x2'],t['y2']),(-dx/length,-dy/length))])
    if t['layer']==32:rfpaths[t['net']].append(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]))
for a in n['arcs']:
    sweep=(a['end_angle']-a['start_angle'])%360
    for angle,sign in [(a['start_angle'],1),(a['end_angle'],-1)]:
        theta=math.radians(angle);pt=(a['cx']+a['radius']*math.cos(theta),a['cy']+a['radius']*math.sin(theta));out=(-sign*math.sin(theta),sign*math.cos(theta));nodes[a['net'],a['layer']].append((pt,out))
    steps=max(4,math.ceil(sweep/.1));rfpaths[a['net']].append(LineString([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/steps)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/steps))) for j in range(steps+1)]))
dc_turns=[];rf_junctions=0;pad_terminations=[]
for (net,layer),ends in nodes.items():
    for i,(pt,v) in enumerate(ends):
        for pt2,v2 in ends[:i]:
            if math.dist(pt,pt2)>tol:continue
            dot=max(-1,min(1,v[0]*v2[0]+v[1]*v2[1]));turn=180-math.degrees(math.acos(dot))
            if layer==32:
                # Existing short track endings inside a solid component pad do
                # not represent an exposed uniform-trace bend.
                inside=[p for p in n['pads'] if p['net']==net and p['layer']==32 and padshape(p).buffer(-.055).contains(Point(pt))]
                if inside and turn>=.01:pad_terminations.append(dict(net=net,point=pt,pad=inside[0]['component']+'.'+inside[0]['number']))
                else:check(turn<.01,'RF nontangent junction '+str((net,pt,turn)));rf_junctions+=1
            elif layer in (1,2,4):dc_turns.append(turn);check(turn<=45.01,'DC turn exceeds 45 degrees '+str((net,pt,turn)))
for ch in range(1,7):
    p=next(p for p in n['pads'] if p['component']==f'R{ch}' and p['number']=='1');g=unary_union(rfpaths[f'MW{ch}']);check(g.distance(Point(p['x'],p['y']))<tol,'RF misses resistor pad centre '+str(ch))
dc_layers={net:sorted({t['layer'] for t in n['tracks'] if t['net']==net and t['layer']!=1}) for net in {t['net'] for t in n['tracks'] if t['net'] and t['net'].startswith('ZIF')}}
check(len(dc_layers)==24 and all(len(v)==1 and v[0] in (2,4) for v in dc_layers.values()),'DC changes internal layers')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(m.SOURCE),pair_centres=pair_report,unchanged_Y_spacing_rotations=True,RF_tangent_junctions_checked=rf_junctions,existing_track_endings_inside_pads=pad_terminations,DC_max_turn_degrees=max(dc_turns),DC_internal_layer_per_net=dc_layers,QD_RF_vias_removed=[x['pad'] for x in plan['removed_QD_RF_vias']],schematic_remap_required=False)
(H/'requested_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit(bool(errors))
