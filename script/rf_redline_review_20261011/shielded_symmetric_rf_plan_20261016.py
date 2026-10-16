"""Route the symmetric proposal with normal pad launches and real L5-L6 fences."""
import json
import math
import csv
import sys
import pickle
from itertools import product, combinations
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, substring, nearest_points
from scipy.spatial import cKDTree
import symmetric_rc_plan_20261016 as sym
import all_rc_placement_20261016 as base

ROOT=base.ROOT
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Shielded_Symmetric_RF_Plan_20261016'
OUT.mkdir(exist_ok=True)
WIDTH=.11
LAND=.25
HOLE=.10
OFFSET=.438
PITCH=.410
RF_EDGE_MIN=6*WIDTH+2*LAND
RF_CENTRE_TARGET=1.29
QD_END_RECT=box(6.52,42.42,12.98,49.88)
QD_LAUNCH_ZONE=QD_END_RECT.buffer(3.0,quad_segs=64)


def csc_paths(a,b,ua,ub):
    """Two tangent circular arcs joined by a forward straight segment."""
    left=lambda u:np.array([-u[1],u[0]])
    for radius,s1,s2 in product((.55,.65,.75,.85,1.,1.2,1.5,2.,2.5,3.,4.,5.,6.),(-1,1),(-1,1)):
        c1=a+s1*radius*left(ua);c2=b+s2*radius*left(ub);dvec=c2-c1;d=np.linalg.norm(dvec)
        if d<1e-6 or abs((s2-s1)*radius)>d:continue
        phi=math.atan2(dvec[1],dvec[0])-math.asin((s2-s1)*radius/d)
        v=np.array([math.cos(phi),math.sin(phi)])
        p1=c1-s1*radius*left(v);p2=c2-s2*radius*left(v)
        if np.dot(p2-p1,v)<-1e-6:continue
        aa=math.atan2(*(a-c1)[::-1]);ab=math.atan2(*(p1-c1)[::-1])
        ba=math.atan2(*(p2-c2)[::-1]);bb=math.atan2(*(b-c2)[::-1])
        da=(s1*(ab-aa))%(2*math.pi);db=(s2*(bb-ba))%(2*math.pi)
        if max(da,db)>math.pi+.001:continue
        ta=aa+s1*np.linspace(0,da,max(2,math.ceil(da*radius/.012)+1))
        tb=ba+s2*np.linspace(0,db,max(2,math.ceil(db*radius/.012)+1))
        pa=c1+radius*np.column_stack([np.cos(ta),np.sin(ta)])
        pb=c2+radius*np.column_stack([np.cos(tb),np.sin(tb)])
        xy=np.vstack([pa,pb]);xy[0]=a;xy[-1]=b
        yield xy,radius


