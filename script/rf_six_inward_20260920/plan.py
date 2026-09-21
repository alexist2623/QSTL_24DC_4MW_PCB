from pathlib import Path
import sys,json,math,copy,shutil,hashlib,importlib.util
H=Path(__file__).resolve().parent;W=H.parent/'_support';OLD=W/'dc_direct_20260920'
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'route_python'),str(W/'rf_revision'),str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board')]
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
from geometry_helpers import fillet_polyline,copper_geometry,primitive_to_altium_dict,validate_path,path_length
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
U=2.54e-6;WIDTH=.125;RFW=.21405524114055727
src=(W/'rf_stubless_20260920/plan_routes.py').read_text();exec(src[src.index('def xy'):src.index('prefix={}')])
if not (H/'baseline_native.json').exists():
 assert hashlib.sha256((P/(B+'.PcbDoc')).read_bytes()).hexdigest()=='59c2ace3b395442eec40b4b17efdaf443ac82efe07221971b6faa3d29ab718d9'
 for ext in ['.PcbDoc','.SchDoc','.SchLib','.PcbLib','.PrjPcb']:shutil.copy2(P/(B+ext),H/(B+ext))
 spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);reader.SOURCE=P/(B+'.PcbDoc')
 (H/'baseline_native.json').write_text(json.dumps(reader.read_native(),indent=2))
 shutil.copy2(OLD/'validator_source.py',H/'validator_source.py')
 shutil.copy2(P.parent/'README.md',H/'README.before.md')
n=json.loads((H/'baseline_native.json').read_text());g=copy.deepcopy(n)
C={c['designator']:c for c in g['components']};PD={p['component']+'-'+p['number']:p for p in g['pads'] if p['component']}
oldp={p['component']+'-'+p['number']:p for p in n['pads'] if p['component']}
old=json.loads((OLD/'dc_routes.json').read_text())
targets=copy.deepcopy(old['zif_to_target']);targets.update({'2':'R5-2','26':'R4-2','1':'Q1-13','4':'R6-2','6':'Q1-23','8':'Q1-22','10':'Q1-21','12':'Q1-20','16':'Q1-19','23':'R3-2','25':'R2-2'})
rfmap={'1':9,'2':6,'3':1,'4':24,'5':12,'6':18}
for z,target in targets.items():PD[target]['net']=f'ZIF{int(z):02d}'
for ch,pin in rfmap.items():
 for key in [f'Q1-{pin}',f'R{ch}-1',f'C{ch}-2']:PD[key]['net']='MW'+ch
 for key in [f'SMP{ch}-1',f'C{ch}-1']:PD[key]['net']='S'+ch

def move(name,angle,anchor,target):
 c=C[name];ps=[p for p in g['pads'] if p['component']==name];a=math.radians(angle-c['rotation']);co,si=math.cos(a),math.sin(a)
 rel={p['number']:(quant((p['x']-c['x'])*co-(p['y']-c['y'])*si),quant((p['x']-c['x'])*si+(p['y']-c['y'])*co)) for p in ps}
 new=tuple(quant(target[i]-rel[anchor][i]) for i in range(2)) if anchor else tuple(map(quant,target))
 for p in ps:
  p['x'],p['y']=[quant(new[i]+rel[p['number']][i]) for i in range(2)];p['rotation']=(p['rotation']+angle-c['rotation'])%360
 c.update(x=new[0],y=new[1],rotation=angle)
for ch,ang,rfpt,cpt,cang in [(1,0,(13.8,30),(13.8,28.45),90),(5,180,(5.7,30),(5.7,28.45),90),(2,0,(15.8,41.45),(15.8,39.9),90),(6,180,(3.7,40.75),(3.7,39.2),90),(3,0,(11,46.4),(11,47.95),270),(4,180,(8.5,46.4),(8.5,47.95),270)]:
 move(f'R{ch}',ang,'1',rfpt);move(f'C{ch}',cang,None,cpt)
regions=read_regions(snapshot(H/(B+'.PcbDoc'))['Regions6/Data']);vm=[];removed=[]
for v in list(g['vias']):
 p=next((p for p in n['pads'] if p['component'] and math.dist(xy(p),xy(v))<4*U),None)
 oldxy=xy(v);oldnet=v['net'];key=p['component']+'-'+p['number'] if p else None
 if p:v.update(x=PD[key]['x'],y=PD[key]['y'],net=PD[key]['net'])
 names=[r['props']['NAME'] for r in regions if r['layer'] in [35,36] and r['geometry'].centroid.distance(Point(*oldxy))<4*U]
 assert len(names)==2,(key,names)
 if not p and math.dist(oldxy,(13.35,16.4))<4*U:
  assert oldnet=='ZIF23';removed.append(dict(old=oldxy,net=oldnet,paste_names=names));g['vias'].remove(v);continue
 vm.append(dict(pin=key,old=oldxy,new=xy(v),old_net=oldnet,net=v['net'],paste_names=names))
