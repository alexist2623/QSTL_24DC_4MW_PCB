from pathlib import Path
import sys,json,math,copy,collections,itertools
H=Path(__file__).resolve().parent;W=H.parent
sys.path[:0]=[str(W/'route_python'),str(W/'rf_revision')]
from shapely.geometry import Point,LineString,box
from shapely.ops import linemerge
from shapely.affinity import rotate,translate
from geometry_helpers import fillet_polyline,copper_geometry,primitive_to_altium_dict,validate_path,path_length
U=2.54e-6
G=json.loads((H/'geometry.json').read_text());V=G['endpoints'];P={p['component']+'-'+p['number']:p for p in G['pads']};base=json.loads((H/'baseline_routes.json').read_text())
G['rf_qd_map']={'1':9,'2':6,'3':1,'4':24}
def xy(v):return v['x'],v['y']
def quant(x):return round(x/U)*U
def sub(a,b):return a[0]-b[0],a[1]-b[1]
def scale(a,k):return a[0]*k,a[1]*k
def add(a,b):return a[0]+b[0],a[1]+b[1]
def unit(a):return scale(a,1/math.hypot(*a))
def cross(a,b):return a[0]*b[1]-a[1]*b[0]
def reduce(pts):
 out=[]
 for p in pts:
  if out and math.dist(p,out[-1])<4*U:continue
  while len(out)>1 and abs(cross(unit(sub(out[-1],out[-2])),unit(sub(p,out[-1]))))<2e-5 and sum(a*b for a,b in zip(sub(out[-1],out[-2]),sub(p,out[-1])))>0:out.pop()
  out.append(p)
 return out
def chamfer(points,cut):
 pts=reduce(points);out=[pts[0]]
 for a,b,c in zip(pts,pts[1:],pts[2:]):
  u,v=unit(sub(b,a)),unit(sub(c,b));turn=math.degrees(math.atan2(cross(u,v),sum(x*y for x,y in zip(u,v))))
  if abs(turn)<45.01:out.append(b);continue
  assert abs(abs(turn)-90)<.01 or abs(abs(turn)-135)<.01,turn
  d=min(cut,math.dist(a,b)*.44,math.dist(b,c)*.44)
  p=add(b,scale(u,-d));q=add(b,scale(v,d));out.append(p)
  if abs(turn)>100:
   aa=math.atan2(u[1],u[0])+math.copysign(math.pi/4,turn);bb=aa+math.copysign(math.pi/4,turn)
   u1=(math.cos(aa),math.sin(aa));u2=(math.cos(bb),math.sin(bb));delta=sub(q,p)
   k=cross(delta,u2)/cross(u1,u2);out.append(add(p,scale(u1,k)))
  out.append(q)
 out.append(pts[-1]);return reduce(out)
prefix={};crossings={}
for n in sorted({t['net'] for t in base['tracks'] if t['layer']==2}):
 lines=[]
 for t in base['tracks']:
  if t['layer']!=2 or t['net']!=n:continue
  a=(t['x1'],t['y1']);b=(t['x2'],t['y2'])
  if min(a[1],b[1])>=22:continue
  if max(a[1],b[1])>22:
   f=(22-a[1])/(b[1]-a[1]);c=(a[0]+f*(b[0]-a[0]),22.)
   if a[1]>22:a=c
   else:b=c
   crossings[n]=c
  lines.append(LineString([a,b]))
 line=linemerge(lines);assert line.geom_type=='LineString',n
 pts=list(line.coords)
 if pts[0][1]>pts[-1][1]:pts.reverse()
 prefix[n]=pts
sources=sorted(crossings,key=lambda n:crossings[n][0]);assert len(sources)==24
targets=['R4-2','Q1-23','Q1-22','Q1-21','Q1-20','Q1-19','Q1-18','Q1-17','Q1-16','Q1-15','Q1-14','Q1-13','Q1-12','Q1-11','Q1-10','Q1-8','Q1-7','Q1-5','Q1-4','R1-2','Q1-3','Q1-2','R2-2','R3-2']
mapping={str(int(n[3:])):targets[i] for i,n in enumerate(sources)}
PN={p['component']+'-'+p['number']:p['net'] for p in G['pads'] if not p['component'].startswith('MOUNT')}
PN.update({target:n for n,target in zip(sources,targets)})
for ch,pin in G['rf_qd_map'].items():PN['Q1-'+str(pin)]='MW'+ch
for p in G['pads']:
 key=p['component']+'-'+p['number']
 if key in PN:p['net']=PN[key]
for v in G['fanout_vias']:v['net']=PN[v['pin']]
for v in G['via_moves']:v['net']=PN[v['pin']]
G['endpoints']={v['pin']:v for v in G['fanout_vias']};V=G['endpoints']
G['pin_nets']=PN
paths={};feeds={}
for i,n in enumerate(sources):
 x={0:.72,19:12.30,20:12.825,21:13.2,22:13.65,23:14.1}.get(i,5.2+.31*(i-1))
 sy=22.4 if i==0 else 22.5+.3*(i if x<crossings[n][0] else 23-i)
 y={19:27.35,20:27.9,21:27.35,22:24.9,23:24.6}.get(i,28.)
 feeds[i]=(x,y);paths[i]=prefix[n]+[(crossings[n][0],sy),(x,sy),(x,y)]
