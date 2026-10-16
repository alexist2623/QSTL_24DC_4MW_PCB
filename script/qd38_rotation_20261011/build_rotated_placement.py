"""Create an offline rotated-QD / seven-row SMP placement, preserving all sources.

This file does not update native PCB, schematic, source geometry or project JSONs.
"""
from pathlib import Path
import copy, hashlib, json, math, random
import numpy as np
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
SOURCE=ROOT/'QSTL_QD4_2SET_38PAD/circuit_plan.json'
CENTER=np.array([9.75,42.5])
RF=[2,5,9,11,12,13,15,16,21,24,28,30,31,32,34,35]

def rot(v): return [-float(v[1]),float(v[0])]
def pg(d):
    if d['shape']=='round': return Point(d['x'],d['y']).buffer(d['sx']/2,quad_segs=48)
    t=math.radians(d['rotation']);u=np.array([math.cos(t),math.sin(t)]);v=np.array([-u[1],u[0]])
    return Polygon([np.array([d['x'],d['y']])+a*d['sx']/2*u+b*d['sy']/2*v for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]])
def pad(ref,pin,xy,size,net,angle=0,layer=32,hole=0,shape='rect'):
    return dict(ref=ref,pin=str(pin),x=float(xy[0]),y=float(xy[1]),sx=size[0],sy=size[1],net=net,rotation=angle,layer=layer,hole=hole,shape=shape)
def body(xy,size,angle): return pg(pad('',0,xy,size,None,angle))

