"""Route all 38 DC nets on the fixed 16-RF proposal; no native CAD edits."""
from pathlib import Path
import csv, json, math, sys, time
from itertools import combinations
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from scipy.ndimage import label as label_regions
from ortools.graph.python import min_cost_flow
import finalize_shielded_rf_20261016 as rf
base=rf.m.base
ROOT=base.ROOT
OUT=ROOT/'QSTL_QD4_2SET_38PAD/DC_Shielded_Plan_20261016'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
args=sys.argv[:];sys.argv=[sys.argv[0]]
import route_dc_rotated as old
sys.argv=args
W=.125; GAP=.10; GUARD=.003
STEP=.26
LAYER_ROLES={'1':'GND','2':'DC_A','3':'DC_B','4':'GND','5':'GND','6':'RF_QD'}

def save(name,obj):
    (OUT/name).write_text(json.dumps(obj,indent=2),encoding='utf-8')

def load():
    data,groups,st=rf.load_routes()
    snapshot=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
    mapping=list(csv.DictReader((ROOT/'QSTL_QD4_2SET_38PAD/pin_mapping.csv').open()))
    shield=json.loads((rf.OUT/'shielded_rf_plan.json').read_text())
    return data,groups,st,snapshot,mapping,shield

def prepare(data,groups,st,snapshot,mapping,shield):
    vias=[];top=[]
    for row in mapping:
        n=int(row['qd_pad']);net=row['dc_net'];pin=row['zif_pin']
        if row['rf']=='True':
            g=next(g for g in groups if g['row']['qd_pad']==n)
            xy=g['resistor']['pads'][1]['centre_mm'];d,h=.50,.25
            label=g['resistor']['ref']+'-2';kind='resistor DC terminal'
        else:
            before=next(p for p in snapshot['pads'] if p['component']=='Q1' and int(p['number'])==n)
            after=next(p['after'] for p in data['pads'] if int(p['number'])==n)
            ov=next(v for v in snapshot['vias'] if v['net']==net and abs(v['diameter']-.35)<.001)
            xy=[after['x']+ov['x']-before['x'],after['y']+ov['y']-before['y']]
            d,h=.35,.20;label='Q1-'+str(n);kind='direct QD terminal'
        vias.append(dict(label=label,net=net,x=float(xy[0]),y=float(xy[1]),diameter=d,hole=h,kind=kind,qd_pad=n,port=False))
        ov=next(v for v in snapshot['vias'] if v['net']==net and abs(v['diameter']-.4)<.001 and v['y']<10)
        v=dict(label='J1-'+pin,net='PORT'+pin,x=ov['x'],y=ov['y']+data['ZIF']['delta_y_mm'],diameter=.4,hole=.2,kind='ZIF terminal',port=True,pin=int(pin))
        vias.append(v)
        tracks=[t for t in snapshot['tracks'] if t['net']==net and t['layer']==1]
        for t in tracks:
            top.append(dict(port=v['label'],width=t['width'],points=[[t['x1'],t['y1']+data['ZIF']['delta_y_mm']],[t['x2'],t['y2']+data['ZIF']['delta_y_mm']]]))
    assert len(vias)==76 and len(top)==38
    return dict(vias=vias,top_fanout=top,mapping=mapping,planned_layer_roles=LAYER_ROLES,source_geometry_SHA256=base.digest(base.SOURCE),
                rf_geometry_SHA256=base.digest(rf.OUT/'shielded_rf_plan.json'),scope='Offline routed proposal; native PCB/schematic unchanged')

def terminal_audit(plan,data,groups,st,shield):
    failures=[];metrics={}
    pads=[('Q1-'+str(n),g) for n,g in st['qd']]
    pads += [(c['ref']+'-'+str(p['pin']),Polygon(p['polygon_mm'])) for g in groups for c in (g['resistor'],g['capacitor']) for p in c['pads']]
    pads += [(name+'-'+pin,g) for name,pin,g in st['smp_pads']]
    rf_copper=unary_union([g['lines'].buffer(.055,quad_segs=32) for g in groups])
    shield_copper=unary_union([Point(v['x_mm'],v['y_mm']).buffer(.125,quad_segs=32) for v in shield['vias']])
    def check(name,d,required,what):
        metrics[what]=min(metrics.get(what,1e6),float(d))
        if d<required-2e-6:failures.append(dict(terminal=name,other=what,gap_mm=float(d),required_mm=required))
    for v in plan['vias']:
        p=Point(v['x'],v['y']);g=p.buffer(v['diameter']/2,quad_segs=64)
        if not v['port']:
            own=next(g for n,g in pads if n==v['label'])
            if not own.covers(p.buffer(v['hole']/2,quad_segs=64)):
                failures.append(dict(terminal=v['label'],other='hole outside terminal pad'))
            check(v['label'],g.distance(rf_copper),.15,'via to RF copper')
            check(v['label'],g.distance(shield_copper),.2,'via to shield land')
            check(v['label'],min(g.distance(o) for n,o in pads if n!=v['label']),.15,'via to foreign Bottom pad')
            check(v['label'],g.distance(st['cavity']),.15,'via to cavity')
    for a,b in combinations(plan['vias'],2):
        d=math.hypot(a['x']-b['x'],a['y']-b['y'])
        check(a['label']+'/'+b['label'],d-(a['diameter']+b['diameter'])/2,.10,'terminal land gap')
        check(a['label']+'/'+b['label'],d-(a['hole']+b['hole'])/2,.20,'terminal drill gap')
    return dict(passed=not failures,failures=failures,minimums_mm=metrics)

