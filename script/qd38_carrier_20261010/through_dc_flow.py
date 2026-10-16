"""Route DC banks as disjoint flows with freely assignable ZIF contacts.

Unlike independent shortest paths, integral node-capacitated flow keeps the
bank planar and determines the connector assignment from the actual routes.
All geometry is a candidate until continuous copper clearance is checked.
"""
from pathlib import Path
import json
import math
import sys
import time
import numpy as np
import networkx as nx
import shapely
from scipy.ndimage import label as label_regions
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from route_circuit import pgeom
from design_geometry import DEST, H

WIDTH = .125
CLEARANCE = .15
RADIUS = WIDTH / 2 + CLEARANCE + .002
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else .3
OFFSET_X = float(sys.argv[2]) if len(sys.argv) > 2 else .15
OFFSET_Y = float(sys.argv[3]) if len(sys.argv) > 3 else .15


def compact(points):
    result = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = map(np.array, (result[-1], points[i], points[i+1]))
        u, v = b-a, c-b
        if abs(u[0]*v[1]-u[1]*v[0]) > 1e-8:
            result.append(points[i])
    result.append(points[-1])
    return result


def stub_options(a, b):
    x, y = a
    dx, dy = b[0]-x, b[1]-y
    diagonal = min(abs(dx), abs(dy))
    sx, sy = np.sign(dx), np.sign(dy)
    yield compact([a, [x+sx*diagonal, y+sy*diagonal], b])
    yield compact([a, [b[0]-sx*diagonal, b[1]-sy*diagonal], b])


