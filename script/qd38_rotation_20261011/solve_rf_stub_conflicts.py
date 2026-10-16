"""Select terminal escapes with geometric conflicts in a planar network flow.

This is an offline routing diagnostic. It neither edits placement nor native CAD.
Only escape choices are binary; conditioned on them, the network is integral.
Every returned polyline still requires independent clearance and curve audits.
"""
import math
import time
import numpy as np
import shapely
from shapely.geometry import Point, LineString
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix

def solve(graph,xy,terminals,direct,time_limit=120):
    started=time.monotonic()
    edges=list(graph.edges());columns={edge:i for i,edge in enumerate(edges)}
    nodes=list(graph);rows={node:i for i,node in enumerate(nodes)}
    nr=len(nodes);n=len(edges);ri=[];ci=[];values=[]
    lower=[];upper=[];integer=np.zeros(n,np.uint8)
    for node in nodes:
        d=16 if node=='sink' else -16 if node=='source' else 0
        lower.append(d);upper.append(d)
    for i,(a,b) in enumerate(edges):
        ri.extend([rows[a],rows[b]]);ci.extend([i,i]);values.extend([-1,1])
    node_columns={a//2:i for i,(a,b) in enumerate(edges) if isinstance(a,int) and a%2==0 and b==a+1}
    grid_columns={}
    for i,(a,b) in enumerate(edges):
        if isinstance(a,int) and isinstance(b,int) and a%2==1 and b%2==0:
            key=tuple(sorted((a//2,b//2)));grid_columns.setdefault(key,[]).append(i)
    grid_keys=list(grid_columns)
    grid_geoms=[LineString([xy[a],xy[b]]) for a,b in grid_keys]
    grid_tree=shapely.STRtree(grid_geoms)
    point_keys=list(node_columns)
    point_geoms=shapely.points(np.asarray([xy[k] for k in point_keys]))
    point_tree=shapely.STRtree(point_geoms)
    stubs=[]
    for ti,t in enumerate(terminals):
        for o in t['options']:
            k=o['anchor'];edge=(k*2+1,f't{ti}') if t['port'] else (f't{ti}',k*2)
            col=columns[edge];integer[col]=1
            stubs.append(dict(col=col,terminal=ti,anchor=k,geom=LineString(o['stub'])))
    for (a,b),points in direct.items():
        col=columns[(f't{a}',f't{b}')];integer[col]=1
        stubs.append(dict(col=col,terminal=(a,b),anchor=None,geom=LineString(points)))
    stub_geoms=[s['geom'] for s in stubs];stub_tree=shapely.STRtree(stub_geoms)
    conflicts=set();sep=.2635
    for si,s in enumerate(stubs):
        shape=s['geom'];col=s['col'];anchor=s['anchor'];buffered=shape.buffer(sep)
        for pj in point_tree.query(buffered):
            key=point_keys[pj]
            if key==anchor or shape.distance(point_geoms[pj])>=sep-1e-9:continue
            conflicts.add(tuple(sorted((col,node_columns[key]))))
        for gj in grid_tree.query(buffered):
            key=grid_keys[gj]
            if anchor in key or shape.distance(grid_geoms[gj])>=sep-1e-9:continue
            for other in grid_columns[key]:conflicts.add(tuple(sorted((col,other))))
        for sj in stub_tree.query(buffered):
            if sj<=si:continue
            t=stubs[sj]
            if s['terminal']==t['terminal']:continue
            if shape.distance(t['geom'])>=sep-1e-9:continue
            conflicts.add(tuple(sorted((col,t['col']))))
    for a,b in sorted(conflicts):
        ri.extend([nr,nr]);ci.extend([a,b]);values.extend([1,1]);lower.append(-np.inf);upper.append(1);nr+=1
    matrix=coo_matrix((np.asarray(values,float),(np.asarray(ri,np.int32),np.asarray(ci,np.int32))),shape=(nr,n)).tocsc()
    c=np.array([graph[a][b].get('weight',0)/1000 for a,b in edges],float)
    print('STUB_MIP',dict(edges=n,binary=int(integer.sum()),conflicts=len(conflicts),seconds=round(time.monotonic()-started,2)),flush=True)
    result=milp(c,integrality=integer,bounds=Bounds(np.zeros(n),np.ones(n)),constraints=LinearConstraint(matrix,np.asarray(lower),np.asarray(upper)),options=dict(time_limit=time_limit,mip_rel_gap=.01,disp=False))
    report=dict(status=int(result.status),message=str(result.message),binary_choices=int(integer.sum()),conflicts=len(conflicts),variables=n,seconds=time.monotonic()-started,flow=None)
    if result.x is None:return report
    fraction=float(np.max(np.abs(result.x-np.round(result.x))));report['max_fractional_flow']=fraction
    if fraction>1e-6:return report
    x=np.round(result.x);residual=matrix@x
    if np.any(residual<np.asarray(lower)-1e-7) or np.any(residual>np.asarray(upper)+1e-7):raise ValueError('Solver flow violates retained constraints')
    flow={node:{} for node in nodes}
    for (a,b),value in zip(edges,x):flow[a][b]=int(value)
    report.update(flow=flow,cost=float(c@x))
    return report
