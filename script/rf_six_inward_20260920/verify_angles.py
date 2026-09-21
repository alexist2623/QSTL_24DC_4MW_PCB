from pathlib import Path
import sys,json,math,collections,hashlib
H=Path(__file__).resolve().parent;W=H.parent/'_support'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board'),str(W/'route_python')]
from native_metadata_helpers import properties,pads_stream,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB';D=P/'docs'
s=snapshot(P/(B+'.PcbDoc'));cs=properties(s['Components6/Data']);ns=properties(s['Nets6/Data']);ps=pads_stream(s['Pads6/Data']);ts,ars,vs=read_route(s,ns);errors=[]
def angle(a,b):return math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%360
def delta(a,b):return abs((a-b+180)%360-180)
off=[]
for i,t in enumerate(ts):
 a=angle((t['x1'],t['y1']),(t['x2'],t['y2']));err=abs((a+22.5)%45-22.5)
 if err>.02:off.append(dict(index=i,net=t['net'],layer=t['layer'],angle=a,error=err))
if off:errors.append('Straight traces violate 0/45/90/135-degree directions')
def key(x,y):return round(x/UNIT),round(y/UNIT)
joints=collections.defaultdict(list)
for i,t in enumerate(ts):
 if t['layer'] not in [2,4]:continue
 a,b=(t['x1'],t['y1']),(t['x2'],t['y2'])
 joints[(t['net'],)+key(*a)].append(angle(a,b));joints[(t['net'],)+key(*b)].append(angle(b,a))
sharp=[];turns=[]
for (n,x,y),head in joints.items():
 if len(head)!=2:continue
 turn=180-delta(*head);turns.append(turn)
 if turn>45.02:sharp.append(dict(net=n,x=x*UNIT,y=y*UNIT,turn_deg=turn))
if sharp:errors.append('DC has direction changes greater than 45 degrees')
# All native RF track/arc junctions must be tangent. Pad-centred branch junctions are explicit exceptions.
rfends=[]
for i,t in enumerate(ts):
 if t['layer']!=32:continue
 a,b=(t['x1'],t['y1']),(t['x2'],t['y2'])
 rfends.extend([(t['net'],a,angle(a,b),'track',i),(t['net'],b,angle(b,a),'track',i)])
for i,a in enumerate(ars):
 for end,sign in [('start_angle',1),('end_angle',-1)]:
  rad=math.radians(a[end]);pt=(a['cx']+a['radius']*math.cos(rad),a['cy']+a['radius']*math.sin(rad))
  rfends.append((a['net'],pt,(a[end]+sign*90)%360,'arc',i))
padpoints=[(ps0['coords'][0]*UNIT,ps0['coords'][1]*UNIT) for ps0 in ps]+[(v['x'],v['y']) for v in vs]
kinks=[];junctions=[]
for i,a in enumerate(rfends):
 for b in rfends[:i]:
  if a[0]!=b[0] or math.dist(a[1],b[1])>8*UNIT:continue
  if any(math.dist(a[1],p)<8*UNIT for p in padpoints):continue
  err=abs(180-delta(a[2],b[2]));junctions.append(err)
  if err>.03:kinks.append(dict(net=a[0],xy=a[1],kink=err,kinds=[a[3],b[3]]))
