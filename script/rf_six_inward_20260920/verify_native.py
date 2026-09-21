from pathlib import Path
import sys,json,struct,math,re,collections,itertools
H=Path(__file__).resolve().parent;W=H.parent/'_support'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board'),str(W/'zif_revision_v2/schematic'),str(W/'rf_revision'),str(W/'route_python')]
from native_metadata_helpers import properties,pads_stream,pad_record,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route,read_regions,paste_audit,read_rules,solid_audit
_vns={'__file__':str(W/'zif_revision_v2/schematic/validate_v2_schematic.py'),'__name__':'symmetric_validator'};exec(compile((H/'validator_source.py').read_text(),_vns['__file__'],'exec'),_vns);validate=_vns['validate']
from geometry_helpers import Line,Arc,copper_geometry
from shapely.geometry import box,Point,LineString
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB';D=P/'docs'
g=json.loads((H/'geometry.json').read_text());e=json.loads((H/'expected.json').read_text());dc=json.loads((H/'dc_routes.json').read_text());rf=json.loads((H/'rf_routes.json').read_text())
s=snapshot(P/(B+'.PcbDoc'));cs=properties(s['Components6/Data']);ns=properties(s['Nets6/Data']);ps=pads_stream(s['Pads6/Data']);ts,ars,vs=read_route(s,ns);cd={c['SOURCEDESIGNATOR']:c for c in cs}
errors=[]
def check(ok,why):
 if not ok:errors.append(why)
def close(a,b,t=4*UNIT):return abs(a-b)<=t
def mm(s):return float(s[:-3])*.0254
def shape(p):
 x,y,sx,sy=[v*UNIT for v in p['coords'][:4]]
 return translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),p['rotation'],origin=(0,0)),x,y)
