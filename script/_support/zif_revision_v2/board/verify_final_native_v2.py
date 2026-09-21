"""Cold, read-only V2 acceptance checks after native save/reopen/repour.

Never writes a design. The only write is the requested QA JSON under work.
Region tails are consumed exactly as repeated uint32 + count*(double,double),
with the first contour exterior and every subsequent contour a hole.
"""
from pathlib import Path
import sys,json,struct,re,collections,hashlib,math,argparse,html
HERE=Path(__file__).resolve().parent;WORK=HERE.parents[1];ROOT=WORK.parent
sys.path[:0]=[str(WORK/'qd_center_revision'),str(WORK/'final_routing/schematic'),str(WORK/'route_python'),str(WORK/'rf_revision')]
from native_metadata_helpers import properties,pads_stream,binary_records,sha,UNIT
from build_routed_copy import snapshot
from geometry_helpers import Arc,copper_geometry
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.affinity import rotate,translate

DEFAULT_PCB=ROOT/'outputs/QSTL_ZIF24_V2_project/QSTL_ZIF24_V2.PcbDoc'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def u16(b,i):return struct.unpack_from('<H',b,i)[0]
def u32(b,i):return struct.unpack_from('<I',b,i)[0]
def mm(s):return float(s[:-3])*.0254 if s.endswith('mil') else float(s)
def pair(p):return p['x'],p['y']
def angle_error(a,b):return abs((a-b+180)%360-180)
def decoded_name(s):
 if re.fullmatch(r'\d+(,\d+)+',s or ''):return ''.join(chr(int(x)) for x in s.split(','))
 return s

def read_rules(data):
 pos=0;out=[]
 while pos<len(data):
  kind,n=struct.unpack_from('<HI',data,pos);pos+=6
  assert pos+n<=len(data),'Truncated rule'
  prop=properties(struct.pack('<I',n)+data[pos:pos+n])[0];pos+=n
  out.append(dict(prop,_native_kind=kind))
 assert pos==len(data);return out

