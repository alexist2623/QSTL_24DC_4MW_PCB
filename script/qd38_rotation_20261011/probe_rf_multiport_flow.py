"""Probe free RF terminal assignment using mutually disjoint planar paths.

This is an offline routing diagnostic. It never changes physical placement or
native design files. A successful flow still needs tangent smoothing and audit.
"""
from pathlib import Path
import argparse
import json
import math
import time
import hashlib
import numpy as np
import networkx as nx
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr

H=Path(__file__).resolve().parent

def alternatives(a,b):
    yield [a,list(b)]
    dx,dy=np.subtract(b,a);d=min(abs(dx),abs(dy));sx,sy=np.sign((dx,dy))
    for mid in ([a,[a[0]+sx*d,a[1]+sy*d],b],
                [a,[b[0]-sx*d,b[1]-sy*d],b]):
        yield rr.strip_collinear(mid)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--placement',type=Path,default=H/'placement_lower_over_smp_candidate.json')
    ap.add_argument('--reference',type=Path,default=H/'rf_lower_over_smp_progress.json')
    ap.add_argument('--step',type=float,default=.28)
    ap.add_argument('--offset',type=float,default=.14)
    ap.add_argument('--y-offset',type=float)
    ap.add_argument('--output',type=Path,default=H/'rf_multiport_flow_diagnostic.json')
    ap.add_argument('--ports',type=int,default=16)
    ap.add_argument('--resolve-stubs',action='store_true')
    ap.add_argument('--solve-seconds',type=float,default=120)
    args=ap.parse_args();t0=time.monotonic()
    placement_bytes=args.placement.read_bytes();reference_bytes=args.reference.read_bytes()
    reference_snapshot=H/('rf_flow_reference_'+hashlib.sha256(reference_bytes).hexdigest()[:16]+'.json')
    if not reference_snapshot.exists():reference_snapshot.write_bytes(reference_bytes)
    p=json.loads(placement_bytes);routes=json.loads(reference_bytes)['routes']
    fixed=[r for r in routes if r['job']['kind']!='RF_QD']
    pads={(d['ref'],str(d['pin'])):d for d in p['physical_pads'] if d['ref']}
    groups=sorted(int(s['ref'][3:]) for s in p['smp'])
    bottom_pads=[d for d in p['physical_pads'] if d['layer'] in (32,74)]
    objects={(f"pad:{d['ref']}-{d['pin']}" if d['ref'] else f"pad:free:{i}:{d['pin']}"):rr.pgeom(d) for i,d in enumerate(bottom_pads)}
    assert len(objects)==len(bottom_pads),'Duplicate pad identity in obstacle dictionary'
    objects.update({'via:'+v['label']:Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32) for v in p['vias']})
    assert len(objects)==len(bottom_pads)+len(p['vias']),'A via or pad obstacle was overwritten'
    for s in p['smp']:
        objects['ring:'+s['ref']]=Point(s['x'],s['y']).buffer(1.175,quad_segs=64)
    cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];objects['cavity']=box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)
    for g in groups:
        objects[f'hull:R{g:02}']=unary_union([rr.pgeom(pads[(f'R{g:02}',str(pin))]) for pin in (1,2)]).convex_hull
    for r in fixed:
        objects['fixed:'+r['job']['net']+':'+r['job']['kind']]=rr.copper(r['tracks'],r['arcs'])
    assert sum(k.startswith('pad:') for k in objects)==len(bottom_pads)
    assert sum(k.startswith('via:') for k in objects)==len(p['vias'])
    boundary=Polygon(p['board_outline']).buffer(-.22)
    obstacle=unary_union(list(objects.values())).buffer(.212,quad_segs=24)
    y_offset=args.offset if args.y_offset is None else args.y_offset
    xs=np.arange(args.offset,19.5,args.step);ys=np.arange(20+y_offset,66,args.step)
    xy=np.array([(x,y) for y in ys for x in xs]);nxg=len(xs);nyg=len(ys)
    points=shapely.points(xy)
    available=~shapely.intersects(points,obstacle)&shapely.covers(boundary,points)
    base=nx.Graph();base.add_nodes_from(map(int,np.where(available)[0]));pairs=[]
    for k in np.where(available)[0]:
        for j in (k+1 if k%nxg<nxg-1 else -1,k+nxg if k//nxg<nyg-1 else -1):
            if j>=0 and available[j]:pairs.append((int(k),int(j)))
    checks=~shapely.intersects(shapely.linestrings(np.array([[xy[a],xy[b]] for a,b in pairs])),obstacle)
    base.add_edges_from(pair for pair,ok in zip(pairs,checks) if ok)
    giant=max(nx.connected_components(base),key=len);available &= np.array([k in giant for k in range(len(xy))])
    terminals=[]
    jobs=sorted([r['job'] for r in routes if r['job']['kind']=='RF_QD'],key=lambda j:(j['a'][1],j['a'][0]))
    # The RF_QD jobs run from QD to resistor in the established schema.
    for is_port in (False,True):
        for j in jobs:
            group=int(j['net'][2:]);key=('pad:'+ (f'Q1-{group}' if is_port else f'R{group:02}-1'))
            a=list(j['a'] if is_port else j['b']);terminal=objects[key]
            blockers=[]
            for label,shape in objects.items():
                if label==key:continue
                if not is_port and label in (f'hull:R{group:02}',f'fixed:MW{group:02}:RF_BIAS'):
                    shape=shape.difference(terminal)
                blockers.append(shape)
            blocked=unary_union(blockers)
            distances=np.linalg.norm(xy-a,axis=1)
            merit=distances+np.array([(4-base.degree(int(k)))*.10 if k in base else 100 for k in range(len(xy))])
            options=[]
            for k in np.argsort(merit):
                if not available[k] or distances[k]>2.5 or base.degree(int(k))<2:continue
                for stub in alternatives(a,xy[k].tolist()):
                    copper=LineString(stub).buffer(.055,quad_segs=24)
                    if copper.distance(blocked)<.154 or not boundary.covers(copper):continue
                    options.append(dict(anchor=int(k),stub=stub));break
                if len(options)>=args.ports:break
            if not options:
                report=dict(passed=False,failure='no_terminal_escape',terminal=key,step=args.step,offset=args.offset)
                args.output.write_text(json.dumps(report,indent=2));print(report,flush=True);return
            terminals.append(dict(port=is_port,group=group,key=key,point=a,options=options))
    graph=nx.DiGraph();graph.add_node('source',demand=-16);graph.add_node('sink',demand=16)
    for k in np.where(available)[0]:graph.add_edge(int(k)*2,int(k)*2+1,capacity=1,weight=0)
    for a,b in base.edges():
        if available[a] and available[b]:
            graph.add_edge(a*2+1,b*2,capacity=1,weight=1000)
            graph.add_edge(b*2+1,a*2,capacity=1,weight=1000)
    for i,t in enumerate(terminals):
        node=f't{i}'
        if t['port']:
            graph.add_edge(node,'sink',capacity=1,weight=0)
            for o in t['options']:
                k=o['anchor'];graph.add_edge(k*2+1,node,capacity=1,weight=round(LineString(o['stub']).length/args.step*1000))
        else:
            graph.add_edge('source',node,capacity=1,weight=0)
            for o in t['options']:
                k=o['anchor'];graph.add_edge(node,k*2,capacity=1,weight=round(LineString(o['stub']).length/args.step*1000))
    direct={}
    for i,t in enumerate(terminals):
        if t['port']:continue
        group=t['group'];terminal=objects[t['key']]
        for j,u in enumerate(terminals):
            if not u['port'] or math.dist(t['point'],u['point'])>4.5:continue
            blockers=[]
            for label,shape in objects.items():
                if label in (t['key'],u['key']):continue
                if label in (f'hull:R{group:02}',f'fixed:MW{group:02}:RF_BIAS'):shape=shape.difference(terminal)
                blockers.append(shape)
            blocked=unary_union(blockers)
            for stub in alternatives(t['point'],u['point']):
                cu=LineString(stub).buffer(.055,quad_segs=24)
                if cu.distance(blocked)<.154 or not boundary.covers(cu):continue
                direct[(i,j)]=stub
                graph.add_edge(f't{i}',f't{j}',capacity=1,weight=round(LineString(stub).length/args.step*1000))
                break
    capacity,flow=nx.maximum_flow(graph,'source','sink')
    constrained_result=None
    if capacity==16 and args.resolve_stubs:
        from solve_rf_stub_conflicts import solve
        constrained_result=solve(graph,xy,terminals,direct,args.solve_seconds)
        if constrained_result['flow'] is not None:flow=constrained_result['flow']
    print('RF_PLANAR_CAPACITY',capacity,'/16',round(time.monotonic()-t0,1),flush=True)
    cut_capacity,(reachable,unreachable)=nx.minimum_cut(graph,'source','sink')
    cut=[]
    for a in reachable:
        for b,e in graph[a].items():
            if b not in unreachable:continue
            record=dict(a=a,b=b,capacity=e['capacity'])
            if isinstance(a,int) and isinstance(b,int):record['xy']=xy[a//2].tolist()
            elif isinstance(a,str) and a.startswith('t'):record['terminal']=terminals[int(a[1:])]['key']
            elif isinstance(b,str) and b.startswith('t'):record['terminal']=terminals[int(b[1:])]['key']
            cut.append(record)
    sources=[(i,t) for i,t in enumerate(terminals) if not t['port']]
    sinks=[(i,t) for i,t in enumerate(terminals) if t['port']]
    removed_super=graph.copy();removed_super.remove_nodes_from(['source','sink'])
    individual=[]
    for i,t in sources:
        nodes=nx.descendants(removed_super,f't{i}')
        individual.append(dict(terminal=t['key'],reachable_QD=[s['key'] for j,s in sinks if f't{j}' in nodes],flow=flow['source'].get(f't{i}',0),anchor_count=len(t['options'])))
    unserved_sinks=[t['key'] for i,t in sinks if flow[f't{i}'].get('sink',0)==0]
    report=dict(passed=False,capacity_complete=capacity==16,scope='Offline multi-anchor upper-bound diagnostic. Unselected terminal stubs are not blocked; all chosen stubs/routes require independent spacing and tangent-curve audits.',placement_sha256=hashlib.sha256(placement_bytes).hexdigest(),reference_sha256=hashlib.sha256(reference_bytes).hexdigest(),capacity=capacity,step=args.step,offset=args.offset,terminals=terminals,mincut_capacity=cut_capacity,mincut=cut,individual=individual,unserved_sinks=unserved_sinks,graph_nodes=len(graph),graph_edges=graph.number_of_edges())
    if capacity==16:
        if constrained_result is not None and constrained_result['flow'] is not None:
            cost=nx.cost_of_flow(graph,flow)
        else:cost,flow=nx.network_simplex(graph)
        result=[]
        for i,t in enumerate(terminals):
            if t['port']:continue
            node=f't{i}';path=[];seen=set();end=None;start_anchor=None;end_anchor=None
            while node!='sink':
                assert node not in seen;seen.add(node)
                following=[b for b,n in flow[node].items() if n>0];assert len(following)==1
                prevnode=node;node=following[0]
                if prevnode==f't{i}' and isinstance(node,int):start_anchor=node//2
                if isinstance(node,int) and node%2==0:path.append(xy[node//2].tolist())
                if isinstance(node,str) and node.startswith('t'):
                    end_index=int(node[1:]);end=terminals[end_index]
                    if isinstance(prevnode,int):end_anchor=prevnode//2
            if start_anchor is None:pts=direct[(i,end_index)]
            else:
                so=next(o for o in t['options'] if o['anchor']==start_anchor)
                eo=next(o for o in end['options'] if o['anchor']==end_anchor)
                pts=rr.strip_collinear(so['stub']+path[1:]+list(reversed(eo['stub']))[1:])
            result.append(dict(group=t['group'],target=end['group'],points=pts))
        pair_conflicts=[]
        for i,a in enumerate(result):
            for b in result[i+1:]:
                gap=LineString(a['points']).distance(LineString(b['points']))-.11
                if gap<.15-1e-7:pair_conflicts.append(dict(a=a['group'],b=b['group'],gap=gap))
        report.update(cost=cost,routes=result,mapping={r['group']:r['target'] for r in result},pair_conflicts=pair_conflicts)
    report['reference_snapshot']=str(reference_snapshot)
    report['obstacle_counts']=dict(bottom_pad_polygons=len(bottom_pads),via_circles=len(p['vias']),SMP_ring_disks=len(p['smp']),resistor_hulls=len(groups),fixed_route_shapes=len(fixed),total=len(objects))
    if constrained_result is not None:report['stub_conflict_solver']={k:v for k,v in constrained_result.items() if k!='flow'}
    report['y_offset']=y_offset
    report['direct_terminal_options']=[dict(group=terminals[i]['group'],target=terminals[j]['group'],points=stub) for (i,j),stub in direct.items()]
    args.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('terminals','routes','individual','mincut')},indent=2),flush=True)

if __name__=='__main__':main()
