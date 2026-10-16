"""Route the rotated carrier RF nets and emit genuine tangent copper arcs."""
import argparse
import copy
import json
import math
from pathlib import Path
import random
import sys
import time
import hashlib

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from skimage.graph import MCP_Geometric

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'qd38_carrier_20261010'))
from route_circuit import pgeom

GRID = .025
NX, NY = 781, 2717
WIDTH = .11
REQUIRED = .15
GUARD = .027

def paint(draw, g, fill=1):
    if g.is_empty:
        return
    if hasattr(g, 'geoms'):
        for part in g.geoms:
            paint(draw, part, fill)
    elif isinstance(g, Polygon):
        draw.polygon([(round(x/GRID), round(y/GRID)) for x,y in g.exterior.coords], fill=fill)
        for ring in g.interiors:
            draw.polygon([(round(x/GRID), round(y/GRID)) for x,y in ring.coords], fill=0)

def mask(g):
    im = Image.new('1', (NX, NY))
    paint(ImageDraw.Draw(im), g)
    return np.asarray(im, dtype=bool).copy()

def compact(path):
    result = [path[0]]
    previous = None
    for a,b in zip(path,path[1:]):
        direction = tuple(np.sign(np.subtract(b,a)))
        if previous is not None and direction != previous:
            result.append(a)
        previous = direction
    result.append(path[-1])
    return [[float(x*GRID),float(y*GRID)] for y,x in result]

def arc_line(arc):
    start = arc['start_angle']
    sweep = (arc['end_angle'] - start) % 360
    count = max(3, int(math.ceil(sweep/.5)))
    return LineString([(arc['cx']+arc['radius']*math.cos(math.radians(a)),
                        arc['cy']+arc['radius']*math.sin(math.radians(a)))
                       for a in np.linspace(start,start+sweep,count+1)])

def fillet(points, net, radius=.18):
    pts = [np.array(x,dtype=float) for x in points]
    before = [x.copy() for x in pts]
    after = [x.copy() for x in pts]
    arcs = []
    for i in range(1,len(pts)-1):
        prev, point, nxt = pts[i-1:i+2]
        u, v = point-prev, nxt-point
        l1, l2 = np.linalg.norm(u), np.linalg.norm(v)
        u, v = u/l1, v/l2
        turn = math.acos(float(np.clip(np.dot(u,v),-1,1)))
        if turn < 1e-7:
            continue
        if turn > math.pi-1e-5:
            raise ValueError('Reversal cannot be filleted')
        cut = min(radius*math.tan(turn/2), l1*.36, l2*.36)
        r = cut/math.tan(turn/2)
        cross = float(u[0]*v[1] - u[1]*v[0])
        sign = 1 if cross>0 else -1
        a = point-u*cut
        b = point+v*cut
        center = a+np.array([-u[1],u[0]])*sign*r
        aa = math.degrees(math.atan2(a[1]-center[1],a[0]-center[0]))%360
        ab = math.degrees(math.atan2(b[1]-center[1],b[0]-center[0]))%360
        before[i], after[i] = a,b
        arcs.append(dict(net=net,layer=32,cx=float(center[0]),cy=float(center[1]),
                         radius=float(r),start_angle=aa if sign>0 else ab,
                         end_angle=ab if sign>0 else aa,width=WIDTH))
    tracks = [dict(net=net,layer=32,a=a.tolist(),b=b.tolist(),width=WIDTH)
              for a,b in zip(after,before[1:]) if np.linalg.norm(b-a)>1e-8]
    return tracks,arcs

def copper(tracks,arcs):
    lines = [LineString([t['a'],t['b']]) for t in tracks]+[arc_line(a) for a in arcs]
    return unary_union(lines).buffer(WIDTH/2,quad_segs=32)

def shortcuts(points, forbidden, other_copper):
    """Replace lattice staircases with long H/V/45 runs where physically clear."""
    points=[list(x) for x in points]
    obstacle=unary_union([forbidden]+other_copper)
    a=0
    while a<len(points)-2:
        changed=False
        for b in range(len(points)-1,a+1,-1):
            x,y=points[a];xx,yy=points[b]
            dx,dy=xx-x,yy-y;d=min(abs(dx),abs(dy))
            sx,sy=np.sign(dx),np.sign(dy)
            candidates=[[[x,y],[xx,yy]], [[x,y],[x+sx*d,y+sy*d],[xx,yy]],
                        [[x,y],[xx-sx*d,yy-sy*d],[xx,yy]]]
            for mid in candidates:
                mid=[p for k,p in enumerate(mid) if not k or math.dist(p,mid[k-1])>1e-8]
                if len(mid)>=b-a+1:continue
                geom=LineString(mid).buffer(WIDTH/2,quad_segs=32)
                if geom.distance(obstacle)>=REQUIRED+.008:
                    points=points[:a]+mid+points[b+1:]
                    changed=True;break
            if changed:break
        if not changed:a+=1
    return points

