from pathlib import Path
import json,sys,math,hashlib,shutil,copy
H=Path(__file__).resolve().parent;W=H.parent;OLD=W/'dc_centered_20260920'
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
sys.path.insert(0,str(W/'route_python'))
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
U=2.54e-6;WIDTH=.125
if not (H/'baseline_native.json').exists():
 assert hashlib.sha256((P/(B+'.PcbDoc')).read_bytes()).hexdigest()=='e556160f4f050d894eca14f4d2ce82f582a142e3eb89270b7ad0280965fb1d67'
 for ext in ['.PcbDoc','.SchDoc','.PrjPcb','.PcbLib','.SchLib']:shutil.copy2(P/(B+ext),H/(B+ext))
 for f in ['native_render_snapshot.json','geometry.json','expected.json','validator_source.py','rf_routes.json']:shutil.copy2(OLD/f,H/('baseline_native.json' if f=='native_render_snapshot.json' else f))
 shutil.copy2(P.parent/'README.md',H/'README.before.md')
n=json.loads((H/'baseline_native.json').read_text());old=json.loads((OLD/'dc_routes.json').read_text())
src=(W/'rf_stubless_20260920/plan_routes.py').read_text();exec(src[src.index('def xy'):src.index('prefix={}')])
def split(ps,y):
 for i,(a,b) in enumerate(zip(ps,ps[1:])):
  if a[1]<=y<b[1]+1e-7 and b[1]>a[1]:
   f=(y-a[1])/(b[1]-a[1]);p=(a[0]+f*(b[0]-a[0]),y)
   return ps[:i+1]+[p],[p]+ps[i+1:]
 raise ValueError((ps,y))
op={(p['net'],p['layer']):p['points'] for p in old['paths']}
ends={p['component']+'-'+p['number']:p for p in n['pads'] if p['component']}
targets=copy.deepcopy(old['zif_to_target']);targets.update({'17':'Q1-3','19':'Q1-2','21':'R1-2'})
changes={target:dict(old=ends[target]['net'],new=f'ZIF{int(k):02d}') for k,target in targets.items() if ends[target]['net']!=f'ZIF{int(k):02d}'}
for key,c in changes.items():
 p=ends[key]
 for v in n['vias']:
  if math.dist(xy(p),xy(v))<4*U:assert v['net']==c['old'];v['net']=c['new']
 p['net']=c['new']
paths=[]
def addpath(net,layer,pts):paths.append(dict(net=net,layer=layer,points=chamfer(pts,.22)))
bus=old['central_bus'];main2=bus['L2'];main4=bus['L4'];lane={f'ZIF{k:02d}':(layer,6.15+.6*i) for layer,ids in [(2,main2),(4,main4)] for i,k in enumerate(ids)}
# Keep verified ZIF escape geometry. Through-vias obstruct both layers; traces on different layers do not.
for k in main2[:10]:
 net=f'ZIF{k:02d}';prefix,_=split(op[net,2],24);x=lane[net][1];p=ends[targets[str(k)]]
 if k in main2[:7]:
  _,suffix=split(op[net,2],39);tx=suffix[0][0]
  addpath(net,2,prefix+[(x,35.1),(tx,35.1+x-tx)]+suffix)
 else:addpath(net,2,prefix+[(x,35.1),(p['x'],35.1+x-p['x']),xy(p)])
for net,layer in [('ZIF25',2),('ZIF23',4),('ZIF23',2)]:addpath(net,layer,op[net,layer])
for k in main4:
 net=f'ZIF{k:02d}';prefix,_=split(op[net,4],24);x=lane[net][1];p=ends[targets[str(k)]]
 if k==2:
  pts=prefix+[(x,35.1),(6.45,35.1+6.45-x),(6.45,p['y']-(6.45-p['x'])),xy(p)]
 elif k==21:
  pts=prefix+[(x,p['y']-(p['x']-x)),xy(p)]
 elif k in [26,1,3,5]:
  pts=prefix+[(x,35.1),(p['x'],35.1+p['x']-x),xy(p)]
 else:
  oldnet=next(f'ZIF{int(z):02d}' for z,t in old['zif_to_target'].items() if t==targets[str(k)])
  _,suffix=split(op[oldnet,4],39);tx=suffix[0][0]
  pts=prefix+[(x,35.1),(tx,35.1+tx-x)]+suffix
 addpath(net,4,pts)
tracks=[]
for route in paths:
 route['points']=reduce([tuple(quant(v) for v in p) for p in route['points']])
 for a,b in zip(route['points'],route['points'][1:]):
  dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1]);assert min(dx,dy,abs(dx-dy))<8*U,(route['net'],a,b)
  tracks.append(dict(net=route['net'],layer=route['layer'],x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=WIDTH))
def shape(p):
 if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(*xy(p)).buffer(p['size_x']/2,quad_segs=64)
 return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),p['rotation'],origin=(0,0)),*xy(p))
geoms=[LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in tracks]
obstacles=[(p['net'],str(p['component'])+'-'+p['number'],shape(p)) for p in n['pads'] if p['hole']]
obstacles += [(v['net'],'via@'+str(tuple(round(x,2) for x in xy(v))),Point(*xy(v)).buffer(v['diameter']/2,quad_segs=64)) for v in n['vias']]
errors=[];minimum={'track_track':99.,'track_via_or_TH_pad':99.}
for i,t in enumerate(tracks):
 if geoms[i].distance(box(7.6,40.35,11.9,44.65))<WIDTH/2:errors.append(['QD',i,t['net']])
 for j,u in enumerate(tracks[:i]):
  if t['net']==u['net'] or t['layer']!=u['layer']:continue
  gap=geoms[i].distance(geoms[j])-WIDTH;minimum['track_track']=min(minimum['track_track'],gap)
  if gap<.15-8*U:errors.append(['track',i,j,t['net'],u['net'],round(gap,6)])
 for onet,label,g in obstacles:
  if onet==t['net']:continue
  gap=geoms[i].distance(g)-WIDTH/2;minimum['track_via_or_TH_pad']=min(minimum['track_via_or_TH_pad'],gap)
  if gap<.15-8*U:errors.append(['obstacle',i,t['net'],label,round(gap,6)])
out=dict(tracks=tracks,arcs=[],paths=paths,added_vias=[],retained_transition_vias=old['added_vias'],zif_to_target=targets,pin_changes=changes,rf_qd_map=old['rf_qd_map'],validation=dict(errors=errors,minimum_clearances_mm=minimum),central_bus=dict(bus,y_max=30),unrouted=[])
(H/'dc_candidate.json').write_text(json.dumps(out,indent=2))
print(json.dumps(dict(tracks=len(tracks),errors=len(errors),first_errors=errors[:40],minimum=minimum,changes=changes),indent=2))
if not errors:(H/'dc_routes.json').write_text(json.dumps(out,indent=2))
