"""Reassign the existing 24 DC trunks to physical even ZIF contacts 2..48."""
from pathlib import Path
import json,copy,math,sys,importlib.util
from shapely.geometry import Point,LineString,box,Polygon,mapping,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';U=2.54e-6
n=json.loads((H/'before_native.json').read_text());new=copy.deepcopy(n);snap=lambda v:round(v/U)*U
trunks={}
for layer in (2,4):
 ts=[t for t in n['tracks'] if t['layer']==layer and t['net'].startswith('ZIF') and min(t['y1'],t['y2'])<20<max(t['y1'],t['y2'])]
 assert len(ts)==12 and all(abs(t['x1']-t['x2'])<4*U for t in ts)
 trunks[layer]=sorted(ts,key=lambda t:t['x1'])
rename={t['net']:f'ZIF{4*i+(2 if layer==2 else 4):02d}' for layer,ts in trunks.items() for i,t in enumerate(ts)}
assert set(rename.values())=={f'ZIF{i:02d}' for i in range(2,49,2)}
# Keep every upper DC trunk and RF primitive exactly, except DC net names.
new['tracks']=[]
for old in n['tracks']:
 t=copy.deepcopy(old)
 if t['net'] not in rename:new['tracks'].append(t);continue
 if max(t['y1'],t['y2'])<=20:continue
 assert t['layer'] in (2,4)
 for k in (1,2):
  if t[f'y{k}']<20:t[f'y{k}']=snap(20)
 t['net']=rename[t['net']];new['tracks'].append(t)
for p in new['pads']:
 if p['component']=='J1':p['net']=f'ZIF{int(p["number"]):02d}' if int(p['number']) in range(2,49,2) else None
 elif p['net'] in rename:p['net']=rename[p['net']]
fanouts=[];adds=[]
for layer,ts in trunks.items():
 for t in ts:
  net=rename[t['net']];p=next(p for p in new['pads'] if p['component']=='J1' and p['net']==net)
  v=next(v for v in new['vias'] if v['net']==t['net'] and v['y']<10)
  v['x']=p['x'];v['y']=snap(7.3 if layer==2 else 8.1)
  x,y,tx=v['x'],v['y'],t['x1'];start=snap(9.1)
  fanouts.append(dict(old_net=t['net'],net=net,pin=p['number'],layer=layer,x=x,y=y,trunk_x=tx))
  paths=[(1,[(p['x'],p['y']),(x,y)],.15),(layer,[(x,y),(x,start),(tx,snap(start+abs(tx-x))),(tx,snap(20))],.125)]
  for l,pts,w in paths:
   pts=[z for i,z in enumerate(pts) if i==0 or math.dist(z,pts[i-1])>U]
   for a,b in zip(pts,pts[1:]):adds.append(dict(net=net,layer=l,native_layer_code=0x1000000+l,x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=snap(w)))
for v in new['vias']:
 if v['net'] in rename:v['net']=rename[v['net']]
new['tracks']+=adds
# Independently check same-layer tracks against tracks and all through-hole obstacles.
tracks=new['tracks'];geoms=[LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in tracks];errors=[];mins={'track_track':99.,'track_via':99.,'track_mount':99.}
obs=[(v['net'],'via',Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64),{5,32} if v['net']=='GND' else {1,2,3,4,5,32}) for v in new['vias']]
obs +=[(p['net'],'mount',Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=128),{1,2,3,4,5,32}) for p in new['pads'] if p['hole']]
for i,t in enumerate(tracks):
 if t['net'] not in rename.values():continue
 dx,dy=abs(t['x1']-t['x2']),abs(t['y1']-t['y2']);assert min(dx,dy,abs(dx-dy))<8*U
 for j,s in enumerate(tracks):
  if j>=i or t['net']==s['net'] or t['layer']!=s['layer']:continue
  gap=geoms[i].distance(geoms[j])-(t['width']+s['width'])/2;mins['track_track']=min(mins['track_track'],gap)
  if gap<.15-8*U:errors.append(['track',i,j,t['net'],s['net'],gap])
 for net,kind,g,layers in obs:
  if net==t['net'] or t['layer'] not in layers:continue
  gap=geoms[i].distance(g)-t['width']/2;mins['track_'+kind]=min(mins['track_'+kind],gap)
  if gap<.15-8*U:errors.append([kind,i,t['net'],net,gap])
vs=[v for v in new['vias'] if v['y']<10]
minvia=min(math.dist((v['x'],v['y']),(u['x'],u['y']))-(v['diameter']+u['diameter'])/2 for i,v in enumerate(vs) for u in vs[:i]);assert minvia>=.15-8*U
print(json.dumps(dict(errors=errors[:40],count=len(errors),minimum=mins,via_min=minvia,mapping=rename),indent=2))
(H/'preflight.json').write_text(json.dumps(dict(passed=not errors,errors=errors,minimum_mm=mins,via_minimum_mm=minvia),indent=2));assert not errors
plan=json.loads((H.parent/'lower_rc_70pct_20260921/plan.json').read_text())
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board')]
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
rs=read_regions(snapshot(H/'before.PcbDoc')['Regions6/Data']);extent=box(-.05,-.05,19.55,67.95);edit=box(-.1,-.1,19.6,10.0)
viaenv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vs]);a,b,c,d=viaenv.bounds;bottomrect=box(a-.4,b-.4,c+.4,d+.4)
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
zifenv=unary_union([viaenv]+[Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])) for p in new['pads'] if p['component']=='J1']);a,b,c,d=zifenv.bounds;toprect=box(a-.3,b-.3,c+.3,d+.3)
openings={}
for layer,rect in [(37,toprect),(38,bottomrect)]:
 old=unary_union([r['geometry'] for r in rs if r['layer']==layer and r['name'].startswith('SURFACE_MASK_OPEN_')]);openings[layer]=unary_union([old.difference(edit),extent.intersection(edit).difference(rect)]).simplify(.00005,preserve_topology=True)
plan.update(source_sha256=n['source_sha256'],rename=rename,fanouts=fanouts,component_y_moves_mm={},component_x_moves_mm={},pad_component_moves=[],ZIF_bottom_mask_rectangle=mapping(bottomrect),ZIF_top_mask_rectangle=mapping(toprect),Top_mask_opening=mapping(openings[37]),Bottom_mask_opening=mapping(openings[38]),description='24 DC nets use physical J1 contacts 2..48 even; pin50 and all odd pins NC; no extra DC transition vias')
(H/'plan.json').write_text(json.dumps(plan,indent=2));(H/'planned_native.json').write_text(json.dumps(new,indent=2))
