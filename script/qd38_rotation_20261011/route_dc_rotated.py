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
import hashlib
import numpy as np
import networkx as nx
import shapely
from scipy.ndimage import label as label_regions
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate

H = Path(__file__).resolve().parent


def pgeom(d):
    if d['shape'] == 'round':
        return Point(d['x'], d['y']).buffer(d['sx']/2, quad_segs=48)
    return translate(rotate(box(-d['sx']/2, -d['sy']/2, d['sx']/2, d['sy']/2),
                            d['rotation'], origin=(0, 0)), d['x'], d['y'])


def smp_envelopes(plan):
    """Forbid the complete five-pad body envelope, not just its hole lands."""
    refs=sorted({p['ref'] for p in plan['physical_pads'] if str(p['ref']).startswith('SMP')})
    envelopes={}
    for ref in refs:
        pads=[pgeom(p) for p in plan['physical_pads'] if p['ref']==ref]
        assert len(pads)==5,(ref,len(pads))
        envelopes[ref]=unary_union(pads).convex_hull
    assert len(envelopes)==16
    return envelopes


def rc_envelopes(plan,net=None):
    """Exclude resistor bodies on DC layers; allow the own R2 entry pad."""
    refs=sorted({p['ref'] for p in plan['physical_pads'] if p['ref'] and p['ref'][0] in 'RC' and p['ref'][1:].isdigit()})
    result={}
    for ref in refs:
        if '--include-cbodies' not in sys.argv and ref.startswith('C'):
            continue
        pads=[p for p in plan['physical_pads'] if p['ref']==ref]
        assert len(pads)==2,(ref,len(pads))
        hull=unary_union([pgeom(p) for p in pads]).convex_hull
        if ref.startswith('R'):
            own=next(p for p in pads if p['pin']=='2')
            if net and net.startswith('DC') and own['net']==net:
                hull=hull.difference(pgeom(own))
        result[ref]=hull
    return result

WIDTH = .125
CLEARANCE = .10
GUARD = .003


def required_gap(net):
    if net and net.startswith('DC'):
        return .10
    return .20 if net=='GND' else .15


def normalized_obstacle(net,g):
    """Normalize category-specific clearance to the 0.10 mm DC baseline."""
    extra=required_gap(net)-CLEARANCE
    return g.buffer(extra,quad_segs=32) if extra>0 else g
STEP = float(sys.argv[1]) if len(sys.argv) > 1 else .3
OFFSET_X = float(sys.argv[2]) if len(sys.argv) > 2 else .15
OFFSET_Y = float(sys.argv[3]) if len(sys.argv) > 3 else .15


def compact(points):
    points = [p for i,p in enumerate(points) if not i or math.dist(p,points[i-1]) > 1e-8]
    if len(points) < 3:
        return points
    result = [points[0]]
    for i in range(1, len(points) - 1):
        a, b, c = map(np.array, (result[-1], points[i], points[i+1]))
        u, v = b-a, c-b
        if abs(u[0]*v[1]-u[1]*v[0]) > 1e-8 or np.dot(u,v) < 0:
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


def turns(points):
    result = []
    for i in range(1, len(points)-1):
        a,b,c = map(np.array, points[i-1:i+2])
        u,v = b-a,c-b
        z = float(u[0]*v[1]-u[1]*v[0]); dot = float(np.dot(u,v))
        result.append((i, math.degrees(math.atan2(z,dot))))
    return result


def bend_score(points):
    # Count an unchamfered right angle as its two required 45-degree turns.
    return sum(round(abs(t)/45) for _,t in turns(points))*1000+LineString(points).length