def terminal_routes(data,g,groups,st):
    r=g['row'];u=g['u'];j=g['j'];e=np.array(r['end']);eu=np.array(r['outward']);s=np.array(r['start'])
    old=next(r for r in data['routes'] if r['smp']==g['row']['smp']);v=np.array(old['entry_outward']);q=s+2.8*v
    c1=np.array(g['capacitor']['pads'][0]['centre_mm']);c2=np.array(g['capacitor']['pads'][1]['centre_mm'])
    foreign=unary_union([other['envelope'] for other in groups if other is not g]);obs=st['byroute'][r['smp']]
    own_body=unary_union([base.shape_rect(np.array(g['capacitor']['centre_mm']),u,1.9,1.8),
                         base.shape_rect(np.array(g['resistor']['centre_mm']),np.array([-u[1],u[0]]),.6,.8)])
    dc=Polygon(g['resistor']['pads'][1]['polygon_mm'])
    sets=[];controls=(.25,.4,.7,1.,1.5,2.,2.5,3.,4.,5.,6.,8.,10.,12.,15.)
    for mode in ('qd','smp'):
        pool=[]
        raw=[]
        for escape in ((2.8,) if mode=='qd' else (1.2,1.6,2.,2.4,2.8)):
            a=e+.20*eu if mode=='qd' else c1+.75*u
            b=j-.75*u if mode=='qd' else s+escape*v
            ua=eu if mode=='qd' else u;ub=u if mode=='qd' else -v
            raw.extend(sym.bezier(a,b,ua,ub,ca,cb) for ca,cb in product(controls,repeat=2))
            raw.extend(csc_paths(a,b,ua,ub))
            if mode=='qd':
                tangent=np.array([0.,np.sign(b[1]-a[1])])
                for fraction,dx,k1,k2 in product((.10,.15,.20,.3,.4,.55,.7,.8),(-3.,-2.5,-2.,-1.5,-1.,-.5,0.,.5,1.,1.5,2.,2.5,3.),(.5,1.,1.5),(.5,1.,1.5)):
                    mid=a*(1-fraction)+b*fraction+np.array([dx,0.])
                    d1=np.linalg.norm(mid-a);d2=np.linalg.norm(b-mid)
                    xy1,r1=sym.bezier(a,mid,ua,tangent,d1*k1/3,d1/3)
                    xy2,r2=sym.bezier(mid,b,tangent,ub,d2/3,d2*k2/3)
                    raw.append((np.vstack([xy1,xy2[1:]]),min(r1,r2)))
        for xy,rad in raw:
            xy=np.vstack([e,xy,j,c2]) if mode=='qd' else np.vstack([c1,xy,s])
            if rad<.55:continue
            line=LineString(xy)
            if not line.is_simple:continue
            if line.distance(obs)<.205:continue
            if line.distance(foreign)<.405:continue
            if line.distance(dc)<.3:continue
            if not line.buffer(.055).disjoint(own_body):continue
            otherpad=g['capacitor']['pads'][0 if mode=='qd' else 1]
            if line.distance(Polygon(otherpad['polygon_mm']))<.2:continue
            pool.append(dict(points=xy,line=line,radius=rad,score=line.length,mode=mode,channel=r['smp'],
                             tail=line.difference(QD_LAUNCH_ZONE) if mode=='qd' else line))
        pool.sort(key=lambda a:a['score'])
        # Retain distinct corridor shapes, not only the shortest curves.
        selected=[];keys=set()
        for item in pool:
            key=tuple(round(v/.18) for t in (.15,.3,.5,.7,.85) for v in item['line'].interpolate(t,normalized=True).coords[0])
            if key in keys:continue
            keys.add(key);selected.append(item)
        sets.append(selected[:600] if mode=='qd' else selected[:100])
    print(r['smp'],'normal-launch candidates',*[len(p) for p in sets],flush=True)
    return sets


def compatible(a,b):
    if a['channel']==b['channel']:return a['line'].distance(b['line'])>=.26
    return a['tail'].distance(b['line'])>=RF_CENTRE_TARGET and b['tail'].distance(a['line'])>=RF_CENTRE_TARGET