def strip_collinear(points):
    """Remove redundant lattice joins without changing the route centreline."""
    result=[]
    for point in points:
        point=list(point)
        if result and math.dist(result[-1],point)<1e-9:
            continue
        while len(result)>1:
            u=np.subtract(result[-1],result[-2]);v=np.subtract(point,result[-1])
            if abs(u[0]*v[1]-u[1]*v[0])<1e-9 and np.dot(u,v)>0:
                result.pop()
            else:
                break
        result.append(point)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--placement',type=Path,default=HERE/'placement_candidate.json')
    parser.add_argument('--iterations',type=int,default=30)
    parser.add_argument('--seed',type=int,default=83)
    parser.add_argument('--output',type=Path,default=HERE/'rf_routed_candidate.json')
    parser.add_argument('--progress',type=Path,default=HERE/'rf_progress.json')
    parser.add_argument('--warm-start',type=Path)
    args=parser.parse_args()
    plan=json.loads(args.placement.read_text())
    source_hash=hashlib.sha256(args.placement.read_bytes()).hexdigest()
    jobs=[j for j in plan['route_jobs'] if j['layer']==32 and j['net'].startswith(('MW','S'))]
    assert len(jobs)==48, len(jobs)
    static=[(p['net'],pgeom(p),f"{p['ref']}-{p['pin']}") for p in plan['physical_pads'] if p['layer'] in (32,74)]
    static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48),v['label'])
               for v in plan['vias'] if v['low']<=32<=v['high']]
    cx,cy=plan['sample_center'];cw,ch=plan['cavity_mm']
    cavity=box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)
    static.append((None,cavity,'blind_cavity'))
    # Reserve the 1.05 mm circle of 0.25 mm shield-via lands. Only
    # the SMP's own S net uses its symmetric RF escape sector.
    static += [(f"S{int(s['ref'][3:]):02}", Point(s['x'],s['y']).buffer(1.175,quad_segs=96), s['ref']+'-shield-ring')
               for s in plan['smp']]
    boundary=Polygon(plan['board_outline'])
    edge_mask=mask(box(-1,-1,21,70).difference(boundary.buffer(-.22)))
    nets=sorted({j['net'] for j in jobs})
    hard={}; forbidden={}
    for net in nets:
        keepouts=[g for n,g,label in static if n!=net]
        for ref in {p['ref'] for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('R')}:
            pads=[p for p in plan['physical_pads'] if p['ref']==ref]
            envelope=unary_union([pgeom(p) for p in pads]).convex_hull
            own=unary_union([pgeom(p) for p in pads if p['net']==net])
            keepouts.append(envelope.difference(own))
        forbidden[net]=unary_union(keepouts)
        hard[net]=mask(forbidden[net].buffer(REQUIRED+WIDTH/2+GUARD,quad_segs=12)) | edge_mask
    starts=[];ends=[]
    for j in jobs:
        a=tuple(round(v/GRID) for v in reversed(j['a']))
        b=tuple(round(v/GRID) for v in reversed(j['b']))
        if hard[j['net']][a] or hard[j['net']][b]:
            raise ValueError((j['net'],j['kind'],'blocked endpoint',j['a'],j['b']))
        starts.append(a);ends.append(b)
    history=np.zeros((NY,NX),dtype=np.float32)
    routes=[None]*len(jobs);soft=[None]*len(jobs);geoms=[None]*len(jobs)
    rng=random.Random(args.seed)
    todo=sorted(range(len(jobs)),key=lambda i:({'RF':0,'RF_BIAS':1,'RF_QD':2}.get(jobs[i]['kind'],3),math.dist(jobs[i]['a'],jobs[i]['b'])))
    if args.warm_start:
        previous=json.loads(args.warm_start.read_text())['routes']
        def signature(job):
            return (job['kind'],*(round(v,7) for point in (job['a'],job['b']) for v in point))
        lookup={signature(r['job']):r for r in previous if r}
        for ix,job in enumerate(jobs):
            old=lookup.get(signature(job))
            if old is None:continue
            r=copy.deepcopy(old);r['job']=job
            for item in r['tracks']+r['arcs']:item['net']=job['net']
            g=copper(r['tracks'],r['arcs'])
            if g.distance(forbidden[job['net']])<REQUIRED+.001:continue
            routes[ix]=r;geoms[ix]=g;soft[ix]=mask(g.buffer(REQUIRED+GUARD,quad_segs=12))
        todo=[ix for ix in todo if routes[ix] is None]
        print('RF WARM_START',len(jobs)-len(todo),'REUSED',flush=True)
    conflicts=[]
    for iteration in range(args.iterations):
        if iteration:
            rng.shuffle(todo)
        for ix in todo:
            net=jobs[ix]['net']
            resistor_pad=unary_union([pgeom(p) for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('R') and p['pin']=='1' and p['net']==net])
            same_stems=[g.difference(resistor_pad) for k,g in enumerate(geoms) if k!=ix and g is not None and jobs[k]['net']==net]
            # The QD-to-R path must not enter its own C2 terminal, which
            # would create a capacitor loop despite same-net DRC clearance.
            extra_keepouts=list(same_stems)
            if jobs[ix]['kind']=='RF_QD':
                extra_keepouts += [pgeom(p) for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('C') and p['pin']=='2' and p['net']==net]
            live_forbidden=unary_union([forbidden[net]]+extra_keepouts)
            live_hard=hard[net] | mask(unary_union(extra_keepouts).buffer(REQUIRED+WIDTH/2+GUARD,quad_segs=12)) if extra_keepouts else hard[net]
            occupied=sum((m for k,m in enumerate(soft) if m is not None and jobs[k]['net']!=net),
                         start=np.zeros((NY,NX),dtype=np.uint16))
            costs=1.+occupied*(20+iteration*20)+history*(1+iteration)
            costs[live_hard]=np.inf
            # A four-millimetre end margin admits the neighboring component
            # escape while avoiding unrelated opposite-end board detours.
            lower=max(0,int((min(jobs[ix]['a'][1],jobs[ix]['b'][1])-4.)/GRID))
            upper=min(NY,int((max(jobs[ix]['a'][1],jobs[ix]['b'][1])+4.)/GRID)+1)
            costs[:lower,:]=np.inf
            costs[upper:,:]=np.inf
            solver=MCP_Geometric(costs,fully_connected=True)
            result,_=solver.find_costs([starts[ix]],[ends[ix]],find_all_ends=False)
            if not math.isfinite(result[ends[ix]]):
                raise ValueError((net,jobs[ix]['kind'],'no path'))
            points=compact(solver.traceback(ends[ix]))
            others=[g for k,g in enumerate(geoms) if g is not None and k!=ix and jobs[k]['net']!=net]
            points=strip_collinear(shortcuts(points,live_forbidden,others))
            selected=None
            for r in (.18,.12,.08,.04,.02,.01):
                ts,aa=fillet(points,net,r)
                # Preserve the exact component-pad centre in the intended
                # C-to-resistor-to-QD chain; any grid correction stays inside
                # its own conductive pad, never as an external branch stub.
                for actual,snapped in ((jobs[ix]['a'],points[0]),(jobs[ix]['b'],points[-1])):
                    if math.dist(actual,snapped)>1e-8:
                        ts.append(dict(net=net,layer=32,a=list(actual),b=list(snapped),width=WIDTH))
                g=copper(ts,aa)
                gap=g.distance(live_forbidden)
                if gap>=REQUIRED+.002:
                    selected=(ts,aa,g,gap,r)
                    break
            if selected is None:
                raise ValueError((net,'tangent rounding clearance',gap))
            ts,aa,g,gap,r=selected
            routes[ix]=dict(job=jobs[ix],points=points,tracks=ts,arcs=aa,minimum_static_gap=gap,nominal_fillet_radius=r)
            geoms[ix]=g
            soft[ix]=mask(g.buffer(REQUIRED+GUARD,quad_segs=12))
        conflicts=[]
        for a in range(len(jobs)):
            for b in range(a):
                if jobs[a]['net']==jobs[b]['net']:
                    continue
                gap=geoms[a].distance(geoms[b])
                if gap<REQUIRED+.001:
                    conflicts.append((a,b,gap))
                    history+=mask(geoms[a].buffer(.18).intersection(geoms[b].buffer(.18)))*.8
        report=dict(iteration=iteration,conflicts=conflicts,routes=routes)
        args.progress.write_text(json.dumps(report,indent=2))
        print('RF ITER',iteration,'CONFLICTS',len(conflicts),flush=True)
        if not conflicts:
            break
        todo=sorted({i for a,b,d in conflicts for i in (a,b)})
        if iteration%4==3:
            todo=[i for i,j in enumerate(jobs) if j['kind']=='RF_QD']
    out=copy.deepcopy(plan)
    out['rf_source_placement_sha256']=source_hash
    out['tracks']=[t for t in plan.get('tracks',[]) if t['layer']!=32]+[t for r in routes for t in r['tracks']]
    out['arcs']=[a for r in routes for a in r['arcs']]
    out['rf_routed_jobs']=routes
    out['rf_routing_validation']=dict(passed=not conflicts,conflicts=conflicts,routes=len(routes),
        min_static_gap_mm=min(r['minimum_static_gap'] for r in routes),
        arcs=len(out['arcs']),minimum_arc_radius_mm=min(a['radius'] for a in out['arcs']))
    args.output.write_text(json.dumps(out,indent=2))
    print(json.dumps(out['rf_routing_validation'],indent=2),flush=True)
    if conflicts:
        sys.exit(2)

if __name__=='__main__':
    main()