def adjust_qd_terminals(plan,data,groups,st,shield):
    """Move terminal vias only within their existing bond lands, not the pads."""
    changes=[]
    shields=unary_union([Point(v['x_mm'],v['y_mm']).buffer(.125,quad_segs=48) for v in shield['vias']])
    pads=rf.all_pad_geometry(groups,st)
    rfc=unary_union([g['lines'].buffer(.055,quad_segs=32) for g in groups])
    for v in plan['vias']:
        if v['kind']!='direct QD terminal':continue
        own=next(g for n,g in st['qd'] if n==v['qd_pad'])
        if Point(v['x'],v['y']).distance(shields)-v['diameter']/2>=.203:continue
        pad=next(p['after'] for p in data['pads'] if int(p['number'])==v['qd_pad'])
        theta=math.radians(pad['rotation']);u=np.array([math.cos(theta),math.sin(theta)])
        original=np.array([v['x'],v['y']]);foreign=pads.difference(own)
        found=None
        for shift in sorted(np.arange(-.25,.251,.0025),key=abs):
            xy=original+shift*u;p=Point(xy);land=p.buffer(.175,quad_segs=48)
            if not own.covers(p.buffer(.1,quad_segs=48)):continue
            if land.distance(shields)<.203 or land.distance(foreign)<.153 or land.distance(rfc)<.153:continue
            if any(math.dist(xy,[w['x'],w['y']])<(v['diameter']+w['diameter'])/2+.103 for w in plan['vias'] if w is not v):continue
            found=xy;break
        if found is None:raise RuntimeError('No safe terminal position '+v['label'])
        v['x'],v['y']=map(float,found)
        changes.append(dict(terminal=v['label'],old_mm=original.tolist(),new_mm=found.tolist(),shift_mm=float(np.linalg.norm(found-original))))
    plan['QD_terminal_shifts_within_unchanged_pads']=changes

def obstacles(plan,data,groups,st):
    # Normalize each obstacle to the common 0.10 mm copper-to-copper rule.
    objects=[]
    for v in plan['vias']:
        radius=max(v['diameter']/2, v['hole']/2+.20-GAP)
        objects.append((v['label'],Point(v['x'],v['y']).buffer(radius,quad_segs=32)))
    for name in {n for n,_,_ in st['smp_pads']}:
        g=unary_union([g for n,p,g in st['smp_pads'] if n==name]).convex_hull
        # Covers component PTH hole-to-inner-copper 0.30 mm as well as the
        # user prohibition on passing between connector signal/ground pads.
        objects.append((name,g.buffer(.10,quad_segs=32)))
    objects.extend((n,g.buffer(.10,quad_segs=32)) for n,g in st['mounts'])
    objects.append(('cavity',st['cavity'].buffer(.05)))
    bodies={g['resistor']['ref']:base.as_component_geometry(g['resistor']).convex_hull for g in groups}
    return objects,bodies

def own_obstacles(objects,bodies,groups,labels):
    obs=[g for name,g in objects if name not in labels]
    for name,hull in bodies.items():
        if name+'-2' in labels:
            g=next(g for g in groups if g['resistor']['ref']==name)
            hull=hull.difference(Polygon(g['resistor']['pads'][1]['polygon_mm']))
        obs.append(hull.buffer(.05))
    return unary_union(obs)

