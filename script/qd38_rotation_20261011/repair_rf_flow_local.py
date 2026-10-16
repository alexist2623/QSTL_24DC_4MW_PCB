"""Try a local full-copper RF escape repair without changing physical placement."""
from pathlib import Path
import json
import copy
import numpy as np
from scipy.optimize import differential_evolution
from shapely.geometry import Point,LineString,box,Polygon
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr

H=Path(__file__).resolve().parent
p=json.loads((H/'placement_lower_over_smp_candidate.json').read_bytes())
flow=json.loads((H/'rf_multi_constrained_0p266_0p16.json').read_bytes())
source=json.loads(Path(flow['reference_snapshot']).read_bytes())
fixed=[r for r in source['routes'] if r['job']['kind']!='RF_QD']
pad_lookup={(d['ref'],str(d['pin'])):d for d in p['physical_pads'] if d['ref']}
source_pad=rr.pgeom(pad_lookup[('R28','1')])
objects=[]
for pad in p['physical_pads']:
    if pad['layer'] not in (32,74):continue
    if (pad['ref'],str(pad['pin'])) in [('R28','1'),('Q1','28')]:continue
    objects.append(rr.pgeom(pad))
for v in p['vias']:objects.append(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64))
for s in p['smp']:
    objects.append(Point(s['x'],s['y']).buffer(1.175,quad_segs=128))
    ref='R'+s['ref'][3:];hull=unary_union([rr.pgeom(pad_lookup[(ref,str(pin))]) for pin in (1,2)]).convex_hull
    objects.append(hull.difference(source_pad) if ref=='R28' else hull)
cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];objects.append(box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2))
for r in fixed:
    shape=rr.copper(r['tracks'],r['arcs'])
    objects.append(shape.difference(source_pad) if r['job']['net']=='MW28' else shape)
for r in flow['routes']:
    if r['group']!=28:objects.append(LineString(r['points']).buffer(.055,quad_segs=64))
blocked=unary_union(objects);boundary=Polygon(p['board_outline'])
r=next(r for r in flow['routes'] if r['group']==28);a=r['points'][0];b=r['points'][-1]
def evaluate(v,curved=False):
    x,y=v;points=rr.strip_collinear([a,[x,a[1]],[x,y],b])
    if curved:
        tracks,arcs=rr.fillet(points,'MW28',.11);cu=rr.copper(tracks,arcs)
    else:cu=LineString(points).buffer(.055,quad_segs=64)
    return cu.distance(blocked),points

result=differential_evolution(lambda v:-min(evaluate(v)[0],evaluate(v,True)[0]),[(13.19,13.21),(41.30,41.75)],tol=1e-5,popsize=8,maxiter=30,seed=7)
gap,points=evaluate(result.x);curve_gap=evaluate(result.x,True)[0]
out=copy.deepcopy(flow);next(q for q in out['routes'] if q['group']==28)['points']=points
out['local_repair']=dict(group=28,minimum_gap=gap,curve_gap_radius_0p11=curve_gap,notes='Full pad/via list used. Independent audit still required.')
target=H/'rf_flow_local_repair_candidate.json';target.write_text(json.dumps(out,indent=2))
print(json.dumps(dict(found=min(gap,curve_gap)>=.1505,path=str(target),gap=gap,curve_gap=curve_gap,points=points),indent=2))