def tail(i,pts):paths[i].extend(pts)
tail(0,[(.72,45.45),(5.35,45.45),(5.35,47.4),xy(V['R4-2'])])
for i in range(1,8):
 x=3.85+.4*(i-1);t=V[targets[i]];tail(i,[(feeds[i][0],36.9+.15*(i-1)),(x,36.9+.15*(i-1)+feeds[i][0]-x),(x,t['y']),xy(t)])
for i in range(8,15):
 t=V[targets[i]];sx,sy=feeds[i]
 if i==8:tail(i,[(sx,38.85),(t['x'],38.85+abs(t['x']-sx)),xy(t)])
 else:tail(i,[(sx,32.-.2*(i-8)),(t['x'],32.-.2*(i-8)+abs(t['x']-sx)),xy(t)])
right=[15,16,17,18,20,21]
for j,i in enumerate(right):
 lane=11.9+.4*j;outer=12.9+.4*j;t=V[targets[i]]
 if j<4:
  sx,sy=feeds[i];tail(i,[(sx,29.8-.2*j),(lane,29.8-.2*j+lane-sx),(lane,36.2)])
 elif j==4:tail(i,[(13.15,28.225),(13.15,30.52),(14.18,31.55),(14.18,32.03),(lane,32.71),(lane,36.2)])
 else:tail(i,[(14.15,28.30),(14.15,30.90),(14.55,31.30),(14.55,32.05),(lane,32.70),(lane,36.2)])
 tail(i,[(outer,37.2),(outer,t['y']),xy(t)])
tail(19,[(12.30,30.35),(V['R1-2']['x'],30.35+V['R1-2']['x']-12.30),xy(V['R1-2'])])
tail(22,[(18.55,24.9),(18.55,V['R2-2']['y']),xy(V['R2-2'])])
tail(23,[(19.0,24.6),(19.0,45.45),(14.15,45.45),(14.15,47.4),xy(V['R3-2'])])
def padshape(p):
 if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(*xy(p)).buffer(p['size_x']/2,resolution=48)
 return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),p['rotation'],origin=(0,0)),*xy(p))
def check_dc(tracks):
 geoms=[LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]) for t in tracks];errors=[];mini={'track_track':99.,'track_via':99.,'track_TH_pad':99.}
 for i,t in enumerate(tracks):
  if geoms[i].distance(box(*G['qd_signal_keepout']))<t['width']/2-4*U:errors.append(['QD',i,t['net']])
  for j,u in enumerate(tracks[:i]):
   if t['net']==u['net']:continue
   gap=geoms[i].distance(geoms[j])-(t['width']+u['width'])/2;mini['track_track']=min(mini['track_track'],gap)
   if gap<.15-4*U:errors.append(['track_track',i,j,t['net'],u['net'],gap])
  for v in G['fanout_vias']:
   if t['net']==v['net']:continue
   gap=geoms[i].distance(Point(*xy(v)))-t['width']/2-v['diameter']/2;mini['track_via']=min(mini['track_via'],gap)
   if gap<.15-4*U:errors.append(['track_via',i,t['net'],v['pin'],gap])
  for p in G['pads']:
   if not p['hole'] or p['net']==t['net']:continue
   gap=geoms[i].distance(padshape(p))-t['width']/2;mini['track_TH_pad']=min(mini['track_TH_pad'],gap)
   if gap<.15-4*U:errors.append(['track_TH_pad',i,t['net'],p['component']+'-'+p['number'],gap])
 return dict(errors=errors,minimum_clearances_mm=mini)
def tracks_from_paths(paths,cut):
 ts=[];newpaths={}
 for i,pts in paths.items():
  pts=chamfer(pts,cut);pts=[tuple(quant(x) for x in p) for p in pts];pts=reduce(pts);newpaths[sources[i]]=pts
  for a,b in zip(pts,pts[1:]):
   dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1]);assert min(dx,dy,abs(dx-dy))<6*U,(sources[i],a,b)
   ts.append(dict(net=sources[i],layer=2,x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=.125))
 return ts,newpaths
if __name__=='__main__':
 ts,npaths=tracks_from_paths(paths,float(sys.argv[1]) if len(sys.argv)>1 else .25);valid=check_dc(ts)
 out=dict(tracks=ts,arcs=[],paths=npaths,zif_to_target=mapping,rf_qd_map=G['rf_qd_map'],validation=valid,unrouted=[],source_order=sources)
 (H/'dc_candidate.json').write_text(json.dumps(out,indent=2));(H/'geometry.json').write_text(json.dumps(G,indent=2))
 print(json.dumps(dict(tracks=len(ts),errors=len(valid['errors']),first_errors=valid['errors'][:35],minimum_clearances=valid['minimum_clearances_mm']),indent=2))
 if not valid['errors']:(H/'dc_routes.json').write_text(json.dumps(out,indent=2))