def read_regions(data):
 result=[]
 for row in binary_records(data,11):
  b=row['body'];off=b.index(b'V7_LAYER=');n=u32(b,off-4)
  assert off+n<=len(b),'Region property string exceeds body'
  prop=dict(x.split('=',1) for x in b[off:off+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
  pos=off+n;rings=[]
  while pos<len(b):
   assert pos+4<=len(b),'Incomplete region contour count'
   count=u32(b,pos);pos+=4
   assert count>=3 and pos+count*16<=len(b),(row['index'],'Invalid contour count',count)
   rings.append([tuple(v*UNIT for v in struct.unpack_from('<2d',b,pos+i*16)) for i in range(count)])
   pos+=count*16
  assert pos==len(b) and rings,'Region tail not consumed exactly'
  g=Polygon(rings[0],rings[1:])
  result.append({'index':row['index'],'layer':b[0],'net_index':u16(b,3),'polygon_index':u16(b,5),'component_index':u16(b,7),'props':prop,'name':decoded_name(prop.get('NAME','')),'rings':rings,'geometry':g,'valid':g.is_valid,'tail_bytes':len(b)-off-n,'consumed_exactly':True})
 return result

def read_route(data,nets):
 tracks=[];arcs=[];vias=[]
 for row in binary_records(data['Tracks6/Data'],4):
  b=row['body'];net=u16(b,3)
  if net==65535:continue
  x1,y1,x2,y2,w=struct.unpack_from('<5i',b,13)
  tracks.append(dict(index=row['index'],net=nets[net]['NAME'],layer=b[0],V7=u32(b,41),x1=x1*UNIT,y1=y1*UNIT,x2=x2*UNIT,y2=y2*UNIT,width=w*UNIT,native_coords=[x1,y1,x2,y2,w]))
 for row in binary_records(data['Arcs6/Data'],1):
  b=row['body'];net=u16(b,3)
  if net==65535:continue
  x,y,r=struct.unpack_from('<3i',b,13);sa,ea=struct.unpack_from('<2d',b,25);w=struct.unpack_from('<i',b,41)[0]
  arcs.append(dict(index=row['index'],net=nets[net]['NAME'],layer=b[0],V7=u32(b,52),cx=x*UNIT,cy=y*UNIT,radius=r*UNIT,start_angle=sa,end_angle=ea,width=w*UNIT,native_coords=[x,y,r,w]))
 for row in binary_records(data['Vias6/Data'],3):
  b=row['body'];net=u16(b,3);x,y,d,h=struct.unpack_from('<4i',b,13)
  vias.append(dict(index=row['index'],net=None if net==65535 else nets[net]['NAME'],x=x*UNIT,y=y*UNIT,diameter=d*UNIT,hole=h*UNIT,native_coords=[x,y,d,h],body=b))
 return tracks,arcs,vias

def trackkey(t):
 vals=t.get('native_coords') or [round(t[k]/UNIT) for k in ['x1','y1','x2','y2','width']]
 return t['net'],t['layer'],tuple(sorted([tuple(vals[:2]),tuple(vals[2:4])])),vals[4]
def arckey(a):
 vals=a.get('native_coords') or [round(a.get('cx',a.get('x'))/UNIT),round(a.get('cy',a.get('y'))/UNIT),round(a['radius']/UNIT),round(a['width']/UNIT)]
 return a['net'],a['layer'],tuple(vals),round(a['start_angle']%360,6),round(a['end_angle']%360,6)
def viakey(v):return v['net'],tuple(v.get('native_coords') or [round(v[k]/UNIT) for k in ['x','y','diameter','hole']])

def paste_audit(regions,vias):
 rows=[r for r in regions if r['name'].startswith('ZIFV2_PASTE_')];errors=[];matches=collections.Counter();details=[]
 for r in rows:
  points=r['rings'][0];cx=sum(p[0] for p in points)/len(points);cy=sum(p[1] for p in points)/len(points)
  distance,v=min(((math.dist((cx,cy),pair(v)),v) for v in vias),key=lambda item:item[0])
  radii=[math.dist(p,(cx,cy)) for p in points];radius_error=max(abs(x-v['diameter']/2) for x in radii)
  layer=r['layer'];expected_name='ZIFV2_PASTE_T_' if layer==35 else 'ZIFV2_PASTE_B_'
  item=dict(region=r['index'],via_index=v['index'],layer=layer,vertex_count=len(points),contours=len(r['rings']),center_error_mm=distance,max_vertex_radius_error_mm=radius_error)
  details.append(item);matches[(v['index'],layer)]+=1
  if layer not in (35,36) or not r['name'].startswith(expected_name) or distance>3*UNIT or radius_error>3*UNIT or len(points)!=72 or len(r['rings'])!=1 or not r['valid'] or r['props'].get('KIND')!='0':errors.append(item)
 missing=[{'via_index':v['index'],'layer':layer,'actual_apertures':matches[(v['index'],layer)]} for v in vias for layer in (35,36) if matches[(v['index'],layer)]!=1]
 return dict(passed=not errors and not missing and len(rows)==2*len(vias),regions=len(rows),top=sum(r['layer']==35 for r in rows),bottom=sum(r['layer']==36 for r in rows),via_count=len(vias),all_region_tails_consumed_exactly=all(r['consumed_exactly'] for r in rows),max_center_error_mm=max((d['center_error_mm'] for d in details),default=None),max_vertex_radius_error_mm=max((d['max_vertex_radius_error_mm'] for d in details),default=None),errors=errors,missing_or_duplicate=missing,evidence='Actual filled 72-vertex region contours on TopPaste35/BottomPaste36; diameter equals native via copper. Native CAM export still requires separate verification.')

def solid_audit(regions,polygons,nets,vias,rules):
 poly_ids=[i for i,p in enumerate(polygons) if p.get('NET') is not None and nets[int(p['NET'])]['NAME']=='GND']
 ground_rules=[r for r in rules if r.get('RULEKIND')=='PolygonConnect' and r.get('ENABLED')=='TRUE']
 solid=[r for r in ground_rules if r.get('NAME')=='ZIF24V2_GND_VIA_SOLID']
 def scope(s):return re.sub(r'\s+','',s).lower()
 rule_ok=len(solid)==1 and solid[0].get('CONNECTSTYLE')=='Direct' and scope(solid[0].get('SCOPE1EXPRESSION',''))=="isviaandinnet('gnd')" and solid[0].get('SCOPE2EXPRESSION')=='All' and all(int(solid[0]['PRIORITY'])<int(r['PRIORITY']) for r in ground_rules if r is not solid[0])
 samples=[];inner_samples=[];layer_reports=[]
 for pi in poly_ids:
  rr=[r for r in regions if r['polygon_index']==pi and r['props'].get('KIND')=='0']
  # Invalid touching contours are repaired for point membership only and
  # reported. Every hole was parsed before this operation, never discarded.
  gg=unary_union([r['geometry'] if r['valid'] else r['geometry'].buffer(0) for r in rr]);prepared=prep(gg)
  layer_reports.append(dict(polygon=pi,layer=polygons[pi]['LAYER'],child_regions=len(rr),hole_contours=sum(len(r['rings'])-1 for r in rr),invalid_children_repaired=[r['index'] for r in rr if not r['valid']],area_mm2=gg.area))
  for v in vias:
   if v['net']!='GND':continue
   radius=v['diameter']/2+.01
   covered=[prepared.covers(Point(v['x']+radius*math.cos(math.radians(a)),v['y']+radius*math.sin(math.radians(a)))) for a in range(360)]
   if not all(covered):samples.append(dict(via_index=v['index'],x=v['x'],y=v['y'],polygon=pi,layer=polygons[pi]['LAYER'],covered_degrees=sum(covered),fraction=sum(covered)/360,uncovered_degrees=[i for i,x in enumerate(covered) if not x]))
   # A point just inside the native copper land avoids falsely demanding
   # extra copper beyond the via where unrelated clearances clip the pour.
   radius=v['diameter']/2-.002
   inner=[prepared.covers(Point(v['x']+radius*math.cos(math.radians(a)),v['y']+radius*math.sin(math.radians(a)))) for a in range(360)]
   if not all(inner):inner_samples.append(dict(via_index=v['index'],x=v['x'],y=v['y'],polygon=pi,layer=polygons[pi]['LAYER'],covered_degrees=sum(inner),fraction=sum(inner)/360,uncovered_degrees=[i for i,x in enumerate(inner) if not x]))
 return dict(dominant_solid_rule_verified=rule_ok,rule=solid,other_polygon_rule_priorities=[{'name':r.get('NAME'),'priority':r.get('PRIORITY'),'style':r.get('CONNECTSTYLE')} for r in ground_rules],ground_polygons=layer_reports,ground_vias=sum(v['net']=='GND' for v in vias),ring_sample_count_per_via_per_polygon=360,ring_radius='native via copper radius +0.01mm',partial_or_missing_ring_samples=samples,full_rings=len(poly_ids)*sum(v['net']=='GND' for v in vias)-len(samples),partial_count=len(samples),inner_ring_radius='native via copper radius -0.002mm',inner_ring_full_annulus_all_ground_vias_all_four_polygons=not inner_samples and len(poly_ids)==4,inner_ring_partial_count=len(inner_samples),inner_ring_partial_samples=inner_samples,interpretation='The outer radius+0.01 ring may be clipped by unrelated copper clearances. The radius-0.002 ring checks a full annulus within the native land. Any partial ring is reported for review instead of being automatically called a thermal. Native dominant direct rule and actual poured-region rings are separate evidence.')

def verify(pcb,plan_path,expected_path,out):
 required=[pcb,plan_path,expected_path,HERE/'routing_geometry.json',HERE.parent/'reference/reference_geometry.json']
 absent=[str(p) for p in required if not p.exists()]
 if absent:raise FileNotFoundError('Final inputs not available: '+', '.join(absent))
 hashes={str(p.resolve()):sha(p) for p in required};d=snapshot(pcb);plan=load(plan_path);e=load(expected_path);g=load(required[3]);ref=load(required[4]);errors=[];warnings=[]
 def check(ok,issue,detail=None):
  if not ok:errors.append({'issue':issue,'detail':detail})
 cs=properties(d['Components6/Data']);ns=properties(d['Nets6/Data']);ps=pads_stream(d['Pads6/Data']);b=properties(d['Board6/Data'])[0];cd={c['SOURCEDESIGNATOR']:c for c in cs}
 owned=[p for p in ps if p['component']!=65535];mounts=[p for p in ps if p['component']==65535]
 pins={cs[p['component']]['SOURCEDESIGNATOR']+'-'+p['number']:p for p in owned}
 actual={key:None if p['net']==65535 else ns[p['net']]['NAME'] for key,p in pins.items()};expected={**e['pin_net_map'],**{k:None for k in e['nc_pins']}}
 check(actual==expected,'pin_net_map_mismatch',{k:[actual.get(k),expected.get(k)] for k in set(actual)|set(expected) if actual.get(k)!=expected.get(k)})
 check((len(cs),len(ps),len(owned),len(mounts),len(ns))==(16,129,123,6,33),'component_pad_net_counts',[len(cs),len(ps),len(owned),len(mounts),len(ns)])
 check(len(pins)==123,'duplicate_component_pin_keys')
 check({c['SOURCEDESIGNATOR']:c.get('SOURCEUNIQUEID','').strip('\\') for c in cs}==e['component_uids'],'schematic_component_UID_mismatch')
 check({c['SOURCEDESIGNATOR']:c['PATTERN'] for c in cs}==e['component_models'],'schematic_footprint_model_mismatch')
 q=[p for key,p in pins.items() if key.startswith('Q1-')]
 check(len(q)==24 and {p['number'] for p in q}=={str(i) for i in range(1,25)},'QD_pin_numbers')
 bottom=[p for key,p in pins.items() if key.startswith(('Q1-','R','C'))]
 check(all(p['layer']==32 and u32(p['blocks'][4],114)==0x0100ffff for p in bottom),'QD_RC_pad_true_bottom')
 check(cd['Q1']['LAYER']=='BOTTOM' and angle_error(float(cd['Q1']['ROTATION']),0)<1e-6,'QD_component_rotation0_bottom')
 check(all(abs(p['coords'][2]*UNIT-.5)<3e-6 and abs(p['coords'][3]*UNIT-.5)<3e-6 for p in q),'QD_pad_half_mm_size')
 geometry_differences=[]
 for c in g['components']:
  a=cd.get(c['designator'])
  if not a or max(abs(mm(a[k.upper()])-c[k]) for k in ['x','y'])>3*UNIT or a['LAYER']!=c['side'] or angle_error(float(a['ROTATION']),c['rotation'])>1e-6:geometry_differences.append({'component':c['designator'],'actual':a,'expected':c})
 for p in g['pads']:
  if p['component'].startswith('MH'):continue
  key=p['component']+'-'+p['number'];a=pins[key];vals=[x*UNIT for x in a['coords']]
  exp=[p['x'],p['y'],p['size_x'],p['size_y']];delta=max(abs(x-y) for x,y in zip(vals[:4],exp))
  if delta>3*UNIT or abs(vals[8]-p['hole'])>3*UNIT or a['layer']!=p['layer'] or angle_error(a['rotation'],p['rotation'])>1e-6:geometry_differences.append({'pin':key,'maximum_mm_error':delta,'layer':a['layer'],'expected_layer':p['layer']})
 check(not geometry_differences,'placement_or_pad_geometry_mismatch',geometry_differences)
 mh_report=[]
 for m in ref['mechanical_pads']:
  a=min(mounts,key=lambda p:math.dist([v*UNIT for v in p['coords'][:2]],pair(m)));vals=[v*UNIT for v in a['coords']]
  ok=max(abs(x-y) for x,y in zip([*vals[:4],vals[8]],[m['x'],m['y'],m['size_x'],m['size_y'],m['hole']]))<=3*UNIT and a['layer']==74 and a['number']=='1' and a['net']!=65535 and ns[a['net']]['NAME']=='GND'
  mh_report.append({'hole':m['mechanical_id'],'native_pad_index':a['index'],'matches':ok,'coords_size_hole_mm':[*vals[:4],vals[8]]})
 check(all(x['matches'] for x in mh_report) and len({x['native_pad_index'] for x in mh_report})==6,'mechanical_holes_reference_mismatch',mh_report)
 smp_report=[]
 for s in ref['smp_components']:
  if s['designator'] not in ['SMP1','SMP2','SMP3','SMP4','SMP7','SMP8']:continue
  c=cd[s['designator']];ok=c['LAYER']=='TOP' and max(abs(mm(c[k.upper()])-s[k]) for k in ['x','y'])<3*UNIT and angle_error(float(c['ROTATION']),s['rotation'])<1e-6
  for pp in s['pads']:
   a=pins[s['designator']+'-'+pp['number']];vals=[v*UNIT for v in a['coords']]
   ok=ok and max(abs(x-y) for x,y in zip([*vals[:4],vals[8]],[pp['x'],pp['y'],pp['size_x'],pp['size_y'],pp['hole']]))<3*UNIT
  smp_report.append({'component':s['designator'],'matches_reference_XY_orientation_pads':ok})
 check(len(smp_report)==6 and all(x['matches_reference_XY_orientation_pads'] for x in smp_report),'six_SMP_reference_geometry',smp_report)
 idx=sorted({int(m[1]) for k in b if (m:=re.match(r'V9_STACK_LAYER(\d+)_COPTHICK$',k))})
 stack=[{'name':b.get(f'V9_STACK_LAYER{i}_NAME'),'V7_id':int(b[f'V9_STACK_LAYER{i}_LAYERID']),'copper_mm':mm(b[f'V9_STACK_LAYER{i}_COPTHICK'])} for i in idx]
 check([s['V7_id'] for s in stack]==[0x01000001,0x01000002,0x01000003,0x01000004,0x01000005,0x0100ffff],'active_copper_stack_not_six',stack)
 diel=[{'name':b[f'V9_STACK_LAYER{i}_NAME'],'thickness_mm':mm(b[f'V9_STACK_LAYER{i}_DIELHEIGHT']),'Dk':float(b[f'V9_STACK_LAYER{i}_DIELCONST'])} for i in range(50) if b.get(f'V9_STACK_LAYER{i}_NAME','').startswith('Dielectric')]
 check(len(diel)==5,'dielectric_count_not_five')
 xx=[mm(v) for k,v in b.items() if re.fullmatch('VX[0-9]+',k)];yy=[mm(v) for k,v in b.items() if re.fullmatch('VY[0-9]+',k)];outline=[max(xx)-min(xx),max(yy)-min(yy)]
 check(abs(outline[0]-19.5)<3*UNIT and abs(outline[1]-67.9)<3*UNIT,'board_outline_size',outline)
 tracks,arcs,vias=read_route(d,ns);route_diffs={}
 for key,aa,ee,fn in [('tracks',tracks,plan['tracks'],trackkey),('arcs',arcs,plan['arcs'],arckey),('vias',vias,plan['vias'],viakey)]:
  ac=collections.Counter(fn(x) for x in aa);ec=collections.Counter(fn(x) for x in ee);route_diffs[key]={'actual':len(aa),'expected':len(ee),'missing':sum((ec-ac).values()),'extra':sum((ac-ec).values())};check(ac==ec,'native_'+key+'_differ_from_validated_plan',route_diffs[key])
 check(all(t['V7']==(0x0100ffff if t['layer']==32 else 0x01000000+t['layer']) for t in tracks+arcs),'wrong_V7_routing_layer_or_phantom')
 check(sum(t['layer']==32 for t in tracks)==24,'QD_true_bottom_stub_count',sum(t['layer']==32 for t in tracks))
 badlayers=[{'kind':kind,'index':p['index'],'net':p['net'],'layer':p['layer']} for kind,rr in [('track',tracks),('arc',arcs)] for p in rr if p['net']!='GND' and ((p['net'].startswith('ZIF') and p['layer'] not in (1,2,32)) or (p['net'].startswith(('MW','S')) and p['layer'] not in (4,32)))]
 check(not badlayers,'signal_main_layers',badlayers)
 keep=box(*g['qd_signal_keepout']);interior=[]
 for t in tracks:
  if t['net']!='GND' and LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2).intersects(keep):interior.append(['track',t['index'],t['net']])
 for a in arcs:
  p=Arc((a['cx'],a['cy']),a['radius'],a['start_angle'],(a['end_angle']-a['start_angle'])%360 or 360,a['layer'],a['width'],a['net'])
  if a['net']!='GND' and copper_geometry(p,.00001).intersects(keep):interior.append(['arc',a['index'],a['net']])
 check(not interior,'QD_interior_signal_crossings',interior)
 vip=[]
 for key,p in pins.items():
  if not key.startswith(('R','C')):continue
  vv=[v for v in vias if v['net']==actual[key] and max(abs(v['native_coords'][i]-p['coords'][i]) for i in (0,1))<=1]
  delta=[vv[0]['native_coords'][i]-p['coords'][i] for i in (0,1)] if len(vv)==1 else None
  good=len(vv)==1 and abs(vv[0]['diameter']-.5)<UNIT and abs(vv[0]['hole']-.25)<UNIT
  vip.append(dict(pin=key,passed=good,center_delta_native_grid=delta,exact_native_integer_center=delta==[0,0]))
 check(len(vip)==16 and all(v['passed'] for v in vip),'RC_all16_via_in_pad',vip)
 rules=read_rules(d['Rules6/Data']);rd={r['RULEKIND']:r for r in rules}
 values={}
 for kind,field,label,value in [('SolderMaskExpansion','EXPANSION','global_mask_expansion_mm',.05),('MinimumSolderMaskSliver','MINSOLDERMASKWIDTH','mask_min_web_mm',.1),('SilkToSolderMaskClearance','MINSILKSCREENTOMASKGAP','silk_mask_mm',.15),('SilkToSilkClearance','SILKTOSILKCLEARANCE','silk_silk_mm',.254),('NetAntennae','NETANTENNAETOLERANCE','antenna_mm',0)]:
  values[label]=mm(rd[kind][field]);check(abs(values[label]-value)<3*UNIT,'rule_'+label,values[label])
 masks={}
 for designator in ['Q1','J1']:
  group=[p for key,p in pins.items() if key.startswith(designator+'-')]
  ok=all(p['blocks'][4][102]==2 and struct.unpack_from('<i',p['blocks'][4],90)[0]==0 and struct.unpack_from('<i',p['blocks'][4],121)[0]==0 for p in group)
  masks[designator]={'count':len(group),'all_native_manual_zero_both':ok};check(ok,'manual_zero_mask_'+designator)
 vm=[dict(index=v['index'],valid=v['body'][66],top_mm=struct.unpack_from('<i',v['body'],54)[0]*UNIT,bottom_mm=struct.unpack_from('<i',v['body'],242)[0]*UNIT) for v in vias]
 vmok=all(x['valid']==2 and abs(x['top_mm']-.025)<3*UNIT and abs(x['bottom_mm']-.025)<3*UNIT for x in vm)
 masks['vias']={'count':len(vm),'all_native_manual025_both':vmok,'configurations':list({(v['valid'],v['top_mm'],v['bottom_mm']) for v in vm})};check(vmok,'via_native_mask_overrides')
 regions=read_regions(d['Regions6/Data']);paste=paste_audit(regions,vias);check(paste['passed'],'explicit_via_paste_geometry',paste)
 polygons=properties(d['Polygons6/Data']);solid=solid_audit(regions,polygons,ns,vias,rules)
 check(solid['dominant_solid_rule_verified'],'GND_via_solid_dominant_rule')
 check(len(solid['ground_polygons'])==4 and {p['layer'] for p in solid['ground_polygons']}=={'TOP','MID2','MID4','BOTTOM'},'four_GND_polygons')
 check(all(p['child_regions']>0 for p in solid['ground_polygons']),'GND_polygons_not_poured')
 if solid['partial_count']:warnings.append({'issue':'partial_GND_via_copper_rings_review_required','count':solid['partial_count']})
 if solid['inner_ring_partial_count']:warnings.append({'issue':'GND_via_inside_land_annulus_not_full_review_required','count':solid['inner_ring_partial_count']})
 ground=[v for v in vias if v['net']=='GND'];pitch=min((math.dist(pair(v),pair(w)) for i,v in enumerate(ground) for w in ground[:i]),default=None)
 check(pitch is None or pitch>=.455-3*UNIT,'GND_pair_pitch_for_mask_web',pitch)
 refs=dict(e.get('source_hashes',{}));build=load(HERE/'build_report.json');refs[build['source']]=build['source_sha256']
 refresult=[{'file':f,'expected_sha256':h,'actual_sha256':sha(f) if Path(f).exists() else None,'unchanged':Path(f).exists() and sha(f)==h} for f,h in refs.items()]
 check(all(r['unchanged'] for r in refresult),'source_reference_modified',refresult)
 drcfiles=sorted(pcb.parent.glob('*DRC*.html'),key=lambda p:p.stat().st_mtime,reverse=True);drc=None
 if drcfiles:
  hp=drcfiles[0];text=hp.read_text(encoding='utf8',errors='replace');lines=[re.sub(r'\s+',' ',s).strip() for s in html.unescape(re.sub('<[^>]*>',' ',text)).splitlines()]
  prefixes=['Un-Routed Net Constraint:','Clearance Constraint:','Short-Circuit Constraint:','Minimum Solder Mask Sliver Constraint:','Silk To Solder Mask Clearance Constraint:','Silk To Silk Clearance Constraint:','Net Antennae:']
  drc={'file':str(hp),'sha256':sha(hp),'counts':{p:sum(l.startswith(p) for l in lines) for p in prefixes}}
 after={str(p.resolve()):sha(p) for p in required};check(hashes==after,'inputs_changed_during_read')
 report={'passed':not errors,'scope':'Cold native V2 metadata,129pads/123schematicpins+6mounts, frozen route equality, physical paste and poured GND region audit; latest native DRC separately reported.','pcb':str(pcb),'pcb_sha256':hashes[str(pcb.resolve())],'input_hashes':hashes,'inputs_unchanged':hashes==after,'counts':{'components':len(cs),'pads':len(ps),'owned_pads':len(owned),'standalone_mounts':len(mounts),'nets':len(ns),'NC_pads':sum(v is None for v in actual.values()),'tracks':len(tracks),'arcs':len(arcs),'vias':len(vias),'GND_vias':len(ground)},'pin_net_map_all123_matches_schematic':actual==expected,'QD':{'bottom_pads':len(q),'rotation':float(cd['Q1']['ROTATION']),'center_mm':[mm(cd['Q1']['X']),mm(cd['Q1']['Y'])]},'RC_via_in_pad':vip,'placement_differences':geometry_differences,'SMP_reference':smp_report,'mechanical_holes':mh_report,'copper_stack':stack,'dielectrics':diel,'outline_mm':outline,'route_geometry_comparison':route_diffs,'signal_main_layer_errors':badlayers,'QD_interior_crossings':interior,'rule_values':values,'native_direct_mask':masks,'explicit_paste':paste,'GND_solid_connection':solid,'minimum_GND_candidate_pitch_mm':pitch,'references':refresult,'latest_DRC':drc,'warnings':warnings,'errors':errors}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf8')
 print(json.dumps({k:report[k] for k in ['passed','pcb_sha256','counts','route_geometry_comparison','warnings','errors']},indent=2));return report

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--pcb',type=Path,default=DEFAULT_PCB);ap.add_argument('--plan',type=Path,default=HERE/'merged_routes.json');ap.add_argument('--expected',type=Path,default=HERE.parent/'schematic/v2_expected_netlist.json');ap.add_argument('--out',type=Path,default=HERE/'final_native_cold_qa_v2.json');args=ap.parse_args()
 try:r=verify(args.pcb,args.plan,args.expected,args.out)
 except (FileNotFoundError,AssertionError) as exc:print('VALIDATION BLOCKED: '+str(exc));raise SystemExit(2)
 raise SystemExit(0 if r['passed'] else 1)