def main():
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    p=json.loads(SOURCE.read_text())
    for key in ['arcs','routed_jobs','dc_routed_jobs','unrouted_jobs','routing_complete','shield_vias','ground_regions','mask_regions','dynamic_zif_assignment']:
        p.pop(key,None)
    p['tracks']=[t for t in p['tracks'] if t['layer']==1]
    p['route_jobs']=[]
    p['cavity_mm']=[4.3,5.3]
    p['qd_rotation_deg']=90
    p['status']='OFFLINE_PLACEMENT_CANDIDATE_NOT_ROUTED_OR_NATIVE_VALIDATED'
    for q in p['pads']:
        for field in ['center','chip','bond','normal','inner']:
            q[field]=rot(q[field])
        q['polygon']=[rot(v) for v in q['polygon']]
        q['rotation']=(q['rotation']+90)%360
        for field,source in [('absolute_center','center'),('absolute_chip','chip'),('absolute_bond','bond')]:
            q[field]=(np.array(q[source])+CENTER).tolist()
        q['side']={'LEFT':'BOTTOM','RIGHT':'TOP','TOP':'LEFT','BOTTOM':'RIGHT'}.get(q['side'],q['side'])
    fixed=[copy.deepcopy(a) for a in p['physical_pads'] if a['ref']=='J1' or a['ref'] is None]
    qd=[pad('Q1',q['number'],q['absolute_center'],[.8,.25],q['net_name'],q['rotation']) for q in p['pads']]
    positions=[(x,y) for y in [24.5,30.5,36.5,42.5,48.5,54.5,60.5] for x in ([3.75,9.75,15.75] if y in [24.5,60.5] else [3.75,15.75])]
    cost=[[math.dist(p['pads'][n-1]['absolute_center'],xy) for xy in positions] for n in RF]
    ri,ci=linear_sum_assignment(cost)
    smps=[];sp=[]
    for i,j in zip(ri,ci):
        n=RF[i];x,y=positions[j]
        smps.append(dict(ref=f'SMP{n:02}',q=n,x=x,y=y,body_diameter=5.5,pattern='RF_Con',layer=1,rotation=0))
        for pin,(dx,dy) in enumerate([(0,0),(-1.27,1.27),(-1.27,-1.27),(1.27,-1.27),(1.27,1.27)],1):
            sp.append(pad(f'SMP{n:02}',pin,(x+dx,y+dy),(1,1),f'S{n:02}' if pin==1 else 'GND',layer=74,hole=.75,shape='round'))
    p['smp']=smps
    fixed+=qd+sp
    board=Polygon(p['board_outline']);cavity=box(7.6,39.85,11.9,45.15)
    report=dict(source_sha256=source_hash,source=str(SOURCE),row_counts=[3,2,2,2,2,2,3],qd_rotation_deg_ccw=90,blockers=[],placement_checks={})
    # Retain full-stack signal-via manufacture geometry. A laser shield hole is
    # not substituted for a plated through signal hole. Keep the drill centre
    # on the long pad axis and require its entire drill to remain in the pad.
    qvias=[]
    for q in qd:
        if int(q['pin']) in RF: continue
        t=math.radians(q['rotation']);u=np.array([math.cos(t),math.sin(t)])
        others=[pg(d) for d in fixed if d['net']!=q['net'] and d['layer'] in (32,74)]
        candidates=[]
        for offset in np.linspace(-.2999,.2999,61):
            for lateral in [-.0249,0,.0249]:
                xy=np.array([q['x'],q['y']])+offset*u+lateral*np.array([-u[1],u[0]])
                g=Point(xy).buffer(.2,quad_segs=48)
                gap=min(g.distance(o) for o in others)
                candidates.append((gap,float(offset),xy))
        best=max(candidates,key=lambda a:a[0]);gap,offset,xy=best
        if gap<.15-1e-7: report['blockers'].append(dict(kind='direct_QD_via_foreign_pad_gap',pin=q['pin'],gap_mm=gap,required_mm=.15))
        qvias.append(dict(x=float(xy[0]),y=float(xy[1]),net=q['net'],diameter=.4,hole=.2,low=1,high=32,label='Q1-'+q['pin'],via_in_pad=True,pad_axis_offset_mm=offset,minimum_foreign_pad_gap_mm=gap))
    # Generate actual C0402 and R0603 lands. Candidate components have all-pad
    # clearance >= 0.155 mm and actual source-body clearance >= 0.254 mm.
    fixed_shapes=[pg(a) for a in fixed if a['layer'] in (32,74)]
    fixed_union=unary_union(fixed_shapes+[Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48) for v in qvias]+[cavity])
    drill_union=unary_union([Point(d['x'],d['y']).buffer(d['hole']/2,quad_segs=48) for d in fixed if d['hole']]+[cavity]+[pg(d) for d in qd])
    all_candidates={}
    axes=[np.array(a,float) for a in [(1,0),(0,1),(-1,0),(0,-1)]]
    for s in smps:
        n=s['q'];origin=np.array([s['x'],s['y']]);target=np.array(p['pads'][n-1]['absolute_center']);candidates=[]
        for cu in axes:
            ca=math.degrees(math.atan2(cu[1],cu[0]))%360
            for along in [2.1,2.35,2.6,2.85,3.1]:
                for across in [0,-.4,.4,-.8,.8]:
                    cc=origin+along*cu+across*np.array([-cu[1],cu[0]])
                    c1=cc-.47856267*cu;c2=cc+.47856267*cu
                    cp=[pad(f'C{n:02}',1,c1,[.71534782,.67247516],f'S{n:02}',ca),pad(f'C{n:02}',2,c2,[.71534782,.67247516],f'MW{n:02}',ca)]
                    cb=body(cc,[1,.5],ca);cg=unary_union([pg(d) for d in cp])
                    if not board.buffer(-.2).covers(cg) or cg.distance(fixed_union)<.155 or cb.distance(drill_union)<.254: continue
                    for ru in axes:
                        ra=math.degrees(math.atan2(ru[1],ru[0]))%360
                        for du in axes:
                            for sep in [1.0,1.3,1.6,1.9,2.2]:
                                r1=c2+sep*du;r2=r1+1.69999914*ru;rc=(r1+r2)/2
                                rp=[pad(f'R{n:02}',1,r1,[1.10000034,1.00000054],f'MW{n:02}',ra),pad(f'R{n:02}',2,r2,[1.10000034,1.00000054],f'DC{n:02}',ra)]
                                rb=body(rc,[1.6,.8],ra);rg=unary_union([pg(d) for d in rp])
                                if not board.buffer(-.2).covers(rg) or rg.distance(fixed_union)<.155 or rg.distance(cg)<.155 or rb.distance(cb)<.254 or rb.distance(drill_union)<.254: continue
                                cost=math.dist(origin,c1)+math.dist(c2,r1)+.35*math.dist(r1,target)+.1*math.dist(rc,CENTER)
                                candidates.append(dict(cost=cost,pads=cp+rp,bodies=[cb,rb],geom=unary_union([cg,rg]),centers=[cc,rc],angles=[ca,ra]))
        candidates.sort(key=lambda c:c['cost']);all_candidates[n]=candidates[:350]
        print('CANDIDATES',n,len(candidates),flush=True)
        if not candidates: report['blockers'].append(dict(kind='no_RC_group_placement',terminal=n))
    best=None
    for iteration in range(120):
        random.seed(iteration)
        order=sorted(smps,key=lambda s:len(all_candidates[s['q']])*(1+random.random()))
        placed={};score=0
        for s in order:
            for c in all_candidates[s['q']]:
                if all(c['geom'].distance(d['geom'])>=.155 and min(a.distance(b) for a in c['bodies'] for b in d['bodies'])>=.254 for d in placed.values()):
                    placed[s['q']]=c;score+=c['cost'];break
        rank=(len(placed),-score)
        if best is None or rank>best[0]: best=(rank,placed)
        if len(placed)==16: break
    placed=best[1]
    if len(placed)!=16: report['blockers'].append(dict(kind='RC_group_packing_incomplete',placed=len(placed),missing=[n for n in RF if n not in placed]))
    components=[copy.deepcopy(c) for c in p['components'] if c['ref'] in ('Q1','J1')]
    next(c for c in components if c['ref']=='Q1')['rotation']=90
    components+=smps;physical=fixed[:];ends={};vias=qvias[:]
    jobs=[];passive_bodies=[]
    for n,c in placed.items():
        cc,rc=c['centers'];ca,ra=c['angles'];physical+=c['pads']
        components += [dict(ref=f'C{n:02}',pattern='FP-GCM155-0_05-IPC_A',x=float(cc[0]),y=float(cc[1]),rotation=ca,layer=32,value='1nF'),dict(ref=f'R{n:02}',pattern='CC1608-0603',x=float(rc[0]),y=float(rc[1]),rotation=ra,layer=32,value='10k')]
        c1,c2,r1,r2=c['pads'];s=next(a for a in smps if a['q']==n)
        ends[str(n)]=dict(x=r2['x'],y=r2['y'],endpoint=f'R{n:02}-2',via_in_pad=True)
        vias.append(dict(x=r2['x'],y=r2['y'],net=f'DC{n:02}',diameter=.5,hole=.25,low=1,high=32,label=f'R{n:02}-2',via_in_pad=True))
        s['escape_angle_deg']=math.degrees(math.atan2(c1['y']-s['y'],c1['x']-s['x']))%360
        qp=p['pads'][n-1];outer=np.array(qp['absolute_center'])+.15*np.array(qp['normal'])
        for net,a,b,kind in [(f'S{n:02}',[s['x'],s['y']],[c1['x'],c1['y']],'RF'),(f'MW{n:02}',[c2['x'],c2['y']],[r1['x'],r1['y']],'RF_BIAS'),(f'MW{n:02}',outer.tolist(),[r1['x'],r1['y']],'RF_QD')]:
            jobs.append(dict(net=net,layer=32,a=a,b=b,width=.11,kind=kind))
        for ref,g in zip([f'C{n:02}',f'R{n:02}'],c['bodies']): passive_bodies.append(dict(ref=ref,outline=list(g.exterior.coords)[:-1]))
    for v in qvias:
        n=str(int(v['label'].split('-')[1]));ends[n]=dict(x=v['x'],y=v['y'],endpoint=v['label'],via_in_pad=True)
    # Preserve the currently selected J1 contacts and top fanout geometry. The
    # downstream router is allowed to reassign these 38 ports synchronously.
    jvias=[copy.deepcopy(v) for v in p['vias'] if v['label'].startswith('J1-')]
    for mapping in p['pinmap']:
        n=str(mapping['qd_pad']);e=ends.get(n)
        if e is None: continue
        layer=mapping['dc_layer'];e.update(layer=layer,zif_pin=mapping['zif_pin'])
        v=next(v for v in vias if v['label']==e['endpoint']);v.update(routing_layer=layer,assigned_dc_layer=layer)
        jv=next(v for v in jvias if v['label']==f"J1-{mapping['zif_pin']}")
        jobs.append(dict(net=mapping['dc_net'],layer=layer,a=[jv['x'],jv['y']],b=[e['x'],e['y']],width=.125,kind='DC'))
    vias+=jvias
    via_pairs=[]
    for i,a in enumerate(vias):
        for b in vias[i+1:]:
            if a['net']==b['net']: continue
            gap=math.dist([a['x'],a['y']],[b['x'],b['y']])-(a['diameter']+b['diameter'])/2
            if gap<.15-1e-7: via_pairs.append(dict(a=a['label'],b=b['label'],gap_mm=gap))
    if via_pairs: report['blockers'].append(dict(kind='foreign_via_to_via_clearance',pairs=via_pairs))
    p.update(components=components,physical_pads=physical,vias=vias,route_jobs=jobs,dc_endpoints=ends,passive_bodies=passive_bodies)
    p['nets']={}
    for d in physical:
        if d['ref'] and d['net']: p['nets'].setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
    report['placement_checks'].update(component_count=len(components),physical_pad_count=len(physical),route_job_count=len(jobs),direct_QD_vias=len(qvias),SMP_ref_assignment=smps,minimum_direct_via_foreign_pad_clearance_mm=min(v['minimum_foreign_pad_gap_mm'] for v in qvias),source_unchanged=source_hash==hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    report['limitations']=['No routed copper, native DRC, shield placement or fabrication approval is claimed.', 'Direct QD vias use the existing J1-size 0.4 mm land / 0.2 mm full-stack drill; their centres and complete drill circles fit the 0.25 mm wide pad, but the annular lands protrude outside the narrow bonding pad.']
    (H/'placement_candidate.json').write_text(json.dumps(p,indent=2))
    (H/'placement_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