def solve(pools):
    matrices={};neighbours={i:set() for i in range(len(pools))}
    for i,j in combinations(range(len(pools)),2):
        a=pools[i];b=pools[j]
        ba=unary_union([x['line'].envelope for x in a]).envelope
        bb=unary_union([x['line'].envelope for x in b]).envelope
        if ba.distance(bb)>RF_CENTRE_TARGET:continue
        la=np.array([x['line'].simplify(.002) for x in a],dtype=object)[:,None];lb=np.array([x['line'].simplify(.002) for x in b],dtype=object)[None,:]
        if a[0]['channel']==b[0]['channel']:mat=shapely.distance(la,lb)>=.26
        else:
            ta=np.array([x['tail'].simplify(.002) for x in a],dtype=object)[:,None];tb=np.array([x['tail'].simplify(.002) for x in b],dtype=object)[None,:]
            mat=(shapely.distance(ta,lb)>=RF_CENTRE_TARGET+.004)&(shapely.distance(la,tb)>=RF_CENTRE_TARGET+.004)
        if mat.all():continue
        matrices[i,j]=mat;matrices[j,i]=mat.T;neighbours[i].add(j);neighbours[j].add(i)
    print('Constraint matrices',len(matrices)//2,flush=True)
    def propagate(dom):
        queue=list(matrices)
        while queue:
            i,j=queue.pop();old=dom[i];d=old[np.any(matrices[i,j][np.ix_(old,dom[j])],axis=1)]
            if len(d)==0:
                if visits==0:print('Propagation conflict',pools[i][0]['channel'],pools[i][0]['mode'],pools[j][0]['channel'],pools[j][0]['mode'],'domains',len(old),len(dom[j]),flush=True)
                return None
            if len(d)!=len(old):
                dom[i]=d;queue.extend((k,i) for k in neighbours[i] if k!=j)
        return dom
    visits=0
    def recurse(dom):
        nonlocal visits
        dom=propagate(dom)
        if dom is None:return None
        left=[i for i in dom if len(dom[i])>1]
        if not left:return dom
        i=min(left,key=lambda k:len(dom[k]));visits+=1
        for c in dom[i]:
            nxt=dom.copy();nxt[i]=np.array([c]);res=recurse(nxt)
            if res is not None:return res
        return None
    result=recurse({i:np.arange(len(p)) for i,p in enumerate(pools)})
    if result is None:raise RuntimeError('Arc-consistent routing search found no complete assignment')
    print('Solved nodes',visits,flush=True)
    return [pools[i][int(result[i][0])] for i in range(len(pools))]

def old_solve(pools):
    chosen={};visits=0;cache={}
    def ok(i,ci,j,cj):
        key=(i,ci,j,cj) if i<j else (j,cj,i,ci)
        if key not in cache:cache[key]=compatible(pools[i][ci],pools[j][cj])
        return cache[key]
    for i,j in combinations(range(len(pools)),2):
        if not any(ok(i,a,j,b) for a in range(len(pools[i])) for b in range(len(pools[j]))):
            print('No pair compatibility',pools[i][0]['channel'],pools[i][0]['mode'],pools[j][0]['channel'],pools[j][0]['mode'],flush=True)
            raise RuntimeError('A route pair needs a larger fanout excursion')
    def assign():
        nonlocal visits
        if len(chosen)==len(pools):return True
        best=None;opts=None
        for i,p in enumerate(pools):
            if i in chosen:continue
            valid=[k for k in range(len(p)) if all(ok(i,k,j,c) for j,c in chosen.items())]
            if not valid:return False
            if opts is None or len(valid)<len(opts):best=i;opts=valid
        for k in opts:
            visits+=1
            if visits%1000==0:print('search',visits,'depth',len(chosen),flush=True)
            if visits>40000:raise RuntimeError('Route-search bound reached')
            chosen[best]=k
            if assign():return True
            del chosen[best]
        return False
    if not assign():raise RuntimeError('No route set at the specified full-width fence spacing')
    print('Selected after',visits,'visits',flush=True)
    return [pools[i][chosen[i]] for i in range(len(pools))]


def render_preview(data,sel,st):
    fig,ax=base.plt.subplots(figsize=(10.5,15.8),dpi=200)
    base.paint(ax,data,sel,st,(18.5,73.5));sym.add_guides(ax,sel)
    ax.set_title('Normal pad launches and widened RF corridors\nShield placement in progress',fontsize=14,pad=18)
    fig.tight_layout();fig.savefig(OUT/'Routing_Working_Preview.png');base.plt.close(fig)


def main():
    data=json.loads(base.SOURCE.read_text());groups=sym.build_groups(data);st=base.build_static(data)
    assert not sym.placement_check(data,groups,st)
    cache=OUT/'candidate_segments.pkl'
    if '--cached' in sys.argv:
        pools=pickle.loads(cache.read_bytes())
        for p in pools:
            for a in p:
                if a['mode']=='qd':a['tail']=a['line'].difference(QD_LAUNCH_ZONE)
    else:
        pools=[s for g in groups for s in terminal_routes(data,g,groups,st)]
        cache.write_bytes(pickle.dumps(pools))
    assert all(pools),'No individual normal-launch route'
    segments=solve(pools);sel=[]
    for i,g in enumerate(groups):
        a,b=segments[2*i:2*i+2]
        sel.append(dict(**g,qd_to_c2=a['points'],smp_to_c1=b['points'],lines=unary_union([a['line'],b['line']]),
                           tail=unary_union([a['tail'],b['tail']]),qline=a['line'],sline=b['line'],
                           local_radius=min(a['radius'],b['radius']),score=a['score']+b['score']))
    render_preview(data,sel,st)
    serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items()
             if k not in ('envelope','capg','resg','lines','tail','qline','sline')} for g in sel]
    (OUT/'routing_working.json').write_text(json.dumps(dict(groups=serial,QD_fanout_envelope_extension_mm=3.0,
        exception_basis='Distance from aligned QD pad-end rectangle; actual relaxed prefixes are measured in the final audit.'),indent=2)+'\n')
    print('Route pair minimum outside launch exception:',min(min(a['tail'].distance(b['lines']),b['tail'].distance(a['lines']))-WIDTH for a,b in combinations(sel,2)),flush=True)


if __name__=='__main__':main()