added=[]
for ch in [5,6]:
 for ref in ['R','C']:
  for num in ['1','2']:
   p=PD[f'{ref}{ch}-{num}'];v=dict(x=p['x'],y=p['y'],net=p['net'],diameter=.5,hole=.25,pin=f'{ref}{ch}-{num}');added.append(v);g['vias'].append(v)
g.update(old_pads=n['pads'],old_components=n['components'],via_moves=vm,added_vias=added,removed_vias=removed,rf_qd_map=rfmap,zif_to_target=targets,pin_nets={k:p['net'] for k,p in PD.items()},qd_signal_keepout=[7.6,40.35,11.9,44.65])

def split(ps,y):
 for i,(a,b) in enumerate(zip(ps,ps[1:])):
  if a[1]<=y<b[1]+1e-7 and b[1]>a[1]:
   f=(y-a[1])/(b[1]-a[1]);p=(a[0]+f*(b[0]-a[0]),y);return ps[:i+1]+[p],[p]+ps[i+1:]
 raise ValueError((ps,y))
op={(p['net'],p['layer']):p['points'] for p in old['paths']};paths=[]
main2=old['central_bus']['L2'][:-2]+[23,25];main4=old['central_bus']['L4']
lanes={f'ZIF{k:02d}':(layer,6.35+.6*i) for layer,ids in [(2,main2),(4,main4)] for i,k in enumerate(ids)}
def addpath(net,layer,pts):paths.append(dict(net=net,layer=layer,points=chamfer(pts,.22)))
for layer,ids in [(2,main2),(4,main4)]:
 for k in ids:
  net=f'ZIF{k:02d}';x=lanes[net][1];p=PD[targets[str(k)]];px,py=xy(p);start=op[net,layer][0]
  if layer==2 and k in main2[:10]:prefix=[start,(start[0],9.6),(x,9.6+x-start[0])]
  elif layer==2 and k==25:prefix=op[net,layer][:3]+[(12.7,3.15),(x,3.4)]
  elif layer==2 and k==23:
   sx=op[net,4][0][0];prefix=[op[net,4][0],(sx,3.55),(sx+.25,3.8),(x-.25,3.8),(x,4.05)]
  elif layer==4 and k==2:prefix=[start,(start[0],9.6),(x,9.6+x-start[0])]
  elif layer==4 and k==26:prefix=[start,(start[0],9.8),(x,9.8+start[0]-x)]
  else:
   j=main4[2:].index(k);sx=op[net,layer][4][0];sy=10.25+.3*j;prefix=op[net,layer][:5]+[(sx,sy),(x,sy+sx-x)]
  if layer==2:
   if k==4:tail=[(x,35.1),(px,35.1+x-px),xy(p)]
   elif k in [6,8,10,12,16,18]:
    lx={6:4.3,8:4.7,10:5.1,12:5.5,16:5.9,18:6.25}[k];tail=[(x,35.1),(lx,35.1+x-lx),(lx,py-.25),(lx+.25,py),xy(p)]
   elif k in [20,22,24]:tail=[(x,35.1),(px,35.1+x-px),xy(p)]
   elif k==23:tail=[(x,33),(13,33+13-x),(13,py-(13-px)),xy(p)]
   elif k==25:tail=[(x,32.5),(13.8,32.5+13.8-x),(13.8,43.35),(14.3,43.85),(16.5,43.85),(px,43.85-(px-16.5)),xy(p)]
  else:
   if k==2:tail=[(x,30.3),(5.65,31),(5,31),xy(p)]
   elif k==26:tail=[(x,35.1),(6.45,35.1+x-6.45),(6.45,py-(px-6.45)),xy(p)]
   elif k==21:tail=[(x,30.3),(13.65,31),(14.5,31),xy(p)]
   elif k in [1,3,5]:tail=[(x,35.1),(px,35.1+px-x),xy(p)]
   else:
    oldnet=next(f'ZIF{int(z):02d}' for z,t in old['zif_to_target'].items() if t==targets[str(k)]);_,suffix=split(op[oldnet,4],39);lx=suffix[0][0];tail=[(x,35.1),(lx,35.1+lx-x)]+suffix
  addpath(net,layer,prefix+tail)
tracks=[]
for route in paths:
 route['points']=reduce([tuple(quant(v) for v in p) for p in route['points']])
 for a,b in zip(route['points'],route['points'][1:]):
  dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1]);assert min(dx,dy,abs(dx-dy))<8*U,(route['net'],a,b)
  tracks.append(dict(net=route['net'],layer=route['layer'],x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=WIDTH))
dc=dict(tracks=tracks,arcs=[],paths=paths,zif_to_target=targets,rf_qd_map=rfmap,central_bus=dict(L2=main2,L4=main4,x_left=6.35,x_right=12.95,pitch_mm=.6,clearance_mm=.475),unrouted=[])

