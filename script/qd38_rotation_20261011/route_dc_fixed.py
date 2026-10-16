"""Route fixed ZIF/DC assignments on one of two inner layers per complete net.

This offline solver never permutes connector assignments. Its input must be an
explicitly synchronized placement/pinmap candidate supplied by the main task.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from skimage.graph import MCP_Geometric

H = Path(__file__).resolve().parent
# Avoid interpreting this module's flags as the exploratory flow grid sizes.
old_argv = sys.argv
sys.argv = [sys.argv[0]]
from route_dc_rotated import pgeom, finalize
sys.argv = old_argv

GRID = .04
NX, NY = 489, 1699
WIDTH, CLEAR, GUARD = .125, .15, .035


def paint(draw, g):
    if g.is_empty:
        return
    if hasattr(g, 'geoms'):
        for part in g.geoms:
            paint(draw,part)
    elif isinstance(g,Polygon):
        draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in g.exterior.coords],fill=1)
        for ring in g.interiors:
            draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in ring.coords],fill=0)


def mask(g):
    im=Image.new('1',(NX,NY))
    paint(ImageDraw.Draw(im),g)
    return np.asarray(im,dtype=bool).copy()


def compact(path):
    result=[path[0]];prev=None
    for a,b in zip(path,path[1:]):
        delta=tuple(np.sign(np.subtract(b,a)))
        if prev is not None and prev!=delta:
            result.append(a)
        prev=delta
    result.append(path[-1])
    return [[float(x*GRID),float(y*GRID)] for y,x in result]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--placement',type=Path,required=True)
    parser.add_argument('--iterations',type=int,default=50)
    parser.add_argument('--seed',type=int,default=13)
    args=parser.parse_args()
    plan=json.loads(args.placement.read_text())
    source_hash=hashlib.sha256(args.placement.read_bytes()).hexdigest()
    plan['dc_source_placement_sha256']=source_hash
    assert plan.get('fixed_zif_assignments_approved'), 'Use an explicitly verified fixed-assignment candidate'
    jobs=sorted([j for j in plan['route_jobs'] if j['kind']=='DC'],key=lambda j:j['net'])
    assert len(jobs)==38
    labels={v['label']:v for v in plan['vias']}
    fixed_map={r['dc_net']:int(r['zif_pin']) for r in plan['pinmap']}
    assert len(set(fixed_map.values()))==38 and 50 not in fixed_map.values()
    for j in jobs:
        source=next(v for v in plan['vias'] if v['net']==j['net'] and not v['label'].startswith('J1-'))
        port=labels[f"J1-{fixed_map[j['net']]}"]
        assert port['net']==j['net']
        j.update(a=[source['x'],source['y']],b=[port['x'],port['y']],source=source['label'],port=port['label'])
    static=[(p['net'],pgeom(p)) for p in plan['physical_pads'] if p['layer']==74]
    static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48)) for v in plan['vias']]
    static += [(None,box(7.55,39.8,11.95,45.2))]
    edge=mask(box(-1,-1,21,70).difference(Polygon(plan['board_outline']).buffer(-.23)))
    hard={}; forbidden={}
    for j in jobs:
        net=j['net'];forbidden[net]=unary_union([g for n,g in static if n!=net])
        hard[net]=mask(forbidden[net].buffer(CLEAR+WIDTH/2+GUARD,quad_segs=12)) | edge
    starts=[];ends=[]
    for j in jobs:
        a=tuple(round(v/GRID) for v in reversed(j['a']))
        b=tuple(round(v/GRID) for v in reversed(j['b']))
        assert not hard[j['net']][a] and not hard[j['net']][b], (j['net'],'blocked endpoint')
        starts.append(a);ends.append(b)
    hist={l:np.zeros((NY,NX),dtype=np.float32) for l in (2,4)}
    occ={l:np.zeros((NY,NX),dtype=np.int16) for l in (2,4)}
    paths=[None]*len(jobs);geoms=[None]*len(jobs);soft=[None]*len(jobs)
    layers=[None]*len(jobs);rng=random.Random(args.seed)
    todo=sorted(range(len(jobs)),key=lambda i:math.dist(jobs[i]['a'],jobs[i]['b']),reverse=True)
    conflicts=[]
    for iteration in range(args.iterations):
        if iteration:
            rng.shuffle(todo)
        for i in todo:
            if soft[i] is not None:
                occ[layers[i]]-=soft[i]
            options=[]
            for layer in (2,4):
                costs=1.+occ[layer]*(6+iteration*8)+hist[layer]*(3+iteration*.5)
                costs[hard[jobs[i]['net']]]=np.inf
                solver=MCP_Geometric(costs,fully_connected=True)
                result,_=solver.find_costs([starts[i]],[ends[i]],find_all_ends=False)
                value=result[ends[i]]
                if math.isfinite(value):
                    options.append((value,layer,compact(solver.traceback(ends[i]))))
            assert options,(jobs[i]['net'],'no path')
            value,layer,path=min(options,key=lambda x:x[0])
            g=LineString(path).buffer(WIDTH/2,quad_segs=24)
            gap=g.distance(forbidden[jobs[i]['net']])
            assert gap>=CLEAR,(jobs[i]['net'],'continuous static gap',gap)
            paths[i]=path;geoms[i]=g;layers[i]=layer
            soft[i]=mask(g.buffer(CLEAR+GUARD,quad_segs=12))
            occ[layer]+=soft[i]
        conflicts=[]
        for i in range(len(jobs)):
            for j in range(i):
                if layers[i]==layers[j]:
                    gap=geoms[i].distance(geoms[j])
                    if gap<CLEAR+.001:
                        conflicts.append((i,j,gap))
                        hist[layers[i]]+=mask(geoms[i].buffer(.18).intersection(geoms[j].buffer(.18)))*.8
        state=dict(source_placement_sha256=source_hash,iteration=iteration,layers=layers,paths=paths,jobs=jobs,conflicts=conflicts,
                   fixed_mapping=fixed_map)
        (H/'dc_fixed_progress.json').write_text(json.dumps(state,indent=2))
        print('FIXED_DC_ITER',iteration,'CONFLICTS',len(conflicts),'LAYERS',[layers.count(l) for l in (2,4)],flush=True)
        if not conflicts:
            break
        todo=sorted({k for a,b,g in conflicts for k in (a,b)})
        if iteration%4==3:
            todo=list(range(len(jobs)))
    if conflicts:
        raise ValueError('Fixed DC routing is incomplete; do not promote this geometry')
    results=[dict(layer=l,routes=[]) for l in (2,4)]
    for i,j in enumerate(jobs):
        r=dict(net=j['net'],layer=layers[i],width=WIDTH,points=paths[i],port=j['port'],source=j['source'])
        results[0 if layers[i]==2 else 1]['routes'].append(r)
        for v in plan['vias']:
            if v['net']==j['net']:
                v.update(assigned_dc_layer=layers[i],routing_layer=layers[i])
    finalize(plan,results)
    saved=json.loads((H/'dc_routed_candidate.json').read_text())
    assert {r['dc_net']:int(r['zif_pin']) for r in saved['pinmap']}==fixed_map


if __name__=='__main__':
    main()