check((len(cs),len(ps),len(ns),len(vs))==(22,147,37,72),'Object count mismatch')
check(struct.unpack('<I',s['Connections6/Header'])[0]==0 and not s['Connections6/Data'],'Saved PCB retains connection lines; rebuild nets and investigate actual continuity')
planpads={p['component']+'-'+p['number']:p for p in g['pads'] if p['component']};actual={cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number']:p for p in ps if p['component']!=65535}
vip=[]
for key,p in actual.items():
 q=planpads[key];xy=[v*UNIT for v in p['coords'][:2]];net=None if p['net']==65535 else ns[p['net']]['NAME']
 check(net==e['pin_net_map'].get(key),'Pin net mismatch '+key)
 check(close(xy[0],q['x']) and close(xy[1],q['y']),'Pad position mismatch '+key)
 check(close(p['coords'][2]*UNIT,q['size_x']) and close(p['coords'][3]*UNIT,q['size_y']),'Pad size mismatch '+key)
 check(abs((p['rotation']-q['rotation']+90)%180-90)<1e-6,'Pad rotation mismatch '+key)
 check(p['layer']==q['layer'],'Pad side mismatch '+key)
 if key.startswith(('Q1-','R','C')):
  vv=[v for v in vs if v['net']==net]
  if not vv:check(False,'No via '+key);continue
  v=min(vv,key=lambda v:math.dist((v['x'],v['y']),xy));distance=math.dist((v['x'],v['y']),xy)
  check(distance<4*UNIT and shape(p).buffer(3*UNIT).covers(Point(v['x'],v['y']).buffer(v['diameter']/2)),'Via not centred in pad '+key)
  vip.append(dict(pin=key,net=net,pad_center_mm=xy,via_center_mm=[v['x'],v['y']],offset_mm=distance,via_diameter_mm=v['diameter'],drill_mm=v['hole']))
for c in g['components']:
 a=cd[c['designator']]
 check(all(close(mm(a[k.upper()]),c[k]) for k in ('x','y')) and abs(float(a['ROTATION'])-c['rotation'])<1e-6 and a['LAYER']==c['side'] and a['PATTERN']==c['pattern'],'Component placement/model mismatch '+c['designator'])
old=snapshot(H/(B+'.PcbDoc'));oldps=pads_stream(old['Pads6/Data']);oldcs=properties(old['Components6/Data'])
check([p['coords'] for p in ps if p['component']==65535]==[p['coords'] for p in oldps if p['component']==65535],'Mounting holes changed')
check(s['BoardRegions/Data']==old['BoardRegions/Data'],'Board outline/regions changed')
check(not any(v['net']=='GND' for v in vs),'Shield via remains')
check(all(v['body'][1]&0x60==0x60 for v in vs),'Via tent flag absent')
regions=read_regions(s['Regions6/Data']);paste=paste_audit(regions,vs);check(paste['passed'],'Via paste aperture mismatch')
solid=solid_audit(regions,properties(s['Polygons6/Data']),ns,vs,read_rules(s['Rules6/Data']));check(solid['dominant_solid_rule_verified'] and len(solid['ground_polygons'])==3,'GND polygon/rule mismatch')
keep=box(*g['qd_signal_keepout']);intrusions=[];copper=[]
for t in ts:copper.append(Line((t['x1'],t['y1']),(t['x2'],t['y2']),t['layer'],t['width'],t['net']))
for a in ars:copper.append(Arc((a['cx'],a['cy']),a['radius'],a['start_angle'],(a['end_angle']-a['start_angle'])%360,a['layer'],a['width'],a['net']))
for t in copper:
 if copper_geometry(t,.000001).intersects(keep):intrusions.append(t.net)
check(not intrusions,'Signals cross QD opening')
check({t['layer'] for t in ts if t['net'].startswith('ZIF')}=={1,2,4},'DC outside L2/L4/fanout')
check(all(t['layer']==32 for t in ts+ars if t['net'].startswith(('MW','S'))),'RF outside Bottom')
# Native save merges collinear DC segments. Compare covered geometry by net/layer.
route_checks=[]
for net,layer in sorted({(t['net'],t['layer']) for t in ts}):
 actual_g=unary_union([LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in ts if (t['net'],t['layer'])==(net,layer)])
 wanted=[t for t in g['fanout_tracks']+dc['tracks']+rf['tracks'] if (t['net'],t['layer'])==(net,layer)]
 planned_g=unary_union([LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in wanted]);delta=actual_g.hausdorff_distance(planned_g)
 check(delta<6*UNIT,'Routed track coverage differs '+net);route_checks.append(dict(net=net,layer=layer,max_error_mm=delta))
check(len(ars)==len(rf['arcs'])==18,'RF arc count mismatch')
lib=snapshot(P/(B+'.PcbLib'));raw=lib['QD4/Data'];pos=4+(struct.unpack_from('<I',raw,0)[0]&0xffffff);n=0
while pos<len(raw):
 if raw[pos]==2:
  p=pad_record(raw,pos);pos=p['end'];q=planpads['Q1-'+p['number']];cx,cy=g['qd_component_center']
  check(close(cx-p['coords'][0]*UNIT,q['x']) and close(cy+p['coords'][1]*UNIT,q['y']),'QD footprint local-coordinate mismatch '+p['number']);n+=1
 else:pos+=5+(struct.unpack_from('<I',raw,pos+1)[0]&0xffffff)
check(n==24,'QD library pad count')
check(sha(P/(B+'.PcbLib'))==sha(H/(B+'.PcbLib')),'PcbLib changed')
for a in ars:
 candidates=[b for b in rf['arcs'] if b['net']==a['net'] and math.dist((a['cx'],a['cy']),(b['cx'],b['cy']))<6*UNIT]
 check(any(close(a['radius'],b['radius']) and abs((a['start_angle']-b['start_angle']+180)%360-180)<1e-5 and abs((a['end_angle']-b['end_angle']+180)%360-180)<1e-5 for b in candidates),'Native RF arc differs '+a['net'])
compilefile=P/'work/rf6_schematic_compile.txt';sch=validate(P/(B+'.SchDoc'),e,compilefile if compilefile.exists() else None,P/(B+'.PcbDoc'));check(sch['passed'],'Schematic mismatch: '+str(sch['errors']))
text=(D/'RF6_DRC.html').read_text(encoding='cp949',errors='replace');rows=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',text,re.S)
check(len(rows)==13 and sum(int(n) for _,n in rows)==0,'Native DRC violations remain')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(P/(B+'.PcbDoc')),pcblib_sha256=sha(P/(B+'.PcbLib')),schematic_sha256=sha(P/(B+'.SchDoc')),components=22,pcb_pads=147,named_nets=37,via_count=len(vs),ground_shield_vias=0,QD=dict(inner_pad_end_opening_mm=[4.3,4.3],pad_size_mm=[1,.5],pad_pitch_mm=.7,moved_to_top_edge=[1,24],via_in_pad=[x for x in vip if x['pin'].startswith('Q1-')],signal_interior_crossings=intrusions,library_matched=n==24),bias_via_in_pad=[x for x in vip if not x['pin'].startswith('Q1-')],capacitor_package='0402',resistor_package='0603',paste=paste,top_and_bottom_tented=len(vs),DRC_after_save_and_reopen=dict(violations=sum(int(n) for _,n in rows),checked_rules=len(rows),report='RF6_DRC.html',rules=dict(rows)),rf_qd_map=g['rf_qd_map'],zif_to_target=dc['zif_to_target'],RF_delay_matching='Deferred by user; short simple routes prioritized',RF_main_planar_lengths_mm={str(k):v['main_length_mm'] for k,v in rf['channels'].items()},route_geometry_comparison=route_checks,mask_exception='Via-in-pad holes share Bottom pad solder-mask openings; all via-specific top/bottom tent flags and paste apertures are present.')
(H/'native_validation.json').write_text(json.dumps(report,indent=2));(H/'schematic_final_validation.json').write_text(json.dumps(sch,indent=2));print(json.dumps(dict(passed=report['passed'],errors=errors,counts=dict(components=len(cs),pads=len(ps),vias=len(vs),tracks=len(ts),arcs=len(ars)),drc=report['DRC_after_save_and_reopen'],schematic=sch['passed']),indent=2))
if report['passed']:(D/'validation.json').write_text(json.dumps(report,indent=2)+'\n');(D/'schematic_validation.json').write_text(json.dumps(sch,indent=2)+'\n')
raise SystemExit(0 if report['passed'] else 1)
