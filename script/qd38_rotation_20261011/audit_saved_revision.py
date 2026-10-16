"""Compare a saved revision to an explicitly audited candidate, including arcs.

This is a read-only native audit adapted from the frozen carrier verifier.
Centreline-equivalent track splitting by AnalyzeNet/CleanNet is allowed; native
arcs, their tangent geometry, pad membership and via spans must match the plan.
Offline candidate validation, native DRC, mask, model and paste audits remain
separate and must all refer to the same saved revision before completion.
"""
from pathlib import Path
import argparse,json,importlib.util,struct,hashlib,collections,math,re
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist
from shapely.geometry import Polygon,shape,Point,box,LineString
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
from shapely.strtree import STRtree
from revision_invariants import contact_pool, assert_plan_contacts, via_groups
from audit_saved_rf_geometry import inspect_saved_rf
from audit_saved_dc_geometry import inspect_saved_dc
from track_geometry_equivalence import track_values, undirected_distance_matrix, union_metrics, metrics_pass
from combined_path_equivalence import inspect_combined_path_equivalence
H=Path(__file__).resolve().parent;ROOT=H.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD';UNIT=2.54e-6;TOL=1e-5
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate',required=True,type=Path)
parser.add_argument('--audit',required=True,type=Path)
parser.add_argument('--schematic',type=Path,default=DEST/'schematic_validation.json')
args=parser.parse_args()
candidate_path=args.candidate.resolve();candidate_audit_path=args.audit.resolve()
log=(H/'native_validation.txt').read_text();assert 'REOPENED' in log and 'COMPLETE' in log
spec=importlib.util.spec_from_file_location('saved_reader',ROOT/'script/_support/zif_revision_v2/render_native_layout.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);r.SOURCE=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
initial=sha(r.SOURCE)
with r.olefile.OleFileIO(r.SOURCE) as o:blobs={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
candidate_hash=sha(candidate_path);plan=json.loads(candidate_path.read_text());sch=json.loads(args.schematic.read_text());errors=[];warnings=[]
candidate_audit=json.loads(candidate_audit_path.read_text())
assert candidate_audit.get('passed') is True and candidate_audit.get('candidate_sha256')==candidate_hash,'Candidate audit is failed or stale'
assert_plan_contacts(plan)
via_groups(plan)
def check(ok,issue,detail=None):
 if not ok:errors.append(dict(issue=issue,detail=detail))
schematic_hash=sha(DEST/'QSTL_QD4_2SET_38PAD.SchDoc')
check(schematic_hash==sch.get('schematic_sha256'),'saved_schematic_differs_from_validated_netmap')
# Designator texts are authoritative even if SOURCEDESIGNATOR metadata is absent.
texts=[];b=blobs['Texts6/Data'];pos=0
while pos<len(b):
 assert b[pos]==5;n=struct.unpack_from('<I',b,pos+1)[0]&0xffffff;body=b[pos+5:pos+5+n];pos+=5+n
 n=struct.unpack_from('<I',b,pos)[0]&0xffffff;t=b[pos+4:pos+4+n];pos+=4+n
 texts.append(dict(component=struct.unpack_from('<H',body,7)[0],layer=body[0],text=t[1:].decode('cp1252')))
cs=r.props(blobs['Components6/Data']);native_names={}
for i,c in enumerate(cs):
 matches=[t['text'] for t in texts if t['component']==i and t['text'] in sch['components']]
 check(len(matches)==1,'component_designator_text_count',dict(index=i,matches=matches))
 native_names[i]=matches[0] if len(matches)==1 else c.get('SOURCEDESIGNATOR',f'UNKNOWN_{i}')
base_props=r.props
def augment(data):
 rows=base_props(data)
 if data==blobs['Components6/Data']:
  for i,row in enumerate(rows):row['SOURCEDESIGNATOR']=native_names[i]
 return rows
r.props=augment
native=r.read_native();check(sha(r.SOURCE)==initial,'PCB_changed_during_audit')
baseline_path=H/'before_rotation/QSTL_QD4_2SET_38PAD.PcbDoc'
check(sha(baseline_path)=='f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632','pre_revision_backup_hash')
with r.olefile.OleFileIO(baseline_path) as o:baseline_blobs={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
old_board=r.props(baseline_blobs['Board6/Data'])[0];new_board=r.props(blobs['Board6/Data'])[0]
stack=lambda row:{k:v for k,v in row.items() if k.startswith('V9_STACK_')}
check(stack(old_board)==stack(new_board),'native_layer_stack_changed')
check(Polygon(native['board_outline']).hausdorff_distance(Polygon(plan['board_outline']))<TOL,'board_outline_changed')
for stream,kind in [('Tracks6/Data',4),('Arcs6/Data',1)]:
 old_outline=[body for body in r.binary(baseline_blobs[stream],kind) if body[0]==57]
 new_outline=[body for body in r.binary(blobs[stream],kind) if body[0]==57]
 # Keep geometry exact while allowing Altium to refresh unrelated object flags.
 geometry=lambda body:body[13:33] if kind==4 else body[13:45]
 check(sorted(map(geometry,old_outline))==sorted(map(geometry,new_outline)),'mechanical_1_outline_geometry_changed',stream)
check(len(cs)==50,'component_count',len(cs));check(len(native['pads'])==243,'pad_count',len(native['pads']))
check(len([p for p in native['pads'] if p['component']=='Q1'])==38,'QD_pad_count')
check(struct.unpack('<I',blobs['Connections6/Header'])[0]==0,'stored_connections_nonzero')
check({native_names[i]:c.get('SOURCEUNIQUEID','').strip('\\') for i,c in enumerate(cs)}==sch['components'],'component_SourceUniqueID_mismatch')
counts={k:len(native[k]) for k in ['components','pads','tracks','arcs','vias','bodies']};maxerrs={}
def group_match(actual,expected,key,values,name,undirected=False,emit_errors=True):
 ga=collections.defaultdict(list);ge=collections.defaultdict(list)
 for x in actual:ga[key(x)].append(x)
 for x in expected:ge[key(x)].append(x)
 errs=[];maximum=0
 for k in set(ga)|set(ge):
  a,e=ga[k],ge[k]
  if len(a)!=len(e):errs.append(dict(key=str(k),actual_count=len(a),expected_count=len(e)));continue
  if not a:continue
  aa=np.array([values(x) for x in a]);ee=np.array([values(x) for x in e])
  dist=undirected_distance_matrix(aa,ee) if undirected else cdist(aa,ee,metric='chebyshev')
  rr,cc=linear_sum_assignment(dist)
  maximum=max(maximum,float(max(dist[rr,cc])))
  for ri,ci in zip(rr,cc):
   if dist[ri,ci]>TOL:errs.append(dict(key=str(k),error=float(dist[ri,ci]),actual=aa[ri].tolist(),expected=ee[ci].tolist()))
 maxerrs[name]=maximum
 if emit_errors:check(not errs,name+'_mismatch',errs[:80])
 return errs
cx,cy=plan['sample_center'];cw,ch=plan['cavity_mm'];cr=plan.get('cavity_radius_mm',.5)
x0,x1,y0,y1=cx-cw/2,cx+cw/2,cy-ch/2,cy+ch/2
actual_fab_tracks=[]
for b in r.binary(blobs['Tracks6/Data'],4):
 if b[0]==59:actual_fab_tracks.append(dict(zip(('x1','y1','x2','y2','width'),[v*UNIT for v in struct.unpack_from('<5i',b,13)])))
expected_fab_tracks=[dict(x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=.05) for a,b in [((x0+cr,y0),(x1-cr,y0)),((x1,y0+cr),(x1,y1-cr)),((x1-cr,y1),(x0+cr,y1)),((x0,y1-cr),(x0,y0+cr))]]
fab_track_values=lambda t:[*sum(sorted([(t['x1'],t['y1']),(t['x2'],t['y2'])]),()),t['width']]
group_match(actual_fab_tracks,expected_fab_tracks,lambda a:'M3',fab_track_values,'blind_pocket_lines',undirected=True)
actual_fab_arcs=[]
for b in r.binary(blobs['Arcs6/Data'],1):
 if b[0]==59:
  x,y,rad=[v*UNIT for v in struct.unpack_from('<3i',b,13)];a0,a1=struct.unpack_from('<2d',b,25)
  actual_fab_arcs.append(dict(cx=x,cy=y,radius=rad,start_angle=a0,end_angle=a1,width=struct.unpack_from('<i',b,41)[0]*UNIT))
expected_fab_arcs=[dict(cx=x,cy=y,radius=cr,start_angle=a0,end_angle=a1,width=.05) for x,y,a0,a1 in [(x1-cr,y0+cr,270,360),(x1-cr,y1-cr,0,90),(x0+cr,y1-cr,90,180),(x0+cr,y0+cr,180,270)]]
group_match(actual_fab_arcs,expected_fab_arcs,lambda a:'M3',lambda a:[a['cx'],a['cy'],a['radius'],a['start_angle']%360,a['end_angle']%360,a['width']],'blind_pocket_arcs')
fab_notes=[t['text'] for t in texts if t['layer']==59]
check(any('4.3 x 5.3 mm' in t and 'DEPTH 1.2 mm FROM BOTTOM' in t and 'NON-THROUGH' in t for t in fab_notes),'rotated_blind_pocket_note_missing',fab_notes)
expectedcomps=[dict(designator=c['ref'],pattern=c['pattern'],side='TOP' if c['layer']==1 else 'BOTTOM',x=c['x'],y=c['y'],rotation=c['rotation']) for c in plan['components']]
group_match(native['components'],expectedcomps,lambda c:(c['designator'],c['pattern'],c['side']),lambda c:[c['x'],c['y'],c['rotation']%360],'components')
expectedpads=[dict(component=p['ref'] or None,number=p['pin'],net=p['net'],layer=p['layer'],x=p['x'],y=p['y'],size_x=p['sx'],size_y=p['sy'],hole=p['hole'],rotation=p['rotation']) for p in plan['physical_pads']]
group_match(native['pads'],expectedpads,lambda p:(p['component'],p['number'],p['net'],p['layer']),lambda p:[p['x'],p['y'],p['size_x'],p['size_y'],p['hole'],p['rotation']%360],'pads')
expected_shapes={(p['ref'],p['pin']):2 if p['shape']=='rect' else 1 for p in plan['physical_pads']}
check(all(p['shape']==expected_shapes[(p['component'],p['number'])] for p in native['pads']),'pad_shape_mismatch')
# Exact primitive matching is diagnostic: CleanNet can split arcs and move a
# pad-covered endpoint without changing routed copper. The independent
# combined RF path audit below checks physical centreline/copper, circle
# geometry and angular coverage in millimetres instead of comparing degrees
# directly with a linear tolerance.
arc_record_errors=group_match(native['arcs'],plan['arcs'],lambda a:(a['net'],a['layer']),lambda a:[a['cx'],a['cy'],a['radius'],a['start_angle']%360,a['end_angle']%360,a['width']],'signal_arcs',emit_errors=False)
arc_record_mixed_unit_error=maxerrs.pop('signal_arcs')
is_rf=lambda net:(net or '').startswith(('S','MW'))
check(all(is_rf(a['net']) for a in native['arcs']+plan['arcs']),'unexpected_non_RF_signal_arc')
check(len(native['arcs'])>0,'RF_tangent_arcs_missing')
expectedtracks=[dict(net=t['net'],layer=t['layer'],x1=t['a'][0],y1=t['a'][1],x2=t['b'][0],y2=t['b'][1],width=t['width']) for t in plan['tracks']]
def tv(t):
 return track_values(t)
track_record_errors=group_match(native['tracks'],expectedtracks,lambda t:(t['net'],t['layer']),tv,'tracks',undirected=True,emit_errors=False)
track_normalization=[]
if track_record_errors:
 # Altium AnalyzeNet/CleanNet may split a track at an existing copper junction.
 # Verify both centreline topology and width-specific copper, rather than
 # treating a mere split of one segment into several as a routing mutation.
 ga=collections.defaultdict(list);ge=collections.defaultdict(list)
 for t in native['tracks']:ga[(t['net'],t['layer'],round(t['width'],5))].append(t)
 for t in expectedtracks:ge[(t['net'],t['layer'],round(t['width'],5))].append(t)
 split_fail=[]
 for key in set(ga)|set(ge):
  a,e=ga[key],ge[key]
  if not a or not e:
   if not is_rf(key[0]):split_fail.append(dict(key=str(key),actual_count=len(a),expected_count=len(e)))
   continue
  # Nearly coincident expected segments can differ by a few floating-point
  # ULPs and falsely contribute their overlapping length twice. Normalize
  # only the union-length metric to Altium's integer coordinate grid; retain
  # all original unsnapped copper/width/coverage and Hausdorff checks.
  metric=dict(key=str(key),**union_metrics(a,e))
  track_normalization.append(metric)
  # Keep the strict line-only proof for DC and other non-RF copper. RF lines
  # and arcs form a single geometric object and are proved together below.
  metric['line_only_passed']=metrics_pass(metric)
  metric['authoritative_comparison']='combined_RF_path' if is_rf(key[0]) else 'line_union'
  if not is_rf(key[0]) and not metric['line_only_passed']:split_fail.append(metric)
 if not split_fail:
  warnings.append('Native AnalyzeNet/CleanNet normalized primitive records; non-RF tracks are checked by native-grid line unions and raw copper coverage, and RF uses the separate combined line/arc/pad equivalence proof at 0.00001 mm.')
 else:check(False,'native_track_split_geometry_mismatch',split_fail)
combined_rf_equivalence=inspect_combined_path_equivalence(native,plan,tol=TOL)
check(combined_rf_equivalence['passed'],'native_RF_combined_path_geometry_mismatch',combined_rf_equivalence.get('failures',[]))
ns=r.props(blobs['Nets6/Data']);vias=[]
for b in r.binary(blobs['Vias6/Data'],3):
 ni=struct.unpack_from('<H',b,3)[0];x,y,d,h=struct.unpack_from('<4i',b,13);vias.append(dict(net=None if ni==65535 else ns[ni]['NAME'],x=x*UNIT,y=y*UNIT,diameter=d*UNIT,hole=h*UNIT,low=b[29],high=b[30]))
group_match(vias,plan['vias']+plan['shield_vias'],lambda v:(v['net'],v['low'],v['high']),lambda v:[v['x'],v['y'],v['diameter'],v['hole']],'vias')
check(sum(v['net']!='GND' and (v['low'],v['high'])==(1,32) for v in vias)==76,'signal_via_spans')
check(sum(v['net']=='GND' and (v['low'],v['high'])==(5,32) for v in vias)==len(plan['shield_vias']),'shield_via_spans')
direct_via_checks=[]
for pad in native['pads']:
 if pad['component']!='Q1' or not (pad['net'] or '').startswith('DC'):continue
 endpoint=[v for v in vias if v['net']==pad['net'] and v['y']>8]
 geom=translate(rotate(box(-pad['size_x']/2,-pad['size_y']/2,pad['size_x']/2,pad['size_y']/2),pad['rotation'],origin=(0,0)),pad['x'],pad['y'])
 ok=len(endpoint)==1 and geom.buffer(TOL).covers(Point(endpoint[0]['x'],endpoint[0]['y']))
 hole_ok=ok and geom.buffer(TOL).covers(Point(endpoint[0]['x'],endpoint[0]['y']).buffer(endpoint[0]['hole']/2,quad_segs=64))
 item=dict(pin=pad['number'],net=pad['net'],endpoint_via_count=len(endpoint),center_in_pad=ok,drill_within_pad=hole_ok)
 direct_via_checks.append(item);check(ok and hole_ok,'direct_QD_via_not_in_pad',item)
check(len(direct_via_checks)==22,'direct_QD_via_check_count',len(direct_via_checks))
internal_dc_layers={f'DC{i:02}':sorted({t['layer'] for t in native['tracks'] if t['net']==f'DC{i:02}' and t['layer'] in (2,4)}) for i in range(1,39)}
check(all(len(layers)==1 for layers in internal_dc_layers.values()),'DC_not_single_internal_layer',internal_dc_layers)
check(all(v==2 for k,v in collections.Counter(v['net'] for v in vias if (v['net'] or '').startswith('DC')).items()),'unexpected_DC_transition_via_count')
saved_rf_geometry=inspect_saved_rf(native,vias)
check(saved_rf_geometry['passed'],'saved_RF_geometry_requirements',saved_rf_geometry['failures'])
# Parse all region contours, preserving every hole.
regions=[]
for b in r.binary(blobs['Regions6/Data'],11):
 off=b.index(b'V7_LAYER=');n=struct.unpack_from('<I',b,off-4)[0]&0xffffff;prop=dict(x.split('=',1) for x in b[off:off+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x);pos=off+n;rings=[]
 while pos<len(b):
  count=struct.unpack_from('<I',b,pos)[0];pos+=4;rings.append([tuple(v*UNIT for v in struct.unpack_from('<2d',b,pos+16*i)) for i in range(count)]);pos+=16*count
 assert pos==len(b)
 regions.append(dict(name=prop.get('NAME'),layer=b[0],net_index=struct.unpack_from('<H',b,3)[0],geometry=Polygon(rings[0],rings[1:])))
saved_dc_geometry=inspect_saved_dc(native,vias,[reg for reg in regions if reg['net_index']!=65535 and ns[reg['net_index']]['NAME']=='GND'])
check(saved_dc_geometry['passed'],'saved_DC_geometry_requirements',saved_dc_geometry['failures'])
region_fail=[];region_metrics=[];expected_names=[]
for family,field in [('GND','ground_regions'),('MASK','solder_openings')]:
 for layer,m in plan[field].items():
  g=shape(m).simplify(.001,preserve_topology=True);parts=list(g.geoms) if hasattr(g,'geoms') else [g]
  for i,part in enumerate(parts):
   name=f'QD38_{family}_{layer}_{i}';expected_names.append(name);actual=[x for x in regions if x['name']==name]
   if len(actual)!=1:region_fail.append(dict(name=name,count=len(actual)));continue
   a=actual[0];haus=part.hausdorff_distance(a['geometry']);area=part.symmetric_difference(a['geometry']).area
   region_metrics.append(dict(name=name,layer=a['layer'],hausdorff_mm=haus,symmetric_difference_mm2=area,valid=a['geometry'].is_valid))
   if haus>TOL or int(layer)!=a['layer'] or not a['geometry'].is_valid:region_fail.append(region_metrics[-1])
check(not region_fail,'regions_mismatch',region_fail)
check(set(expected_names)=={x['name'] for x in regions},'unexpected_regions',list({x['name'] for x in regions}-set(expected_names)))
# Verify saved GND copper continuity independently of stored airwire caches.
ground_nodes=[]
for pad in native['pads']:
 if pad['net']!='GND':continue
 if pad['shape']==1:
  geom=Point(pad['x'],pad['y']).buffer(pad['size_x']/2,quad_segs=64)
 else:
  geom=translate(rotate(box(-pad['size_x']/2,-pad['size_y']/2,pad['size_x']/2,pad['size_y']/2),pad['rotation'],origin=(0,0)),pad['x'],pad['y'])
 ground_nodes.append(dict(label='PAD:'+str(pad['component'])+'-'+pad['number'],layers={1,2,3,4,5,32} if pad['layer']==74 else {pad['layer']},geometry=geom))
for i,v in enumerate(vias):
 if v['net']=='GND':ground_nodes.append(dict(label='VIA:'+str(i),layers={ll for ll in [1,2,3,4,5,32] if v['low']<=ll<=v['high']},geometry=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)))
for reg in regions:
 if reg['net_index']!=65535 and ns[reg['net_index']]['NAME']=='GND':ground_nodes.append(dict(label=reg['name'],layers={reg['layer']},geometry=reg['geometry']))
parent=list(range(len(ground_nodes)))
def root(k):
 while parent[k]!=k:parent[k]=parent[parent[k]];k=parent[k]
 return k
for ll in [1,2,3,4,5,32]:
 ids=[i for i,n in enumerate(ground_nodes) if ll in n['layers']];geoms=[ground_nodes[i]['geometry'] for i in ids];tree=STRtree(geoms)
 for i,g in enumerate(geoms):
  for j in tree.query(g.buffer(4*UNIT)):
   if i<int(j) and g.distance(geoms[int(j)])<=4*UNIT:parent[root(ids[i])]=root(ids[int(j)])
ground_groups=collections.defaultdict(list)
for i,n in enumerate(ground_nodes):ground_groups[root(i)].append(n['label'])
ground_connected=len(ground_groups)==1
check(ground_connected,'saved_GND_copper_disconnected',list(ground_groups.values()) if not ground_connected else None)
# Compare actual component pad membership to the generated schematic and live compiler.
pinmap={p['component']+'-'+p['number']:p['net'] for p in native['pads'] if p['component']};expected={**sch['pin_net'],**{k:None for k in sch['nc']}}
check(pinmap==expected,'schematic_pad_net_mismatch',{k:[pinmap.get(k),expected.get(k)] for k in set(pinmap)|set(expected) if pinmap.get(k)!=expected.get(k)})
saved_zif_pads=[p for p in native['pads'] if p['component']=='J1' and p['net'] is not None]
saved_contact_pool=contact_pool(p['number'] for p in saved_zif_pads)
check(saved_contact_pool['passed'],'saved_ZIF_legacy_contact_pool',saved_contact_pool)
check(len({p['net'] for p in saved_zif_pads})==38 and all(p['net'].startswith('DC') for p in saved_zif_pads),'saved_ZIF_independent_DC_membership')
compiled={};compilemeta={};cp=H/'native_compile.txt';compiled_verified=False
if cp.exists():
 net=None
 for line in cp.read_text().splitlines():
  if line.startswith('NET='):net=line[4:].split('|')[0];compiled[net]=[]
  elif line.startswith('PIN=') and net:compiled[net].append(line[4:].replace('.','-'))
  elif '=' in line:compilemeta[line.split('=',1)[0]]=line.split('=',1)[1]
 if 'COMPLETE' in cp.read_text():
  check(all(set(compiled.get(n,[]))==set(pins) for n,pins in plan['nets'].items()),'live_compiled_nets_mismatch',{n:[compiled.get(n),pins] for n,pins in plan['nets'].items() if set(compiled.get(n,[]))!=set(pins)})
  floating={n:pins for n,pins in compiled.items() if n not in plan['nets']}
  check(all(len(p)==1 and p[0] in sch['nc'] for p in floating.values()),'unexpected_compiled_floating_nets',floating)
  check({p[0] for p in floating.values() if len(p)==1}==set(sch['nc']),'compiled_NC_membership_mismatch',floating)
  check(compilemeta.get('VIOLATION_COUNT')=='0','native_compile_violations',compilemeta)
  check(compilemeta.get('PROJECT','').casefold()==str(DEST/'QSTL_QD4_2SET_38PAD.PrjPcb').casefold(),'compiled_project_mismatch',compilemeta.get('PROJECT'))
  compiled_verified=not any(x['issue'] in ['live_compiled_nets_mismatch','unexpected_compiled_floating_nets','compiled_NC_membership_mismatch','native_compile_violations','compiled_project_mismatch','saved_schematic_differs_from_validated_netmap'] for x in errors)
 else:check(False,'live_compile_log_incomplete')
else:check(False,'live_compile_log_unavailable')
check(compiled_verified,'saved_compiled_membership_not_verified')
provenance=json.loads((DEST/'copy_provenance.json').read_text());preserved={name:sha(ROOT/'QSTL_24DC_4MW_PCB'/name)==v for name,v in provenance['source_sha256'].items()};check(all(preserved.values()),'original_source_changed',preserved)
trackdupes=[(str(k),v) for k,v in collections.Counter((t['net'],t['layer'],tuple(round(x/UNIT) for x in tv(t))) for t in native['tracks']).items() if v>1]
viadupes=[(str(k),v) for k,v in collections.Counter((v['net'],v['low'],v['high'],round(v['x']/UNIT),round(v['y']/UNIT)) for v in vias).items() if v>1]
check(not trackdupes,'duplicate_tracks',trackdupes);check(not viadupes,'duplicate_vias',viadupes)
arcdupes=[(str(k),v) for k,v in collections.Counter((a['net'],a['layer'],round(a['cx']/UNIT),round(a['cy']/UNIT),round(a['radius']/UNIT),round(a['start_angle']%360,7),round(a['end_angle']%360,7),round(a['width']/UNIT)) for a in native['arcs']).items() if v>1]
check(not arcdupes,'duplicate_arcs',arcdupes)
paste_flag=re.search(r'VIA_PASTE_ENABLED=(\d+)',log)
if paste_flag and int(paste_flag.group(1))>0:warnings.append('Native GetState_PasteMaskEnabled reports True on '+paste_flag.group(1)+' vias; effective CAM openings still require verification despite negative cache expansion.')
if 'DRC_RETURNED_FALSE' in log:warnings.append('Native DRC API returned False; this audit does not certify native DRC success.')
if compilemeta.get('COMPILE_RESULT')!='True':warnings.append('Native compiler returned False; net connectivity was independently compared where COMPLETE exists.')
report=dict(passed=not errors,native_file=str(r.SOURCE),native_sha256=initial,counts=counts,signal_vias=len(plan['vias']),shield_vias=len(plan['shield_vias']),candidate_sha256=candidate_hash,region_count=len(regions),max_numeric_error=maxerrs,regions_max_hausdorff_mm=max(x['hausdorff_mm'] for x in region_metrics),native_connection_count=struct.unpack('<I',blobs['Connections6/Header'])[0],component_SourceUniqueIDs_match=not any(x['issue']=='component_SourceUniqueID_mismatch' for x in errors),live_compile=compilemeta,compiled_net_count=len(compiled),source_files_unchanged=preserved,errors=errors,warnings=warnings,region_metrics=region_metrics,track_record_comparison_exact=not track_record_errors,track_normalization_checks=track_normalization,ground_copper_connected=ground_connected,ground_copper_component_count=len(ground_groups),ground_primitives=len(ground_nodes),completion=False)
report.update(schematic_sha256=schematic_hash,live_compile_sha256=sha(cp) if cp.exists() else None,live_compile_membership_verified=compiled_verified)
assert sha(r.SOURCE)==initial,'Native changed before end of audit'
assert sha(candidate_path)==candidate_hash,'Candidate changed during audit'
report['candidate_file']=str(candidate_path)
report['candidate_audit_file']=str(candidate_audit_path)
report['candidate_audit_sha256']=sha(candidate_audit_path)
report['scope']='Saved pad/net, arc/track/via/region equivalence to the audited complete candidate, ground continuity and compiled net membership; not an independent manufacturing release.'
report['pre_revision_backup_file']=str(baseline_path)
report['layer_stack_preserved']=stack(old_board)==stack(new_board)
report['direct_QD_via_in_pad']=direct_via_checks
report['DC_internal_layers']=internal_dc_layers
report['ZIF_contact_pool']=saved_contact_pool
report['saved_RF_geometry']=saved_rf_geometry
report['saved_RF_combined_equivalence']=combined_rf_equivalence
report['arc_record_comparison_exact']=not arc_record_errors
report['arc_record_comparison_diagnostics']=arc_record_errors
report['arc_record_mixed_unit_error_diagnostic']=arc_record_mixed_unit_error
report['saved_DC_geometry']=saved_dc_geometry
(H/'saved_revision_audit.json').write_text(json.dumps(report,indent=2));(H/'saved_revision_snapshot.json').write_text(json.dumps(native,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ['region_metrics','source_files_unchanged','track_normalization_checks']},indent=2))




