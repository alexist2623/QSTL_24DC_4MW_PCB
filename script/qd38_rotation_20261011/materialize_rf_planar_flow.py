"""Curve and independently check a complete offline planar RF flow result."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import math
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr
from geodesic_rf_assignment import remap

H=Path(__file__).resolve().parent

def minimum_rf_bend_shortcut(points,obstacles,boundary):
    """Choose the fewest visible straight runs; RF slopes are unrestricted."""
    n=len(points)
    pairs=[(i,j) for i in range(n-1) for j in range(i+1,n)]
    lines=np.array([LineString([points[i],points[j]]) for i,j in pairs],dtype=object)
    copper=shapely.buffer(lines,.055,quad_segs=24)
    valid=(shapely.distance(copper,obstacles)>=.1505-1e-8)&shapely.covers(boundary,copper)
    edges={i:[] for i in range(n)}
    for (i,j),ok,line in zip(pairs,valid,lines):
        if ok:edges[i].append((j,1000+line.length))
    best=[math.inf]*n;previous=[None]*n;best[0]=0
    for i in range(n-1):
        for j,cost in edges[i]:
            if best[i]+cost<best[j]:best[j]=best[i]+cost;previous[j]=i
    if not math.isfinite(best[-1]):return points
    chosen=[];i=n-1
    while i is not None:chosen.append(points[i]);i=previous[i]
    return list(reversed(chosen))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--placement',type=Path,default=H/'placement_lower_over_smp_candidate.json')
    ap.add_argument('--flow',type=Path,required=True)
    ap.add_argument('--reference',type=Path)
    ap.add_argument('--output',type=Path,default=H/'rf_planar_flow_candidate.json')
    args=ap.parse_args()
    flow=json.loads(args.flow.read_text());assert (flow.get('passed') or flow.get('capacity_complete')) and len(flow['routes'])==16
    original=json.loads(args.placement.read_text())
    mapping={int(r['group']):int(r['target']) for r in flow['routes']}
    assert len(set(mapping.values()))==16
    p=remap(original,mapping)
    if 'fixed_rf_routes' in flow:
        fixed=copy.deepcopy(flow['fixed_rf_routes'])
    else:
        reference=args.reference or Path(flow['reference_snapshot'])
        source=json.loads(reference.read_text());fixed=copy.deepcopy([r for r in source['routes'] if r['job']['kind']!='RF_QD'])
        if flow.get('reference_sha256'):
            assert hashlib.sha256(reference.read_bytes()).hexdigest()==flow['reference_sha256']
    for route in fixed:
        net=route['job']['net']
        if net.startswith('MW'):
            net=f'MW{mapping[int(net[2:])]:02}'
            route['job']['net']=net
            for t in route['tracks']+route['arcs']:t['net']=net
    jobs={j['net']:j for j in p['route_jobs'] if j['kind']=='RF_QD'}
    raw=[]
    for item in flow['routes']:
        net=f'MW{item["target"]:02}';job=copy.deepcopy(jobs[net]);points=list(reversed(item['points']))
        assert math.dist(points[0],job['a'])<1e-5 and math.dist(points[-1],job['b'])<1e-5
        raw.append(dict(job=job,points=points))
    static=[(pad['net'],rr.pgeom(pad)) for pad in p['physical_pads'] if pad['layer'] in (32,74)]
    static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48)) for v in p['vias'] if v['low']<=32<=v['high']]
    static += [(f'S{int(s["ref"][3:]):02}',Point(s['x'],s['y']).buffer(1.175,quad_segs=96)) for s in p['smp']]
    cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];static.append((None,box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)))
    rrefs=sorted({pad['ref'] for pad in p['physical_pads'] if pad['ref'] and pad['ref'].startswith('R')})
    boundary=Polygon(p['board_outline']).buffer(-.2)
    forbidden={}
    fixed_geoms=[rr.copper(r['tracks'],r['arcs']) for r in fixed]
    for r in raw:
        net=r['job']['net'];parts=[g for n,g in static if n!=net]
        own_r=[]
        for ref in rrefs:
            pads=[pad for pad in p['physical_pads'] if pad['ref']==ref]
            own=unary_union([rr.pgeom(pad) for pad in pads if pad['net']==net])
            hull=unary_union([rr.pgeom(pad) for pad in pads]).convex_hull
            parts.append(hull.difference(own));own_r.append(own)
        own_r=unary_union(own_r)
        for fixed_route,g in zip(fixed,fixed_geoms):
            parts.append(g.difference(own_r) if fixed_route['job']['net']==net else g)
        parts += [rr.pgeom(pad) for pad in p['physical_pads'] if pad['ref'] and pad['ref'].startswith('C') and str(pad['pin'])=='2' and pad['net']==net]
        forbidden[net]=unary_union(parts)
    geoms=[LineString(r['points']).buffer(.055,quad_segs=32) for r in raw]
    for sweep in range(5):
        changes=0
        for i in (range(len(raw)) if sweep%2==0 else reversed(range(len(raw)))):
            route=raw[i];net=route['job']['net']
            obstacles=unary_union([forbidden[net]]+[g for j,g in enumerate(geoms) if j!=i])
            points=minimum_rf_bend_shortcut(route['points'],obstacles,boundary)
            if points!=route['points']:
                route['points']=points;geoms[i]=LineString(points).buffer(.055,quad_segs=32);changes+=1
        print('RF_FLOW_SIMPLIFY',sweep,'CHANGES',changes,flush=True)
        if not changes:break
    failures=[]
    for i,route in enumerate(raw):
        net=route['job']['net'];others=unary_union([forbidden[net]]+[g for j,g in enumerate(geoms) if j!=i])
        selected=None
        for radius in (.25,.18,.12,.08,.04,.02,.01,.005):
            tracks,arcs=rr.fillet(route['points'],net,radius)
            geom=rr.copper(tracks,arcs)
            gap=geom.distance(others)
            if gap>=.1505 and boundary.covers(geom):
                selected=(tracks,arcs,geom,gap,radius);break
        if selected is None:
            failures.append(dict(net=net,failure='no_clear_tangent_rounding',last_gap=gap,
                                 static_gap=geom.distance(forbidden[net]),
                                 other_gaps=[(raw[j]['job']['net'],geom.distance(g)) for j,g in enumerate(geoms) if j!=i and geom.distance(g)<.15],
                                 points=route['points'],static_land_gaps=[(n,geom.distance(g)) for n,g in static if n!=net and geom.distance(g)<.15]));continue
        tracks,arcs,geom,gap,radius=selected
        route.update(tracks=tracks,arcs=arcs,minimum_static_gap=geom.distance(forbidden[net]),nominal_fillet_radius=radius)
        geoms[i]=geom
    if failures:
        args.output.with_suffix('.failures.json').write_text(json.dumps(dict(passed=False,failures=failures),indent=2))
        print(json.dumps(failures,indent=2));raise SystemExit(2)
    p['rf_source_placement_sha256']=hashlib.sha256(args.placement.read_bytes()).hexdigest()
    p['rf_routed_jobs']=fixed+raw
    p['tracks']=[t for t in p['tracks'] if t['layer']!=32]+[t for r in fixed+raw for t in r['tracks']]
    p['arcs']=[a for r in fixed+raw for a in r['arcs']]
    p['rf_planar_flow_source']=str(args.flow.resolve())
    p['rf_routing_validation']=dict(passed=False,status='Independent geometry and topology audit required',routes=48,arcs=len(p['arcs']))
    args.output.write_text(json.dumps(p,indent=2));print(args.output,flush=True)

if __name__=='__main__':main()
