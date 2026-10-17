"""Use exact tangent circles for broad SMP approaches, retaining uncertain entries."""
from pathlib import Path
import sys,json,copy,math
from itertools import product
import numpy as np
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/native_16rf_apply_20261016'),str(ROOT/'script/rf_redline_review_20261011')]
import build_candidate as bc
import finalize_shielded_rf_20261016 as f
data,live,st=f.load_routes();original=json.loads((H/'baseline/entry_routes.json').read_text());out=copy.deepcopy(original)
by={g['row']['smp']:g for g in live};pg=json.loads((H/'baseline/candidate.json').read_text())
left=lambda u:np.array([-u[1],u[0]])
cross=lambda a,b:float(a[0]*b[1]-a[1]*b[0])
unit=lambda u:u/np.linalg.norm(u)
for g in original['groups']:
    h=by[g['row']['smp']]
    for key in ('qd_to_c2','smp_to_c1'):h[key]=np.array(g[key])
    h['qline']=LineString(h['qd_to_c2']);h['sline']=LineString(h['smp_to_c1']);h['lines']=unary_union([h['qline'],h['sline']])
def line(a,b):return dict(line=True,a=np.asarray(a).tolist(),b=np.asarray(b).tolist())
def arc(c,a,b,s,r):
    aa=math.degrees(math.atan2(*(a-c)[::-1]));ab=math.degrees(math.atan2(*(b-c)[::-1]))
    z=dict(line=False,cx=float(c[0]),cy=float(c[1]),radius=r,start_angle=(aa if s>0 else ab)%360,end_angle=(ab if s>0 else aa)%360)
    pts=bc.sample(z);return z,pts if s>0 else pts[::-1]
def single(a,b,u,v,r):
    theta=math.acos(float(np.clip(np.dot(u,v),-1,1)));det=cross(u,v)
    if abs(det)<1e-6:return
    x,y=np.linalg.solve(np.column_stack((u,v)),b-a);d=r*math.tan(theta/2)
    if x-d<.75-1e-8 or y-d<2.4-1e-8:return
    p=a+(x-d)*u;q=b-(y-d)*v;c=p+np.sign(det)*r*left(u)
    z,pts=arc(c,p,q,np.sign(det),r)
    yield dict(primitives=[line(a,p),z,line(q,b)],points=np.vstack([a,pts,b]),radius=r,arcs=1,launch=float(x-d),radial=float(y-d))
def double(a,b,u,v,r,escape):
    start=a+.75*u;end=b-escape*v
    for s1,s2 in product((-1,1),repeat=2):
        c1=start+s1*r*left(u);c2=end+s2*r*left(v);dvec=c2-c1;d=np.linalg.norm(dvec)
        if d<1e-7 or abs((s2-s1)*r)>d:continue
        phi=math.atan2(dvec[1],dvec[0])-math.asin((s2-s1)*r/d)
        t=np.array([math.cos(phi),math.sin(phi)]);p1=c1-s1*r*left(t);p2=c2-s2*r*left(t)
        if np.dot(p2-p1,t)<-1e-6:continue
        da=(s1*(math.atan2(*(p1-c1)[::-1])-math.atan2(*(start-c1)[::-1])))%(2*math.pi)
        db=(s2*(math.atan2(*(end-c2)[::-1])-math.atan2(*(p2-c2)[::-1])))%(2*math.pi)
        if max(da,db)>math.pi+.0001 or min(da,db)<1e-6:continue
        z1,pa=arc(c1,start,p1,s1,r);z2,pb=arc(c2,p2,end,s2,r)
        yield dict(primitives=[line(a,start),z1,line(p1,p2),z2,line(end,b)],points=np.vstack([a,pa,pb,b]),radius=r,arcs=2,launch=.75,radial=escape)