def run_layer(plan, layer):
    t0 = time.monotonic()
    jobs = [j for j in plan['route_jobs'] if j['kind'] == 'DC' and j['layer'] == layer]
    sources = [v for v in plan['vias'] if not v['label'].startswith('J1-') and v['assigned_dc_layer'] == layer]
    ports = [v for v in plan['vias'] if v['label'].startswith('J1-') and v['assigned_dc_layer'] == layer]
    assert len(sources) == len(ports) == len(jobs)
    objects = [(d['net'], pgeom(d)) for d in plan['physical_pads'] if d['layer'] in (layer, 74)]
    objects += [(v['net'], Point(v['x'], v['y']).buffer(v['diameter']/2, quad_segs=24))
                for v in plan['vias'] if v['low'] <= layer <= v['high']]
    objects += [(None, box(7.05, 40.3, 12.45, 44.7))]
    obstacle = unary_union([g.buffer(RADIUS, quad_segs=16) for n,g in objects])
    xs = np.arange(OFFSET_X, 19.5, STEP)
    ys = np.arange(OFFSET_Y, 67.9, STEP)
    xx, yy = np.meshgrid(xs, ys)
    xy = np.column_stack([xx.ravel(), yy.ravel()])
    inside = (xy[:,0] >= .25) & (xy[:,0] <= 19.25) & (xy[:,1] >= .25) & (xy[:,1] <= 67.65)
    available = inside & ~shapely.intersects(shapely.points(xy), obstacle)
    nxg, nyg = len(xs), len(ys)
    regions, _ = label_regions(available.reshape(nyg,nxg))
    sizes=np.bincount(regions.ravel()); sizes[0]=0
    available &= regions.ravel()==int(np.argmax(sizes))
    base=nx.Graph()
    base.add_nodes_from(map(int,np.where(available)[0]))
    pairs=[]
    for k in np.where(available)[0]:
        for j in (k+1 if k%nxg<nxg-1 else -1,k+nxg if k//nxg<nyg-1 else -1):
            if j>=0 and available[j]: pairs.append((int(k),int(j)))
    checks=~shapely.intersects(shapely.linestrings(np.array([[xy[a],xy[b]] for a,b in pairs])),obstacle)
    base.add_edges_from(pair for pair,ok in zip(pairs,checks) if ok)
    giant=max(nx.connected_components(base),key=len)
    available &= np.array([k in giant for k in range(len(xy))])
    terminals = []
    used_stubs = []
    for is_port, candidates in [(False, sources), (True, ports)]:
        for v in sorted(candidates, key=lambda v:(v['y'],v['x'])):
            a = [v['x'], v['y']]
            distances=np.linalg.norm(xy-a,axis=1)
            merit=distances+np.array([(4-base.degree(int(k)))*.22 if k in base else 100 for k in range(len(xy))])
            order = np.argsort(merit)
            others = unary_union([g for n,g in objects if n != v['net']])
            best = None
            for k in order:
                if not available[k]:
                    continue
                if is_port and xy[k,1] < a[1] + .25:
                    continue
                if base.degree(int(k)) < 2:
                    continue
                d = np.linalg.norm(xy[k]-a)
                if d > 2:
                    continue
                for stub in stub_options(a, xy[k].tolist()):
                    copper = LineString(stub).buffer(WIDTH/2, quad_segs=12)
                    if copper.distance(others) < CLEARANCE + .005:
                        continue
                    if any(copper.distance(g) < CLEARANCE + .01 for g in used_stubs):
                        continue
                    best = (int(k), stub, copper)
                    break
                if best:
                    break
            if not best:
                print('NO_ESCAPE_ANCHOR', layer, v['label'], flush=True)
                return {'layer': layer, 'failure': 'no_escape_anchor', 'terminal': v['label']}
            k, stub, copper = best
            terminals.append(dict(port=is_port, via=v, anchor=k, stub=stub))
            used_stubs.append(copper)
            available[k] = False

    # Protect every terminal escape from other routes. Only its exact graph
    # anchor is reinstated; unit capacity prevents another net taking it.
    # Do not isolate every terminal by buffering its end beyond one grid
    # pitch. Continuous geometry below remains the acceptance criterion.
    stub_block = unary_union([g.buffer(CLEARANCE + WIDTH/2 - .000001, quad_segs=12) for g in used_stubs])
    available &= ~shapely.intersects(shapely.points(xy), stub_block)
    for t in terminals:
        available[t['anchor']] = True
    graph = nx.DiGraph()
    graph.add_node('source', demand=-len(sources))
    graph.add_node('sink', demand=len(sources))
    for k in np.where(available)[0]:
        graph.add_edge(int(k)*2, int(k)*2+1, capacity=1, weight=0)
    edge_pairs = []
    for k in np.where(available)[0]:
        for j in (k+1 if k % nxg < nxg-1 else -1, k+nxg if k//nxg < nyg-1 else -1):
            if j >= 0 and available[j]:
                edge_pairs.append((int(k), int(j)))
    segments = shapely.linestrings(np.array([[xy[a],xy[b]] for a,b in edge_pairs]))
    legal = ~shapely.intersects(segments, obstacle)
    for (a,b), ok in zip(edge_pairs,legal):
        if ok:
            graph.add_edge(a*2+1, b*2, capacity=1, weight=100)
            graph.add_edge(b*2+1, a*2, capacity=1, weight=100)
    for i,t in enumerate(terminals):
        k=t['anchor'];node=f't{i}'
        if t['port']:
            graph.add_edge(k*2+1,node,capacity=1,weight=0)
            graph.add_edge(node,'sink',capacity=1,weight=0)
            # No other route can traverse a reserved sink anchor.
            for b in list(graph.successors(k*2+1)):
                if b != node:
                    graph.remove_edge(k*2+1,b)
        else:
            graph.add_edge('source',node,capacity=1,weight=0)
            graph.add_edge(node,k*2,capacity=1,weight=0)
            for a in list(graph.predecessors(k*2)):
                if a != node:
                    graph.remove_edge(a,k*2)
    print('GRAPH',layer,'NODES',len(graph),'EDGES',graph.number_of_edges(),'SECONDS',round(time.monotonic()-t0,2),flush=True)
    try:
        cost,flow = nx.network_simplex(graph)
    except nx.NetworkXUnfeasible:
        value,partial=nx.maximum_flow(graph,'source','sink')
        unmatched=[t['via']['label'] for i,t in enumerate(terminals) if not t['port'] and partial['source'][f't{i}']==0]
        unreachable=[t['via']['label'] for i,t in enumerate(terminals) if not t['port'] and not nx.has_path(graph,f't{i}','sink')]
        cut_value,(reachable,not_reachable)=nx.minimum_cut(graph,'source','sink')
        cuts=[]
        for a in reachable:
            for b in graph.successors(a):
                if b in not_reachable:
                    cuts.append(dict(a=str(a),b=str(b),xy=xy[a//2].tolist() if isinstance(a,int) else None))
        print('INSUFFICIENT_FLOW',layer,value,'/',len(sources),flush=True)
        print('UNMATCHED',unmatched,'UNREACHABLE',unreachable,flush=True)
        print('CUT_XY',[c['xy'] for c in cuts if c['xy']],flush=True)
        return dict(layer=layer,failure='insufficient_flow',connected=value,required=len(sources),terminals=terminals,unmatched=unmatched,unreachable=unreachable,cut=cuts)
    routes=[]
    for i,t in enumerate(terminals):
        if t['port']:
            continue
        node=f't{i}';seen=set();path=[]
        while node != 'sink':
            assert node not in seen
            seen.add(node)
            following=[b for b,n in flow[node].items() if n > 0]
            assert len(following)==1,(node,following)
            node=following[0]
            if isinstance(node,int) and node%2==0:
                path.append(xy[node//2].tolist())
            if isinstance(node,str) and node.startswith('t'):
                end=terminals[int(node[1:])]
        points=compact(t['stub']+path[1:]+list(reversed(end['stub']))[1:])
        routes.append(dict(net=t['via']['net'],layer=layer,width=WIDTH,
                           port=end['via']['label'],points=points,
                           source=t['via']['label']))
    failures=[]
    copper=[LineString(r['points']).buffer(WIDTH/2,quad_segs=16) for r in routes]
    for i,a in enumerate(copper):
        for j in range(i):
            d=a.distance(copper[j])
            if d < CLEARANCE-1e-7:
                failures.append(dict(a=routes[i]['net'],b=routes[j]['net'],gap=d))
        same={routes[i]['net'],next(v['net'] for v in ports if v['label']==routes[i]['port'])}
        # The destination contact will be reassigned to the source net.
        destination=next(v for v in ports if v['label']==routes[i]['port'])
        for v in plan['vias']:
            if v['low']<=layer<=v['high'] and v is not destination and v['net']!=routes[i]['net']:
                d=a.distance(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=24))
                if d < CLEARANCE-1e-7:
                    failures.append(dict(a=routes[i]['net'],b=v['label'],gap=d))
        for pad in plan['physical_pads']:
            if pad['layer'] in (layer,74) and pad['net']!=routes[i]['net']:
                d=a.distance(pgeom(pad))
                if d < CLEARANCE-1e-7:
                    failures.append(dict(a=routes[i]['net'],b=f"{pad['ref']}-{pad['pin']}",gap=d))
    print('FLOW_RESULT',layer,'ROUTES',len(routes),'CONFLICTS',len(failures),'SECONDS',round(time.monotonic()-t0,2),flush=True)
    return dict(layer=layer,routes=routes,clearance_failures=failures,terminals=terminals,cost=cost)


def main():
    plan=json.loads((H/'through_dc_input.json').read_text())
    results=[]
    for layer in (2,4):
        result=run_layer(plan,layer)
        results.append(result)
        (H/f'through_dc_flow_L{layer}_{STEP}_{OFFSET_X}_{OFFSET_Y}.json').write_text(json.dumps(result,indent=2))
    passed=all(not r.get('failure') and not r.get('clearance_failures') for r in results)
    (H/f'through_dc_candidate_{STEP}_{OFFSET_X}_{OFFSET_Y}.json').write_text(json.dumps(dict(passed=passed,layers=results,grid=STEP,offset=[OFFSET_X,OFFSET_Y]),indent=2))
    print('ALL_DC_FLOW_PASSED',passed,flush=True)


if __name__=='__main__':
    main()
