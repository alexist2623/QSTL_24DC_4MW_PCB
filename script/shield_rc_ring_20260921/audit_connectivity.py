from pathlib import Path
import sys,struct,json,math,collections,shutil,hashlib
H=Path(__file__).resolve().parent;W=H.parent/'_support';PREV=H.parent/'rf_six_inward_20260920';P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board'),str(W/'rf_revision'),str(W/'route_python')]
from native_metadata_helpers import properties,pads_stream,UNIT,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route,read_regions,trackkey,arckey
from geometry_helpers import Arc,copper_geometry
from shapely.geometry import Point,LineString,box
from shapely.affinity import rotate,translate
source=P/(B+'.PcbDoc');s=snapshot(source);cs=properties(s['Components6/Data']);ns=properties(s['Nets6/Data']);ps=pads_stream(s['Pads6/Data']);ts,ars,vs=read_route(s,ns);regions=read_regions(s['Regions6/Data']);polygons=properties(s['Polygons6/Data']);expected=json.loads((PREV/'expected.json').read_text())
layers={1,2,3,4,5,32};nets=collections.defaultdict(list);actual={};nodes=[]
def insert(net,label,lay,geom):
 if net is None:return
 item=dict(net=net,label=label,layers=set(lay),geometry=geom);nets[net].append(item);nodes.append(item)
for p in ps:
 net=None if p['net']==65535 else ns[p['net']]['NAME'];label=(cs[p['component']]['SOURCEDESIGNATOR'] if p['component']!=65535 else 'MOUNT')+'-'+p['number']
 x,y,sx,sy=[v*UNIT for v in p['coords'][:4]]
 if p['component']!=65535:actual[label]=net
 # Every connected SMD trace terminates at a pad centre, far from pad corners.
 shape=translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),p['rotation'],origin=(0,0)),x,y)
 if p['layer']==74:shape=Point(x,y).buffer(min(sx,sy)/2,quad_segs=128)
 insert(net,'pad:'+label,layers if p['layer']==74 else {p['layer']},shape)
for v in vs:
 span=tuple(sorted((v['body'][29],v['body'][30])))
 assert span==((5,32) if v['net']=='GND' else (1,32)),('Unexpected via layer span',v['net'],span)
 insert(v['net'],'via:'+str(v['index']),({5,32} if v['net']=='GND' else layers),Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=128))
for t in ts:insert(t['net'],'track:'+str(t['index']),{t['layer']},LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2,quad_segs=32))
for a in ars:insert(a['net'],'arc:'+str(a['index']),{a['layer']},copper_geometry(Arc((a['cx'],a['cy']),a['radius'],a['start_angle'],(a['end_angle']-a['start_angle'])%360,a['layer'],a['width'],a['net']),.000001))
for r in regions:
 ni=r['net_index']
 if ni==65535 and r['polygon_index']!=65535:ni=int(polygons[r['polygon_index']]['NET'])
 if r['layer'] in layers and ni!=65535:insert(ns[ni]['NAME'],'region:'+str(r['index']),{r['layer']},r['geometry'])
reports=[];broken=[]
for net,items in sorted(nets.items()):
 parent=list(range(len(items)))
 def root(i):
  while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
  return i
 for i,a in enumerate(items):
  for j,b in enumerate(items[:i]):
   if a['layers']&b['layers'] and a['geometry'].distance(b['geometry'])<=4*UNIT:parent[root(i)]=root(j)
 groups=collections.defaultdict(list)
 for i,a in enumerate(items):groups[root(i)].append(a['label'])
 pads=sorted(a['label'][4:] for a in items if a['label'].startswith('pad:') and not a['label'].startswith('pad:MOUNT'))
 assert pads==sorted(expected['nets'][net]),(net,pads,expected['nets'][net])
 report=dict(net=net,copper_connected_components=len(groups),connected_pins=pads,primitive_count=len(items),groups=list(groups.values()) if len(groups)>1 else [])
 reports.append(report)
 if len(groups)>1:broken.append(report)
assert actual==expected['pin_net_map']|{p:None for p in expected['nc_pins']}
raw=s['Connections6/Data'];pos=0;connections=[]
while pos<len(raw):
 size=struct.unpack_from('<I',raw,pos)[0];pos+=4;b=raw[pos:pos+size];pos+=size
 ni=struct.unpack_from('<H',b,3)[0];net=ns[ni]['NAME'];x1,y1,x2,y2=struct.unpack_from('<4i',b,13);ends=[]
 for x,y in [(x1,y1),(x2,y2)]:
  pp=[p for p in ps if math.dist((p['coords'][0],p['coords'][1]),(x,y))<4]
  ends.append(dict(x=x*UNIT,y=y*UNIT,pads=[dict(pin=(cs[p['component']]['SOURCEDESIGNATOR'] if p['component']!=65535 else 'MOUNT')+'-'+p['number'],net=None if p['net']==65535 else ns[p['net']]['NAME']) for p in pp]))
 connections.append(dict(net=net,endpoints=ends,endpoints_agree_with_net=all(any(p['net']==net for p in e['pads']) for e in ends)))
assert pos==len(raw) and len(connections)==struct.unpack('<I',s['Connections6/Header'])[0]
report=dict(passed=not broken and not connections,physical_copper_connectivity_passed=not broken,pcb_sha256=sha(source),method='Independent graph of saved copper intersections by net and physical layer, including explicit through and L5-L6 blind-via spans and GND polygon regions with inherited polygon net assignments; no ratsnest/DRC result used to infer continuity.',connected_net_count=len(reports),DC_net_count=sum(r['net'].startswith('ZIF') for r in reports),RF_named_net_count=sum(r['net'].startswith(('MW','S')) for r in reports),all_component_pin_assignments_match_schematic=True,disconnected_copper_nets=broken,via_spans_top_to_bottom=sum(v['net']!='GND' for v in vs),via_spans_L5_L6=sum(v['net']=='GND' for v in vs),nets=reports,stored_connection_line_count=len(connections),stored_connection_lines=connections)
name='connectivity.json';(H/name).write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='nets'},indent=2))
assert report['passed']
(P/'docs/connection_validation.json').write_text(json.dumps(report,indent=2)+'\n')