if kinks:errors.append('RF contains non-tangent corners')
refp=W/'reference_placement/placements.json';ref=json.loads(refp.read_text());refpath=Path(ref['source']);refsha=sha(refpath)
if refsha!=ref['source_sha256']:errors.append('Readonly reference hash changed')
sample=next(c for c in ref['components'] if c['designator']=='Sample');current={int(p['number']):p for p in ps if p['component']!=65535 and cs[p['component']]['SOURCEDESIGNATOR']=='Q1'}
g=json.loads((H/'geometry.json').read_text());cx,cy=g['qd_component_center'];mapping=[]
def bearing(xy):return math.degrees(math.atan2(xy[0]-cx,xy[1]-cy))%360
for ch,pin in g['rf_qd_map'].items():
 if int(ch)>4:continue
 n='MW'+ch;rp=next(p for p in sample['pads'] if p['net']==n);rxy=(rp['x_board_relative_mm'],rp['y_board_relative_mm']);cp=current[int(pin)];cxy=tuple(v*UNIT for v in cp['coords'][:2]);native_net=ns[cp['net']]['NAME']
 closest=min(current,key=lambda k:math.dist(rxy,tuple(v*UNIT for v in current[k]['coords'][:2])))
 if closest!=int(pin) or native_net!=n:errors.append('Physical RF position mismatch '+n)
 mapping.append(dict(channel=n,reference_sample_pad=rp['number'],reference_xy_mm=rxy,current_QD_pad=int(pin),current_xy_mm=cxy,reference_bearing_deg=bearing(rxy),current_bearing_deg=bearing(cxy),centre_displacement_mm=math.dist(rxy,cxy),closest_available_current_pad=closest,source_to_pad=f'SMP{ch} -> C{ch} -> QD{pin}',bias=f'R{ch}'))
ro=[m['channel'] for m in sorted(mapping,key=lambda m:m['reference_bearing_deg'])];co=[m['channel'] for m in sorted(mapping,key=lambda m:m['current_bearing_deg'])]
if ro!=co:errors.append('Reference clockwise RF order changed')
old=snapshot(H/(B+'.PcbDoc'));ops=pads_stream(old['Pads6/Data']);ocs=properties(old['Components6/Data'])
oldrefs={c['SOURCEDESIGNATOR'] for c in ocs if not c['SOURCEDESIGNATOR'].startswith(('R','C'))};ocs_all=ocs;ocs=[c for c in ocs if c['SOURCEDESIGNATOR'] in oldrefs];actualold=[c for c in cs if c['SOURCEDESIGNATOR'] in oldrefs]
if [{k:c.get(k) for k in ['SOURCEDESIGNATOR','X','Y','ROTATION','LAYER','PATTERN','SOURCEUNIQUEID']} for c in actualold]!=[{k:c.get(k) for k in ['SOURCEDESIGNATOR','X','Y','ROTATION','LAYER','PATTERN','SOURCEUNIQUEID']} for c in ocs]:errors.append('Existing component placement changed unexpectedly')
def pgeom(p,cc):return (cc[p['component']]['SOURCEDESIGNATOR'] if p['component']!=65535 else 'MOUNT',p['number'],p['coords'],p['rotation'],p['layer'])
if collections.Counter(json.dumps(pgeom(p,cs)) for p in ps if p['component']==65535 or cs[p['component']]['SOURCEDESIGNATOR'] in oldrefs)!=collections.Counter(json.dumps(pgeom(p,ocs_all)) for p in ops if p['component']==65535 or ocs_all[p['component']]['SOURCEDESIGNATOR'] in oldrefs):errors.append('Fixed pad geometry changed')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(P/(B+'.PcbDoc')),straight_track_count=len(ts),non_octilinear_tracks=off,DC=dict(layers=[2,4],corner_count=len(turns),max_direction_change_deg=max(turns),disallowed_corners=sharp),RF=dict(arc_count=len(ars),radius_range_mm=[min(a['radius'] for a in ars),max(a['radius'] for a in ars)],tangent_junction_count=len(junctions),max_tangent_error_deg=max(junctions),hard_corners=kinks),reference=dict(path=str(refpath),sha256=refsha,unchanged=refsha==ref['source_sha256'],coordinate_view='Common board Top view: X right, Y up. Bottom component placement is already represented in saved coordinates.',method='Recompute all four biased-RF positions from native reference pad coordinates after the QD rotation/compaction. Closest available current peripheral pads and clockwise order both checked. Photograph is qualitative orientation evidence; no calibrated photo-to-board transform is claimed.',mapping=mapping,reference_clockwise=ro,current_clockwise=co),fixed_component_placement_and_pad_geometry_unchanged=not any('geometry' in x or 'metadata' in x for x in errors))
(H/'angle_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if not errors:(D/'RF_position_and_angles.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(bool(errors))
