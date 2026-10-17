"""Optimize local tangent curves without moving any components or DC vias."""
from solve_routes import H,ROOT,f,bc,data,groups,st,by,p,targets,zones
import json,math
import numpy as np
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
from scipy.optimize import differential_evolution
saved=json.loads((H/'routes.json').read_text())
for z in saved['groups']:
    g=by[z['row']['smp']];g['qd_to_c2']=np.array(z['qd_to_c2']);g['qline']=LineString(g['qd_to_c2']);g['lines']=unary_union([g['qline'],g['sline']])

def solve(name,other,zone,bounds):
    g=by[name];r=g['row'];u=g['u'];j=g['j'];e=np.array(r['end']);eu=np.array(r['outward']);c2=np.array(g['capacitor']['pads'][1]['centre_mm'])
    a=e+.20*eu;b=j-.75*u
    foreign=unary_union([h['envelope'] for h in groups if h is not g])
    fixed=unary_union([h['lines'] for h in groups if h is not g and h['row']['smp']!=other])
    peer=by[other]['qline']
    dc=Polygon(g['resistor']['pads'][1]['polygon_mm'])
    body=unary_union([f.m.base.shape_rect(np.array(g['capacitor']['centre_mm']),u,1.9,1.8),f.m.base.shape_rect(np.array(g['resistor']['centre_mm']),np.array([-u[1],u[0]]),.6,.8)])
    dv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in p['vias']])
    def make(v):
        mid=np.array(v[:2]);t=np.array([math.cos(v[2]),math.sin(v[2])])
        q1,r1=f.m.sym.bezier(a,mid,eu,t,v[3],v[4]);q2,r2=f.m.sym.bezier(mid,b,t,u,v[5],v[6])
        xy=np.vstack([e,q1,q2[1:],j,c2]);return xy,LineString(xy),min(r1,r2)
    def cost(v,details=False):
        xy,line,rad=make(v)
        tail=line.difference(f.m.QD_LAUNCH_ZONE)
        vals=[(line.distance(st['byroute'][name]),.205),(line.distance(foreign),.405),(line.distance(dc),.30),(line.distance(body),.055),(line.distance(dv),.258),(line.distance(fixed),.567),(tail.distance(fixed),1.285),(line.distance(peer),.567),(tail.distance(peer),1.285),(by[other]['qline'].difference(f.m.QD_LAUNCH_ZONE).distance(line),1.285),(rad,.51)]
        zg=line.intersection(zone)
        gap=min(zg.distance(peer),peer.intersection(zone).distance(line)) if not zg.is_empty and not peer.intersection(zone).is_empty else 2
        penalty=sum(max(0,t-x)**2 for x,t in vals)+(0 if line.is_simple else 10)
        score=20000*penalty+25*max(0,1.30-gap)**2+.002*line.length
        return (score,vals,gap,rad) if details else score
    result=differential_evolution(cost,bounds,popsize=9,maxiter=130,seed=43,polish=True,tol=.0001)
    score,vals,gap,rad=cost(result.x,True);print(name,'OPT',score,'gap',gap-.11,'rad',rad,'constraints',vals,flush=True)
    assert min(v-t for v,t in vals)>-.001,(name,vals)
    xy,line,rad=make(result.x);g['qd_to_c2']=xy;g['qline']=line;g['lines']=unary_union([line,g['sline']]);g['tail']=unary_union([line.difference(f.m.QD_LAUNCH_ZONE),g['sline']]);g['local_radius']=min(g['local_radius'],rad)
    (H/(name+'_optimized.json')).write_text(json.dumps(dict(points=xy.tolist(),variables=result.x.tolist(),gap_mm=gap-.11,radius_mm=rad),indent=2))

if __name__=='__main__':
    solve('SMP11','SMP12',zones[0],[(4.9,6),(40,43.7),(-2,-1),(.2,2),(.2,2),(.2,3),(.2,2)])
    solve('SMP12','SMP11',zones[0],[(6.5,7.5),(38.5,41.5),(-1.8,-.9),(.2,2),(.2,2),(.2,4),(.2,3)])
    solve('SMP24','SMP28',zones[1],[(13.7,15.3),(45,46.6),(-2.1,-.7),(.2,2),(.2,2),(.2,2),(.2,2)])
    serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items() if k not in ('envelope','capg','resg','lines','tail','qline','sline')} for g in groups]
    (H/'refined_routes.json').write_text(json.dumps(dict(groups=serial),indent=2))