def solve_bank(plan,data,groups,st,layer,sources,ports):
    start=time.monotonic();objects,bodies=obstacles(plan,data,groups,st)
    block=unary_union([g for n,g in objects]+[g.buffer(.05) for g in bodies.values()]).buffer(W/2+GAP+GUARD,quad_segs=24)
    xmin,ymin,xmax,ymax=data['board_bounds_xy_mm']
    xs=np.arange(xmin+.33,xmax-.3,STEP);ys=np.arange(ymin+.33,75,STEP)
    xx,yy=np.meshgrid(xs,ys);xy=np.c_[xx.ravel(),yy.ravel()];nxg=len(xs);nyg=len(ys)
    points=shapely.points(xy)
    available=~shapely.intersects(points,block)
    regions,_=label_regions(available.reshape(nyg,nxg));sizes=np.bincount(regions.ravel());sizes[0]=0
    available &= regions.ravel()==int(np.argmax(sizes))
    # Reserve short, continuously checked terminal escapes before integral flow.
    terminals=[];stubs=[]
    for v in sorted(sources+ports,key=lambda v:(v['port'],v['y'],v['x'])):
        a=[v['x'],v['y']];dist=np.linalg.norm(xy-a,axis=1)
        obs=own_obstacles(objects,bodies,groups,{v['label']})
        candidates=np.where(available & (dist<2.0))[0]
        candidates=candidates[np.argsort(dist[candidates])]
        found=None
        for k in candidates:
            if v['port'] and xy[k,1]<a[1]+.25:continue
            for stub in old.stub_options(a,xy[k].tolist()):
                g=LineString(stub).buffer(W/2,quad_segs=24)
                if g.distance(obs)<GAP+GUARD:continue
                if any(g.distance(o)<GAP+GUARD for o in stubs):continue
                found=(int(k),stub,g);break
            if found:break
        if not found:raise RuntimeError(f'No terminal escape L{layer}: {v["label"]}')
        k,stub,g=found;terminals.append(dict(via=v,anchor=k,stub=stub));stubs.append(g);available[k]=False
    stubblock=unary_union(stubs).buffer(GAP+GUARD+W/2-.000001,quad_segs=24)
    available &= ~shapely.intersects(points,stubblock)
    for t in terminals:available[t['anchor']]=True
    # Positive-cost, node-capacitated paths: distinct nets cannot cross in a layer.
    ngrid=len(xy);S=ngrid*2;T=S+1
    solver=min_cost_flow.SimpleMinCostFlow()
    nodes=np.where(available)[0].astype(np.int64)
    solver.add_arcs_with_capacity_and_unit_cost(nodes*2,nodes*2+1,np.ones(len(nodes),dtype=np.int64),np.zeros(len(nodes),dtype=np.int64))
    aa=[];bb=[]
    for k in nodes:
        for j in (k+1 if k%nxg<nxg-1 else -1,k+nxg if k//nxg<nyg-1 else -1):
            if j>=0 and available[j]:aa.append(int(k));bb.append(int(j))
    aa=np.array(aa);bb=np.array(bb)
    segments=shapely.linestrings(np.stack([xy[aa],xy[bb]],axis=1))
    valid=~shapely.intersects(segments,block)
    # Entry/exit anchors are reserved to their terminals, not transit corridors.
    source_nodes={t['anchor'] for t in terminals if not t['via']['port']};port_nodes={t['anchor'] for t in terminals if t['via']['port']}
    for reverse in (False,True):
        a,b=(bb,aa) if reverse else (aa,bb)
        ok=valid & ~np.isin(a,list(port_nodes)) & ~np.isin(b,list(source_nodes))
        a=a[ok];b=b[ok]
        cost=(10000+np.where(a%nxg==b%nxg,abs(xy[a,0]-9.75)*650,0)).astype(np.int64)
        solver.add_arcs_with_capacity_and_unit_cost(a*2+1,b*2,np.ones(len(a),dtype=np.int64),cost)
    for t in terminals:
        k=t['anchor']
        if t['via']['port']:solver.add_arc_with_capacity_and_unit_cost(k*2+1,T,1,0)
        else:solver.add_arc_with_capacity_and_unit_cost(S,k*2,1,0)
    solver.set_node_supply(S,len(sources));solver.set_node_supply(T,-len(sources))
    print('SOLVING',layer,'sources',len(sources),'nodes',len(nodes),'arcs',solver.num_arcs(),flush=True)
    status=solver.solve();print('FLOW_STATUS',layer,status,'seconds',round(time.monotonic()-start,2),flush=True)
    if status!=solver.OPTIMAL:raise RuntimeError(f'Unroutable bank L{layer}: {status}')
    following={}
    for i in range(solver.num_arcs()):
        if solver.flow(i)>0:following[solver.tail(i)]=solver.head(i)
    byanchor={t['anchor']:t for t in terminals if t['via']['port']}
    routes=[]
    for t in terminals:
        if t['via']['port']:continue
        k=t['anchor']*2;path=[]
        while k!=T:
            if k%2==0:path.append(xy[k//2].tolist())
            last=k;k=following[k]
        end=byanchor[last//2]
        p=old.compact(t['stub']+path[1:]+list(reversed(end['stub']))[1:])
        routes.append(dict(net=t['via']['net'],source=t['via']['label'],port=end['via']['label'],qd_pad=t['via']['qd_pad'],layer=layer,width_mm=W,points=p))
    return routes

def main():
    data,groups,st,snapshot,mapping,shield=load();plan=prepare(data,groups,st,snapshot,mapping,shield)
    adjust_qd_terminals(plan,data,groups,st,shield)
    check=terminal_audit(plan,data,groups,st,shield);save('terminal_geometry_audit.json',check);save('dc_input.json',plan)
    print('TERMINALS',check,flush=True)
    if not check['passed']:return
    if '--prepare-only' in sys.argv:return
    sources=sorted([v for v in plan['vias'] if not v['port']],key=lambda v:(v['x'],v['y']))
    ports=sorted([v for v in plan['vias'] if v['port']],key=lambda v:(v['x'],v['y']))
    routes=[]
    for layer,start,end in ((2,0,19),(3,19,38)):
        r=solve_bank(plan,data,groups,st,layer,sources[start:end],ports[start:end]);save(f'raw_L{layer}.json',r);routes.extend(r)
    save('raw_dc_routes.json',routes)

if __name__=='__main__':main()