report=[];exact={};changed=[];uncertain=[]
for group in out['groups']:
    name=group['row']['smp'];g=by[name];pp=g['smp_to_c1'];a,b=pp[0],pp[-1];u=unit(pp[1]-a);v=unit(b-pp[-2]);net='S'+name[3:]
    if name=='SMP13':
        exact[net]=copy.deepcopy(original['C13_exact_primitives'])
        report.append(dict(channel=name,status='preserved accepted C13',radius_mm=1.6,arcs=1,normal_launch_mm=.75,straight_radial_entry_mm=3.4));continue
    others=unary_union([h['lines'] for h in live if h is not g])
    foreignpads=unary_union([bc.pg(d) for d in pg['physical_pads'] if d['layer'] in (32,74) and d['net']!=net])
    foreignbody=unary_union([h['envelope'] for h in live if h is not g])
    dv=unary_union([Point(d['x'],d['y']).buffer(d['diameter']/2,quad_segs=96) for d in pg['vias']])
    allpads=unary_union([bc.pg(d) for d in pg['physical_pads'] if d['layer'] in (32,74)])
    ownbody=unary_union([f.m.base.shape_rect(np.array(g['capacitor']['centre_mm']),g['u'],1.9,1.8),f.m.base.shape_rect(np.array(g['resistor']['centre_mm']),left(g['u']),.6,.8)])
    pool=[];reject={}
    for r in (1.6,1.5,1.4,1.3,1.2,1.1,1.0):
        candidates=list(single(a,b,u,v,r) or [])
        for escape in (1.6,1.8,2.,2.2,2.4,2.6,2.8,3.,3.2):candidates.extend(double(a,b,u,v,r,escape))
        for item in candidates:
            ll=LineString(item['points']);reason=None
            gap=ll.distance(others)-.11;padgap=ll.distance(foreignpads)-.055;dvgap=ll.distance(dv)-.055
            if not ll.is_simple:reason='self-crossing'
            elif gap<1.165:reason='other RF clearance'
            elif padgap<.2005:reason='foreign pad'
            elif dvgap<.2005:reason='DC terminal via'
            elif ll.distance(g['qline'])<.31:reason='own RF/DC junction'
            elif ll.distance(foreignbody)<.405:reason='foreign component envelope'
            elif not ll.buffer(.055).disjoint(ownbody):reason='own inter-pad body'
            elif not Polygon(pg['board_outline']).buffer(-.2).covers(ll.buffer(.055)):reason='board edge'
            if reason is None and name in ('SMP02','SMP24'):
                # The outer broad turn is near mounting land A4/A3. Require
                # room for the whole shield row, not only trace clearance.
                for side in (-1,1):
                    off=ll.offset_curve(side*.438,quad_segs=32)
                    for t in np.arange(1.05,max(1.05,off.length-1.05),.08):
                        pt=off.interpolate(t)
                        if pt.distance(allpads)<.3255 or pt.distance(dv)<.3255:
                            reason='continuous shield row obstructed by mounting/pad land';break
                    if reason:break
            if reason:reject[reason]=reject.get(reason,0)+1;continue
            item.update(length=ll.length,other_RF_edge_gap_mm=gap,foreign_pad_gap_mm=padgap,foreign_DC_via_gap_mm=dvgap)
            pool.append(item)
    if not pool:
        uncertain.append(name);report.append(dict(channel=name,status='retained: broad arc not yet verified',rejections=reject));print(name,'RETAINED',reject,flush=True);continue
    # Prefer a single broad arc. A two-arc S bend is needed where the two rays do not meet ahead of both terminals.
    selected=min(pool,key=lambda t:(t['arcs'],-t['radius'],t['length']))
    group['smp_to_c1']=selected['points'].tolist();exact[net]=selected['primitives'];changed.append(name)
    row=dict(channel=name,status='candidate',radius_mm=selected['radius'],arcs=selected['arcs'],normal_launch_mm=selected['launch'],straight_radial_entry_mm=selected['radial'],other_RF_edge_gap_mm=selected['other_RF_edge_gap_mm'],foreign_pad_gap_mm=selected['foreign_pad_gap_mm'],foreign_DC_via_gap_mm=selected['foreign_DC_via_gap_mm'])
    report.append(row);print(json.dumps(row),flush=True)
out['exact_entry_primitives']=exact;out['entry_report']=report
out['uncertain_entries']=uncertain;out['changed_entries']=changed
(H/'entry_routes.json').write_text(json.dumps(out,indent=2))
(H/'rounding_proposal.json').write_text(json.dumps(dict(changed=changed,uncertain=uncertain,entries=report),indent=2))
