"""Compare RF terminal assignments in a shared obstacle domain with 45-degree ports."""
from pathlib import Path
import json
import math
import itertools
import numpy as np
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from scipy.optimize import linear_sum_assignment
from skimage.graph import MCP_Geometric
import route_rf_rotated as rr
from geodesic_rf_assignment import remap

H=Path(__file__).resolve().parent
p=json.loads((H/'placement_candidate.json').read_text())
reference=json.loads((H/'rf_ordered_candidate.json').read_text())
groups=sorted(s['q'] for s in p['smp'])
pads={(d['ref'],d['pin']):d for d in p['physical_pads'] if d['ref']}
static={f"{d['ref']}-{d['pin']}":rr.pgeom(d) for d in p['physical_pads'] if d['layer'] in (32,74)}
static.update({v['label']:Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48) for v in p['vias']})
for s in p['smp']:
    static[s['ref']+'-ring']=Point(s['x'],s['y']).buffer(1.175,quad_segs=96)
cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];static['cavity']=box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)
for g in groups:
    static[f'R{g:02}-hull']=unary_union([rr.pgeom(pads[(f'R{g:02}',str(pin))]) for pin in (1,2)]).convex_hull
for route in reference['rf_routed_jobs']:
    if route['job']['kind']!='RF_BIAS':continue
    xy=route['job']['b']
    group=next(g for g in groups if math.dist(xy,(pads[(f'R{g:02}','1')]['x'],pads[(f'R{g:02}','1')]['y']))<1e-5)
    static[f'R{group:02}-stem']=rr.copper(route['tracks'],route['arcs'])
common=unary_union(list(static.values()))
hard=rr.mask(common.buffer(.232,quad_segs=32))
hard |= rr.mask(box(-1,-1,21,70).difference(Polygon(p['board_outline']).buffer(-.22)))
directions=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1)]

def ports(label,start):
    terminal=static[label]
    blocked=[]
    for name,shape in static.items():
        if name==label:continue
        if label.startswith('R') and name in (label.split('-')[0]+'-hull',label.split('-')[0]+'-stem'):
            shape=shape.difference(terminal)
        blocked.append(shape)
    blocked=unary_union(blocked)
    origin=np.round(np.array(start)/rr.GRID)*rr.GRID
    result=[]
    for dx,dy in directions:
        for step in range(12,69):
            xy=origin+rr.GRID*step*np.array((dx,dy))
            cell=tuple(round(v/rr.GRID) for v in reversed(xy))
            if not (0<=cell[0]<rr.NY and 0<=cell[1]<rr.NX) or hard[cell]:continue
            neck=LineString([origin,xy]).buffer(.055,quad_segs=32)
            gap=neck.distance(blocked)
            if gap>=.152:
                result.append(dict(cell=cell,xy=xy.tolist(),origin=origin.tolist(),gap=gap,neck_length=math.dist(origin,xy),neck_points=[origin.tolist(),xy.tolist()]))
                break
    if not result and label.startswith('Q1-'):
        net=f"MW{int(label.split('-')[1]):02}"
        route=next(r for r in reference['rf_routed_jobs'] if r['job']['kind']=='RF_QD' and r['job']['net']==net)
        for stop in range(1,len(route['points'])):
            prefix=route['points'][:stop+1]
            xy=np.array(prefix[-1]);cell=tuple(round(v/rr.GRID) for v in reversed(xy))
            if hard[cell]:continue
            neck=LineString(prefix).buffer(.055,quad_segs=32);gap=neck.distance(blocked)
            if gap>=.152:
                result.append(dict(cell=cell,xy=xy.tolist(),origin=prefix[0],gap=gap,neck_length=LineString(prefix).length,neck_points=prefix))
                break
    if not result:raise ValueError(('NO PORT',label,start))
    return result

rp={};qp={}
for g in groups:
    d=pads[(f'R{g:02}','1')];rp[g]=ports(f'R{g:02}-1',(d['x'],d['y']))
    d=p['pads'][g-1];start=[x+.15*n for x,n in zip(d['absolute_center'],d['normal'])];qp[g]=ports(f'Q1-{g}',start)
print('R ports', {g:len(v) for g,v in rp.items()},flush=True)
print('QD ports', {g:len(v) for g,v in qp.items()},flush=True)
goals=[tuple(port['cell']) for q in groups for port in qp[q]]
costs=np.ones((rr.NY,rr.NX),float);costs[hard]=np.inf
matrix=np.zeros((16,16));allpaths={}
for i,g in enumerate(groups):
    solver=MCP_Geometric(costs,fully_connected=True)
    dist,_=solver.find_costs([tuple(port['cell']) for port in rp[g]],goals,find_all_ends=True)
    for j,q in enumerate(groups):
        choices=[]
        for port in qp[q]:
            cell=tuple(port['cell'])
            if not math.isfinite(dist[cell]):continue
            cells=solver.traceback(cell)
            rport=next(r for r in rp[g] if tuple(r['cell'])==tuple(cells[0]))
            length=dist[cell]*rr.GRID+rport['neck_length']+port['neck_length']
            points=rport['neck_points'][:-1]+[[x*rr.GRID,y*rr.GRID] for y,x in cells]+port['neck_points'][-2::-1]
            choices.append((length,points))
        if not choices:raise ValueError(('NO DOMAIN PATH',g,q))
        length,points=min(choices,key=lambda item:item[0]);matrix[i,j]=length;allpaths[(g,q)]=points
    print('COMMON',g,flush=True)
rows,cols=linear_sum_assignment(matrix)
mapping={groups[i]:groups[j] for i,j in zip(rows,cols)}
chosen={str(g):allpaths[(g,q)] for g,q in mapping.items()}
conflicts=[]
for a,b in itertools.combinations(groups,2):
    gap=LineString(chosen[str(a)]).distance(LineString(chosen[str(b)]))-.11
    if gap<.15:conflicts.append(dict(a=a,b=b,gap=gap))
out=H/'placement_rf_common_ports.json';out.write_text(json.dumps(remap(p,mapping),indent=2))
report=dict(mapping=mapping,length=float(matrix[rows,cols].sum()),identity=float(np.trace(matrix)),cost_matrix=matrix.tolist(),R_ports=rp,QD_ports=qp,selected_paths=chosen,conflicts=conflicts)
(H/'rf_common_ports_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('cost_matrix','R_ports','QD_ports','selected_paths')},indent=2))
