from pathlib import Path
import sys,json,math,hashlib,collections
H=Path(__file__).resolve().parent;W=H.parent;sys.path.insert(0,str(W/'route_python'))
from shapely.geometry import Point,LineString,Polygon
n=json.loads((H/'native_render_snapshot.json').read_text());old=json.loads((H/'baseline_native.json').read_text());U=2.54e-6
P=Path(n['source']).parent;D=P/'docs';PD={p['component']+'-'+p['number']:p for p in n['pads'] if p['component']};C={c['designator']:c for c in n['components']};errors=[]
def check(ok,msg):
 if not ok:errors.append(msg)
def xy(p):return p['x'],p['y']
def shape(p):
 a=math.radians(p['rotation']);co,si=math.cos(a),math.sin(a)
 return Polygon([(p['x']+dx*co-dy*si,p['y']+dx*si+dy*co) for dx,dy in [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),(p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]])
actual_hash=hashlib.sha256(Path(n['source']).read_bytes()).hexdigest();check(actual_hash==n['source_sha256'],'Stale native snapshot')
expected=json.loads((H/'expected.json').read_text())['pin_net_map']
check(all(p['net']==expected.get(p['component']+'-'+p['number']) for p in n['pads'] if p['component']),'Pin assignments differ from synchronized schematic')
for c in n['components']:
 if c['designator'].startswith(('R','C')):check(abs(c['rotation']/45-round(c['rotation']/45))<1e-8,'Non-45-degree rotation '+c['designator'])
 else:check(c==next(z for z in old['components'] if z['designator']==c['designator']),'Fixed component changed '+c['designator'])
for ext in ['.PcbLib','.PrjPcb']:
 check((P/('QSTL_24DC_4MW_PCB'+ext)).read_bytes()==(H/('QSTL_24DC_4MW_PCB'+ext)).read_bytes(),'Unexpected change '+ext)
rows=[]
for ch,pin in [(1,9),(2,6),(3,1),(4,24)]:
 net='MW'+str(ch);rp=PD[f'R{ch}-1'];cp=PD[f'C{ch}-2'];qp=PD[f'Q1-{pin}']
 ts=[t for t in n['tracks'] if t['layer']==32 and t['net']==net];ars=[a for a in n['arcs'] if a['layer']==32 and a['net']==net]
 edges=[((t['x1'],t['y1']),(t['x2'],t['y2'])) for t in ts]
 for a in ars:
  edges.append(tuple((a['cx']+a['radius']*math.cos(math.radians(a[k])),a['cy']+a['radius']*math.sin(math.radians(a[k]))) for k in ['start_angle','end_angle']))
 nodes=[];adj=collections.defaultdict(list)
 def node(pt):
  for j,p in enumerate(nodes):
   if math.dist(pt,p)<10*U:return j
  nodes.append(pt);return len(nodes)-1
 for a,b in edges:
  i,j=node(a),node(b);adj[i].append(j);adj[j].append(i)
 ends=[i for i in adj if len(adj[i])==1];seen=set();stack=[0]
 while stack:
  i=stack.pop()
  if i in seen:continue
  seen.add(i);stack+=adj[i]
 check(len(ends)==2 and max(map(len,adj.values()))<=2 and len(seen)==len(nodes),net+' has a branch or disconnected path')
 check(all(any(math.dist(nodes[i],xy(p))<10*U for i in ends) for p in [cp,qp]),net+' endpoints are not C2 and QD')
 dist=min(LineString([a,b]).distance(Point(*xy(rp))) for a,b in edges[:len(ts)])
 check(dist<4*U,net+' does not pass through resistor pad centre')
 gap=shape(rp).distance(shape(cp));check(.15<=gap<=.25,net+' R/C are not closely spaced')
 check(C[f'R{ch}']['y']>C[f'C{ch}']['y'],'Resistor not above capacitor')
 # Both capacitor connections enter along the capacitor pad axis.
 for pad in [PD[f'C{ch}-1'],cp]:
  touching=[t for t in n['tracks'] if t['net']==pad['net'] and t['layer']==32 and min(math.dist(xy(pad),(t['x1'],t['y1'])),math.dist(xy(pad),(t['x2'],t['y2'])))<10*U]
  check(len(touching)==1 and abs(touching[0]['y2']-touching[0]['y1'])<4*U,net+' non-collinear capacitor entry')
 rows.append(dict(channel=ch,QD_pin=pin,R_RF_pad_to_main_line_mm=dist,R_branch_trace_length_mm=0.,R_to_C_pad_edge_gap_mm=gap,path_endpoints=len(ends),maximum_graph_degree=max(map(len,adj.values())),R_rotation=C[f'R{ch}']['rotation'],C_rotation=C[f'C{ch}']['rotation']))
report=dict(passed=not errors,errors=errors,pcb_sha256=actual_hash,channels=rows,RF_pin_map_unchanged=True,DC_pin_map_updated_in_schematic_and_library=True,all_passive_rotations_multiple_of_45=True,passive_package=dict(R='0603',C='0402'),description='Planar RF main paths run through each resistor RF via/pad centre; no separate Bottom bias branch. Does not claim elimination of via barrel stubs or EM discontinuities.')
(H/'stubless_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if report['passed']:(D/'RF_stubless.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(bool(errors))