def minimum_bend_shortcut(points, forbidden, boundary):
    """Find the fewest-turn visible octilinear path through ordered vertices.

    Every candidate edge is checked against the complete continuous copper
    exclusion. The dynamic program retains incoming direction, prioritizing
    turn count lexicographically over route length. This is independent of
    grid shortest-path length, which alone creates arbitrary staircases.
    """
    def direction(a,b):
        return int(round(math.atan2(b[1]-a[1],b[0]-a[0])*4/math.pi))%8
    def delta(a,b):
        return min((a-b)%8,(b-a)%8)
    n=len(points)
    candidates=[]
    for a in range(n-1):
        for b in range(a+1,n):
            for middle in stub_options(points[a],points[b]):
                if len(middle)<2:
                    continue
                candidates.append((a,b,middle))
    centerlines=np.array([LineString(mid) for a,b,mid in candidates],dtype=object)
    copper=shapely.buffer(centerlines,WIDTH/2,quad_segs=16)
    accepted=(shapely.distance(copper,forbidden)>=CLEARANCE+GUARD-1e-8)&shapely.covers(boundary,copper)
    edges={a:[] for a in range(n)}
    for (a,b,mid),valid in zip(candidates,accepted):
        if valid:
            dirs=[direction(x,y) for x,y in zip(mid,mid[1:])]
            intrinsic=sum(delta(x,y) for x,y in zip(dirs,dirs[1:]))
            edges[a].append((b,mid,dirs[0],dirs[-1],intrinsic*1000+LineString(mid).length))
    best=[{} for _ in range(n)];best[0][None]=(0,None)
    for a in range(n-1):
        for incoming,(cost,_) in list(best[a].items()):
            for b,mid,first,last,edgecost in edges[a]:
                turn=0 if incoming is None else delta(incoming,first)
                if turn>3:
                    continue
                value=cost+edgecost+turn*1000
                if last not in best[b] or value<best[b][last][0]-1e-7:
                    best[b][last]=(value,(a,incoming,mid))
    if not best[-1]:
        return points
    direction_end=min(best[-1],key=lambda d:best[-1][d][0])
    chunks=[];at=n-1
    while at:
        prev,prevdir,mid=best[at][direction_end][1]
        chunks.append(mid);at,direction_end=prev,prevdir
    result=compact([p for mid in reversed(chunks) for p in mid])
    return result if bend_score(result)<bend_score(points)-1e-7 else points