primitives=[];sections={};channels={};control={}
for ch,pin in rfmap.items():
 i=int(ch);src=xy(PD[f'SMP{i}-1']);ci=xy(PD[f'C{i}-1']);co=xy(PD[f'C{i}-2']);r=xy(PD[f'R{i}-1']);q=xy(PD[f'Q1-{pin}'])
 if i in [1,5]:
  incoming=[src,(ci[0],src[1]),ci]
  outgoing=[co,(co[0],31.3),(q[0],31.3+abs(co[0]-q[0])),q]
 elif i in [2,6]:
  y=38.2 if i==2 else 37.5
  incoming=[src,(src[0],y),(ci[0],y+abs(ci[0]-src[0])),ci]
  outgoing=[co,(co[0],q[1]),q]
 else:
  incoming=[src,(ci[0],src[1]),ci]
  outgoing=[co,(co[0],45.9),(q[0],45.9-abs(q[0]-co[0])),q]
 parts={}
 for name,pts,net in [('input',incoming,f'S{i}'),('output',outgoing,f'MW{i}')]:
  pts=reduce(pts)
  for a,b in zip(pts,pts[1:]):
   dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1]);assert min(dx,dy,abs(dx-dy))<8*U,(i,name,a,b)
  pp=fillet_polyline(pts,.3,layer=32,width=RFW,net=net,shrink_to_fit=False);assert not validate_path(pp)
  parts[name]=pp;sections[f'{i}_{name}']=[primitive_to_altium_dict(p) for p in pp];control[f'{i}_{name}']=pts;primitives+=pp
 assert any(type(p).__name__=='Line' and LineString([p.start,p.end]).distance(Point(*r))<4*U for p in parts['output']),('stub',i)
 channels[ch]=dict(QD_pin=pin,input=f'SMP{i}-1',capacitor=f'C{i}',bias=f'R{i}',input_length_mm=path_length(parts['input']),output_length_mm=path_length(parts['output']),resistor_RF_pad_on_main_line=True,bias_branch_length_mm=0)
serial=[primitive_to_altium_dict(p) for p in primitives]
rf=dict(tracks=[p for p in serial if p['kind']=='track'],arcs=[p for p in serial if p['kind']=='arc'],channels=channels,sections=sections,control_points=control,rf_qd_map=rfmap,delay_matching_deferred_by_user=True,shield_vias=0)

def shape(p):
 if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(*xy(p)).buffer(p['size_x']/2,quad_segs=64)
 return translate(rotate(box(-p['size_x']/2,-p['size_y']/2,p['size_x']/2,p['size_y']/2),p['rotation'],origin=(0,0)),*xy(p))
obs=[dict(net=p['net'],label=str(p['component'])+'-'+p['number'],layers={1,2,3,4,5,32} if p['hole'] else {p['layer']},geom=shape(p)) for p in g['pads']]
obs += [dict(net=v['net'],label='via@'+str(tuple(round(x,3) for x in xy(v))),layers={1,2,3,4,5,32},geom=Point(*xy(v)).buffer(v['diameter']/2,quad_segs=64)) for v in g['vias']]
pad_errors=[]
for i,a in enumerate(obs):
 for b in obs[:i]:
  if a['net']==b['net'] or not a['layers']&b['layers']:continue
  gap=a['geom'].distance(b['geom'])
  if gap<.15-8*U:pad_errors.append([a['label'],b['label'],gap])
assert not pad_errors,pad_errors
for name,rs,geoms in [('DC',tracks,[LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2,quad_segs=32) for t in tracks]),('RF',serial,[copper_geometry(p,.000001) for p in primitives])]:
 errors=[];mini={'track_track':99.,'track_pad_or_via':99.}
 for i,t in enumerate(rs):
  if geoms[i].intersects(box(*g['qd_signal_keepout'])):errors.append(['QD',i,t['net']])
  for j,u in enumerate(rs[:i]):
   if t['net']==u['net'] or t['layer']!=u['layer']:continue
   gap=geoms[i].distance(geoms[j]);mini['track_track']=min(mini['track_track'],gap)
   if gap<.15-8*U:errors.append(['track',i,j,t['net'],u['net'],round(gap,6)])
  for o in obs:
   if o['net']==t['net'] or t['layer'] not in o['layers']:continue
   gap=geoms[i].distance(o['geom']);mini['track_pad_or_via']=min(mini['track_pad_or_via'],gap)
   if gap<.15-8*U:errors.append(['obstacle',i,t['net'],o['label'],round(gap,6)])
 (dc if name=='DC' else rf)['validation']=dict(errors=errors,minimum_clearances_mm=mini)
 print(name,json.dumps(dict(tracks=len(rs),errors=len(errors),first_errors=errors[:50],minimum=mini),indent=2))
for name,obj in [('geometry',g),('dc_candidate',dc),('rf_candidate',rf)]:(H/(name+'.json')).write_text(json.dumps(obj,indent=2))
if not dc['validation']['errors'] and not rf['validation']['errors']:
 for name,obj in [('dc_routes',dc),('rf_routes',rf)]: (H/(name+'.json')).write_text(json.dumps(obj,indent=2))
 print('GEOMETRY PASSED')