def finalize(plan, results):
    """Reassign contacts, simplify planar flow and audit every continuous route."""
    routes = [r for result in results for r in result['routes']]
    mapping = {r['port'].split('-')[1]: r['net'] for r in routes}
    assert len(routes) == len(mapping) == 38 and '50' not in mapping
    if plan.get('user_confirmed_contact_pool'):
        selected={int(n) for n in mapping}
        assert selected == set(range(2,50,2)) | set(range(1,28,2))
    for p in plan['physical_pads']:
        if p['ref'] == 'J1':
            p['net'] = mapping.get(p['pin'])
    for v in plan['vias']:
        if v['label'].startswith('J1-'):
            v['net'] = mapping[v['label'].split('-')[1]]
    for r in routes:
        for v in plan['vias']:
            if v['label'] in (r['source'],r['port']):
                v.update(assigned_dc_layer=r['layer'],routing_layer=r['layer'])
    obstacle_cache = {}
    for r in routes:
        obs = [normalized_obstacle(p['net'],pgeom(p)) for p in plan['physical_pads']
               if p['layer'] in (r['layer'],74) and p['net'] != r['net']]
        obs += [normalized_obstacle(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48))
                for v in plan['vias'] if v['low']<=r['layer']<=v['high'] and v['net'] != r['net']]
        obs += [normalized_obstacle(None,box(7.6,39.85,11.9,45.15))]
        obs += [normalized_obstacle(None,g) for g in smp_envelopes(plan).values()]
        obs += [normalized_obstacle(None,g) for g in rc_envelopes(plan,r['net']).values()]
        obstacle_cache[r['net']] = unary_union(obs)
    copper = [LineString(r['points']).buffer(WIDTH/2,quad_segs=32) for r in routes]
    routing_boundary = Polygon(plan['board_outline']).buffer(-.2)

    def legal(points, i, margin=GUARD):
        g = LineString(points).buffer(WIDTH/2,quad_segs=32)
        if g.distance(obstacle_cache[routes[i]['net']]) < CLEARANCE + margin - 1e-8:
            return False
        if not routing_boundary.covers(g):
            return False
        for j,other in enumerate(copper):
            if j != i and routes[j]['layer'] == routes[i]['layer'] and g.distance(other) < CLEARANCE + margin - 1e-8:
                return False
        return True

    raw_bend_score=sum(bend_score(r['points'])//1000 for r in routes)
    for sweep in range(12):
        changes=0
        order=list(range(len(routes)))
        if sweep%2:
            order.reverse()
        for i in order:
            r=routes[i]
            blocked=unary_union([obstacle_cache[r['net']]]+[copper[j] for j in range(len(routes)) if j!=i and routes[j]['layer']==r['layer']])
            q=minimum_bend_shortcut(r['points'],blocked,routing_boundary)
            if bend_score(q)<bend_score(r['points'])-1e-7:
                r['points']=q;copper[i]=LineString(q).buffer(WIDTH/2,quad_segs=32);changes+=1
        print('MINIMUM_BEND_SWEEP',sweep,'CHANGES',changes,'45_TURNS',sum(bend_score(r['points'])//1000 for r in routes),flush=True)
        if not changes:
            break

    # Remove needless grid staircases with exact H/V/45 shortcuts. The
    # complete source/target path is rechecked for each accepted shortcut.
    for sweep in range(3):
        changes = 0
        for i,r in enumerate(routes):
            p = r['points']; a = 0
            while a < len(p)-2:
                found = False
                for b in range(len(p)-1,a+1,-1):
                    if b <= a+1:
                        break
                    for middle in stub_options(p[a],p[b]):
                        if len(middle) >= b-a+1:
                            continue
                        joins=compact(p[max(0,a-1):a]+middle+p[b+1:b+2])
                        if any(abs(t)>135.01 for _,t in turns(joins)):
                            continue
                        if legal(middle,i) and bend_score(compact(p[:a]+middle+p[b+1:]))<bend_score(p)-1e-7:
                            q = compact(p[:a]+middle+p[b+1:])
                            p=q; copper[i]=LineString(p).buffer(WIDTH/2,quad_segs=32)
                            changes += 1; found = True; break
                    if found:
                        break
                if not found:
                    a += 1
            r['points'] = p
        print('DC_SHORTCUT_SWEEP',sweep,'CHANGES',changes,flush=True)
        if not changes:
            break

    chamfers = []
    for i,r in enumerate(routes):
        p=r['points']; k=1
        while k < len(p)-1:
            a,b,c=map(np.array,p[k-1:k+2]);u=b-a;v=c-b
            lu,lv=np.linalg.norm(u),np.linalg.norm(v);u/=lu;v/=lv
            delta=math.atan2(float(u[0]*v[1]-u[1]*v[0]),float(np.dot(u,v)))
            if abs(math.degrees(delta)) <= 45.01:
                k+=1;continue
            if abs(math.degrees(delta)) > 135.01:
                k+=1;continue
            accepted=False
            # Quantified adaptive chamfers are all exactly 45 degrees. A
            # small value is explicitly reported, never hidden as success.
            for t in [.20,.15,.10,.075,.05,.025,.01,.005,.002]:
                t=min(t,lu*.4,lv*.4)
                p0=b-t*u;p1=b+t*v
                sign=1 if delta>0 else -1
                count=int(round(abs(math.degrees(delta))/45))-1
                theta=math.atan2(u[1],u[0])
                vectors=np.array([[math.cos(theta+sign*j*math.pi/4),math.sin(theta+sign*j*math.pi/4)] for j in range(1,count+1)])
                length=float(np.dot(p1-p0,np.sum(vectors,axis=0))/np.dot(np.sum(vectors,axis=0),np.sum(vectors,axis=0)))
                mid=[p0.tolist()];cur=p0.copy()
                for vector in vectors:
                    cur+=length*vector;mid.append(cur.tolist())
                if math.dist(mid[-1],p1)>1e-6:
                    continue
                q=compact(p[:k]+mid+p[k+1:])
                if legal(mid,i):
                    chamfers.append(dict(net=r['net'],at=b.tolist(),trim_mm=float(t),original_turn_deg=abs(math.degrees(delta))))
                    p=q;copper[i]=LineString(p).buffer(WIDTH/2,quad_segs=32);accepted=True
                    k+=len(mid);break
            if not accepted:
                k+=1
        r['points']=p

    failures=[];minimum=100.;bad_turns=[];bad_directions=[];endpoint_checks=[]
    for i,r in enumerate(routes):
        g=copper[i]; d=g.distance(obstacle_cache[r['net']]);minimum=min(minimum,d)
        if d < CLEARANCE-1e-7:
            failures.append(dict(net=r['net'],other='static',gap=d))
        for j in range(i):
            if routes[j]['layer']==r['layer']:
                d=g.distance(copper[j]);minimum=min(minimum,d)
                if d<CLEARANCE-1e-7:
                    failures.append(dict(net=r['net'],other=routes[j]['net'],gap=d))
        for k,t in turns(r['points']):
            if abs(t)>45.01:
                bad_turns.append(dict(net=r['net'],index=k,turn_deg=t,xy=r['points'][k]))
        for a,b in zip(r['points'],r['points'][1:]):
            dx,dy=abs(b[0]-a[0]),abs(b[1]-a[1])
            if min(dx,dy,abs(dx-dy))>1e-7:
                bad_directions.append(dict(net=r['net'],a=a,b=b))
        endpoints=[v for v in plan['vias'] if v['label'] in (r['source'],r['port'])]
        touches=[g.intersects(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48)) for v in endpoints]
        endpoint_checks.append(dict(net=r['net'],source=r['source'],port=r['port'],connected=len(endpoints)==2 and all(touches)))
    plan['tracks']=[t for t in plan['tracks'] if t['layer'] not in (1,2,4)]
    for v in plan['vias']:
        if v['label'].startswith('J1-'):
            pin=v['label'].split('-')[1]
            pad=next(p for p in plan['physical_pads'] if p['ref']=='J1' and p['pin']==pin)
            plan['tracks'].append(dict(net=v['net'],layer=1,width=.15,a=[pad['x'],pad['y']],b=[v['x'],v['y']]))
    plan['dc_routed_jobs']=[]
    for r in routes:
        number=int(r['net'][2:]);pin=int(r['port'].split('-')[1])
        row=next(row for row in plan['pinmap'] if row['qd_pad']==number)
        row['zif_pin']=pin;row['dc_layer']=r['layer']
        plan['dc_endpoints'][str(number)].update(zif_pin=pin,layer=r['layer'])
        job=next(j for j in plan['route_jobs'] if j['kind']=='DC' and j['net']==r['net'])
        job.update(a=r['points'][-1],b=r['points'][0],layer=r['layer'])
        plan['tracks'].extend(dict(net=r['net'],layer=r['layer'],width=WIDTH,a=a,b=b) for a,b in zip(r['points'],r['points'][1:]))
        plan['dc_routed_jobs'].append(dict(job=job,points=list(reversed(r['points']))))
    plan['nets']={}
    for p in plan['physical_pads']:
        if p['ref'] and p['net']:
            plan['nets'].setdefault(p['net'],[]).append(p['ref']+'-'+p['pin'])
    audit=dict(routes=len(routes),clearance_mm=minimum,clearance_failures=failures,turns_over45=bad_turns,
               non_H_V_45_segments=bad_directions,intermediate_vias=0,zif_pin50_unused='50' not in mapping,
               chamfer_count=len(chamfers),minimum_chamfer_trim_mm=min([v['trim_mm'] for v in chamfers],default=None),
               raw_45_turn_equivalent_count=raw_bend_score,
               final_45_turn_count=sum(sum(abs(t)>1 for _,t in turns(r['points'])) for r in routes),
               full_smp_five_pad_hull_exclusion=True,
               endpoint_checks=endpoint_checks,fixed_mapping=bool(plan.get('fixed_zif_assignments_approved')),
               user_confirmed_contact_pool=bool(plan.get('user_confirmed_contact_pool')),
               used_even_pins=sorted(int(n) for n in mapping if int(n)%2==0),
               used_odd_pins=sorted(int(n) for n in mapping if int(n)%2),
               chamfers=chamfers,passed=not failures and not bad_turns and not bad_directions and all(c['connected'] for c in endpoint_checks))
    plan['dc_routing_validation']=audit
    (H/'dc_audit.json').write_text(json.dumps(audit,indent=2))
    (H/'dc_routed_candidate.json').write_text(json.dumps(plan,indent=2))
    print('DC_FINAL',json.dumps({k:v for k,v in audit.items() if k not in ['chamfers','clearance_failures','turns_over45','non_H_V_45_segments']}),flush=True)


def run_layer(plan, layer):
    t0 = time.monotonic()
    joint='--joint-build' in sys.argv
    jobs = [j for j in plan['route_jobs'] if j['kind'] == 'DC' and (joint or j['layer'] == layer)]
    sources = [v for v in plan['vias'] if not v['label'].startswith('J1-') and (joint or v['assigned_dc_layer'] == layer)]
    ports = [v for v in plan['vias'] if v['label'].startswith('J1-') and (joint or v['assigned_dc_layer'] == layer)]
    assert len(sources) == len(ports) == len(jobs)
    objects = [(d['net'], pgeom(d)) for d in plan['physical_pads'] if d['layer'] in (layer, 74)]
    objects += [(v['net'], Point(v['x'], v['y']).buffer(v['diameter']/2, quad_segs=24))
                for v in plan['vias'] if v['low'] <= layer <= v['high']]
    # Rotated blind pocket plus 0.05 mm geometric milling allowance. The
    # larger non-Top GND exclusion applies to GND polygons, not signal pads.
    objects += [(None, box(7.55, 39.8, 11.95, 45.2))]
    objects += [(None,g) for g in smp_envelopes(plan).values()]
    body_objects=[(None,g) for g in rc_envelopes(plan).values()]
    obstacle = unary_union([g.buffer(WIDTH/2+required_gap(n)+GUARD, quad_segs=24) for n,g in objects+body_objects])
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
            others = unary_union([normalized_obstacle(n,g) for n,g in objects if n != v['net']]+
                                 [normalized_obstacle(None,g) for g in rc_envelopes(plan,v['net']).values()])
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
                    if copper.distance(others) < CLEARANCE + GUARD:
                        continue
                    if any(copper.distance(g) < CLEARANCE + GUARD for g in used_stubs):
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
    stub_block = unary_union([g.buffer(CLEARANCE + GUARD + WIDTH/2 - .000001, quad_segs=12) for g in used_stubs])
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
            # Penalize prolonged outer-edge runs meaningfully: at a 9 mm
            # lateral offset the same axial length costs 90% more. A later
            # direction-state shortcut minimizes bends in the chosen bank.
            central=1000 if '--central' in sys.argv else 2
            weight = 10000 + (round(abs(xy[a,0]-9.75)*central) if a%nxg==b%nxg else 0)
            graph.add_edge(a*2+1, b*2, capacity=1, weight=weight)
            graph.add_edge(b*2+1, a*2, capacity=1, weight=weight)
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
    if joint:
        return dict(graph=graph,terminals=terminals,xy=xy)
    if '--capacity-only' in sys.argv:
        value,partial=nx.maximum_flow(graph,'source','sink')
        unmatched=[t['via']['label'] for i,t in enumerate(terminals) if not t['port'] and partial['source'][f't{i}']==0]
        unreachable=[t['via']['label'] for i,t in enumerate(terminals) if not t['port'] and not nx.has_path(graph,f't{i}','sink')]
        _,(reachable,not_reachable)=nx.minimum_cut(graph,'source','sink')
        cuts=[]
        for a in reachable:
            for b in graph.successors(a):
                if b in not_reachable:
                    cuts.append(dict(a=str(a),b=str(b),xy=xy[a//2].tolist() if isinstance(a,int) else None))
        print('CAPACITY_PROBE',layer,value,'/',len(sources),flush=True)
        print('UNMATCHED',unmatched,'UNREACHABLE',unreachable,'CUT_XY',[c['xy'] for c in cuts if c['xy']],flush=True)
        return dict(layer=layer,failure='capacity_probe',connected=value,required=len(sources),unmatched=unmatched,unreachable=unreachable,cut=cuts,terminals=terminals)
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
                if d < required_gap(v['net'])-1e-7:
                    failures.append(dict(a=routes[i]['net'],b=v['label'],gap=d))
        for pad in plan['physical_pads']:
            if pad['layer'] in (layer,74) and pad['net']!=routes[i]['net']:
                d=a.distance(pgeom(pad))
                if d < required_gap(pad['net'])-1e-7:
                    failures.append(dict(a=routes[i]['net'],b=f"{pad['ref']}-{pad['pin']}",gap=d))
    print('FLOW_RESULT',layer,'ROUTES',len(routes),'CONFLICTS',len(failures),'SECONDS',round(time.monotonic()-t0,2),flush=True)
    return dict(layer=layer,routes=routes,clearance_failures=failures,terminals=terminals,cost=cost)


def main():
    approved_pool='--pooled' in sys.argv
    if not approved_pool and '--explore-permutation' not in sys.argv:
        raise SystemExit('Free contact reassignment was superseded. Use route_dc_fixed.py with the verified fixed mapping. Add --explore-permutation only for an explicitly non-production bottleneck study.')
    source=H/('pooled_placement_candidate.json' if approved_pool else 'placement_candidate.json')
    for arg in sys.argv:
        if arg.startswith('--source='):
            source=Path(arg.split('=',1)[1])
    plan=json.loads(source.read_text())
    if approved_pool:
        assert plan.get('user_confirmed_contact_pool')
        pins={int(v['label'].split('-')[1]) for v in plan['vias'] if v['label'].startswith('J1-')}
        assert pins == set(range(2,50,2)) | set(range(1,28,2))
    suffix='_stagger' if '--stagger-j1' in sys.argv else ''
    if '--stagger-j1' in sys.argv:
        for v in plan['vias']:
            if v['label'].startswith('J1-') and int(v['label'].split('-')[1])%4==0:
                v['y']+=.70
        plan['j1_fanout_alternating_even_via_rows_mm']=[6.75,7.45]
        for t in plan['tracks']:
            if t['layer']==1:
                v=next(v for v in plan['vias'] if v['net']==t['net'] and v['label'].startswith('J1-'))
                t['b']=[v['x'],v['y']]
    if '--central' in sys.argv:
        suffix+='_central'
        plan['dc_outer_run_cost_factor_per_mm_x_offset']=.1
    if '--alternate-sources' in sys.argv:
        suffix+='_alternate'
        plan['dc_endpoint_bank_policy']='Alternating sources by spatial X/Y order; 19 nets per internal layer'
    suffix+='_rbody'
    if '--capacity-only' in sys.argv:
        suffix+='_probe'
    plan['dc_resistor_body_hull_exclusion_all_internal_layers']=True
    plan['dc_capacitor_body_hull_exclusion_all_internal_layers']='--include-cbodies' in sys.argv
    source_hash=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    plan['dc_source_placement_sha256']=source_hash
    plan['dc_smp_full_five_pad_hull_exclusion']=True
    plan['dc_resistor_body_hull_exclusion_all_internal_layers']=True
    # Rotating the device also rotates its natural terminal banks. Reassign
    # the one permitted inner layer per net to its spatial left/right bank;
    # preserve the existing number of connector ports on each inner layer.
    source_vias=sorted([v for v in plan['vias'] if not v['label'].startswith('J1-')],key=lambda v:(v['x'],v['y']))
    first_count=sum(v['label'].startswith('J1-') and v['assigned_dc_layer']==2 for v in plan['vias'])
    for i,v in enumerate(source_vias):
        layer=2 if i<first_count else 4
        if '--alternate-sources' in sys.argv:
            layer=2 if i%2==0 else 4
        for arg in sys.argv:
            if arg.startswith('--swap='):
                left,right=arg.split('=',1)[1].split(':')
                if v['label']==left:
                    layer=4
                elif v['label']==right:
                    layer=2
        v.update(assigned_dc_layer=layer,routing_layer=layer)
        n=str(int(v['net'][2:]))
        plan['dc_endpoints'][n]['layer']=layer
        next(row for row in plan['pinmap'] if row['dc_net']==v['net'])['dc_layer']=layer
        next(j for j in plan['route_jobs'] if j['kind']=='DC' and j['net']==v['net'])['layer']=layer
    results=[]
    if '--finalize' in sys.argv:
        result=json.loads((H/f'dc_flow_{STEP}_{OFFSET_X}_{OFFSET_Y}{suffix}.json').read_text())
        assert approved_pool and result['passed'] and result['source_placement_sha256']==source_hash
        finalize(plan,result['layers'])
        return
    for layer in (2,4):
        result=run_layer(plan,layer)
        results.append(result)
        (H/f'dc_flow_L{layer}_{STEP}_{OFFSET_X}_{OFFSET_Y}{suffix}.json').write_text(json.dumps(result,indent=2))
    passed=all(not r.get('failure') and not r.get('clearance_failures') for r in results)
    (H/f'dc_flow_{STEP}_{OFFSET_X}_{OFFSET_Y}{suffix}.json').write_text(json.dumps(dict(passed=passed,layers=results,grid=STEP,offset=[OFFSET_X,OFFSET_Y],source_placement_sha256=source_hash),indent=2))
    print('ALL_DC_FLOW_PASSED',passed,flush=True)
    # Exploratory free pools never emit a final candidate. The user approved
    # free chip-function assignment only within all 24 existing even contacts
    # plus 14 new odd contacts; that explicit pool may be finalized.
    if approved_pool and passed:
        finalize(plan,results)


if __name__=='__main__':
    main()
