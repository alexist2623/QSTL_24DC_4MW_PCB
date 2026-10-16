"""Fit sixteen bias-tee pairs to the fixed mechanical proposal (plan only)."""
from pathlib import Path
from itertools import combinations
import math
import json
import csv
import hashlib
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, Circle, Rectangle
from shapely.geometry import box, Point, LineString, Polygon
from shapely.affinity import rotate, translate
from shapely.ops import unary_union
from latest_connection_plan import pg

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'QSTL_QD4_2SET_38PAD/ZIF10mm_Reference_End_20261016/updated_mechanical_plan.json'
OUT=ROOT/'QSTL_QD4_2SET_38PAD/All_RC_Placement_20261016'
OUT.mkdir(exist_ok=True)
COLORS=['#aa6428','#24609d','#9d326a','#44792e','#7250a1','#24838d',
        '#b34c31','#4b6da3','#8c5f30','#49863b','#a34a83','#217d9e',
        '#8b591f','#4b829e','#b74f3d','#287769']


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def shape_rect(c,u,w,h):
    theta=math.degrees(math.atan2(u[1],u[0]))
    return translate(rotate(box(-w/2,-h/2,w/2,h/2),theta,origin=(0,0)),*c)


def component(ref,c,u,pitch,size,body,kind):
    # Positive local X is terminal 1; the resistor uses a separately selected axis.
    pads=[dict(pin=1,centre_mm=(c+pitch/2*u).tolist(),polygon_mm=list(shape_rect(c+pitch/2*u,u,*size).exterior.coords)),
          dict(pin=2,centre_mm=(c-pitch/2*u).tolist(),polygon_mm=list(shape_rect(c-pitch/2*u,u,*size).exterior.coords))]
    b=shape_rect(c,u,*body)
    g=unary_union([b]+[Polygon(p['polygon_mm']) for p in pads])
    return dict(ref=ref,kind=kind,centre_mm=c.tolist(),angle_deg=math.degrees(math.atan2(u[1],u[0])),
                pads=pads,body_polygon_mm=list(b.exterior.coords)),g


def cubic(a,b,ua,ub,scale=.36):
    length=np.linalg.norm(b-a); t=np.linspace(0,1,65)[:,None]
    p1=a+ua*length*scale; p2=b-ub*length*scale
    xy=(1-t)**3*a+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*b
    d1=3*((1-t)**2*(p1-a)+2*(1-t)*t*(p2-p1)+t*t*(b-p2))
    d2=6*((1-t)*(p2-2*p1+a)+t*(b-2*p2+p1))
    cross=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0]); valid=cross>1e-9
    rad=float(np.min(np.linalg.norm(d1[valid],axis=1)**3/cross[valid])) if valid.any() else 1e6
    return xy,rad


def frame_at(line,s):
    p=np.array(line.interpolate(s).coords[0]); a=np.array(line.interpolate(max(0,s-.015)).coords[0]);b=np.array(line.interpolate(min(line.length,s+.015)).coords[0])
    u=(b-a)/np.linalg.norm(b-a)
    return p,u


def build_static(data):
    snap=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
    template=[p for p in snap['pads'] if p['component']=='SMP35']; origin=next(p for p in template if p['number']=='1')
    smp_bodies=[];smp_pads=[]
    for r in data['rows']:
        x,y=r['start'];smp_bodies.append((r['smp'],box(x-2.75,y-2.75,x+2.75,y+2.75)))
        for p in template:
            n=dict(p,x=p['x']+x-origin['x'],y=p['y']+y-origin['y'])
            smp_pads.append((r['smp'],p['number'],pg(n)))
    qd=[(int(p['number']),pg(p['after'])) for p in data['pads']]
    mounts=[(h['name'],Point(h['xy_mm']).buffer(2.75 if h['name'][0]=='P' else 2.0,quad_segs=48)) for h in data['mounts']]
    cx,cy=data['qd_centre_mm'];cavity=box(cx-2.15,cy-2.65,cx+2.15,cy+2.65)
    static=unary_union([g for _,g in smp_bodies+qd+mounts]+[cavity])
    byroute={}
    for r in data['rows']:
        byroute[r['smp']]=unary_union([g for n,p,g in smp_pads if not (n==r['smp'] and p=='1')]+
                                    [g for n,g in smp_bodies if n!=r['smp']]+[g for n,g in qd if n!=r['qd_pad']]+[g for _,g in mounts]+[cavity])
    return dict(static=static,byroute=byroute,smp_bodies=smp_bodies,smp_pads=smp_pads,qd=qd,mounts=mounts,cavity=cavity)


def candidates(r,route,st,outline):
    line=LineString(route['points_mm']);points=np.asarray(route['points_mm']);
    cumulative=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))]
    pool=[]
    offsets=(-2.,-1.5,-1.,-.5,0,.5,1.,1.5,2.) if r['smp'] in ('SMP05','SMP21','SMP02','SMP24') else (-.75,0,.75)
    for s,offset in ((s,o) for s in np.arange(5.3,line.length-4.4,.5) for o in offsets):
        base,tangent=frame_at(line,s);c=base+offset*np.array([-tangent[1],tangent[0]]);angle=math.atan2(tangent[1],tangent[0])
        # Prefer cardinal orientations; tangent-aligned fallback keeps L geometry.
        angles=[round(angle/(math.pi/2))*math.pi/2,angle]
        for theta in angles:
            u=np.array([math.cos(theta),math.sin(theta)])
            if np.dot(u,tangent)<.72:continue
            for side in (-1,1):
                v=side*np.array([-u[1],u[0]])
                j=c-3.0*u
                cap,cg=component(r['capacitor'],c,u,3.0,(1.,1.8),(3.5,1.8),'C1206')
                res,rg=component(r['resistor'],j+.85*v,-v,1.7,(1.1,1.),(1.6,.8),'R0603')
                g=cg.union(rg)
                if g.distance(st['static'])<.35:continue
                if not outline.buffer(-.3).covers(g):continue
                # Blend back to the original route, preserving its QD tangent and SMP escape.
                sa=max(.03,s-6.0);sb=min(line.length-2.8,s+4.0)
                if sb<=s+2.1:continue
                a,ua=frame_at(line,sa);b,ub=frame_at(line,sb)
                pre,ra=cubic(a,j,ua,u)
                post,rb=cubic(c+1.5*u,b,u,ub)
                if min(ra,rb)<1.0:continue
                qp=np.vstack([points[cumulative<sa],pre,c-1.5*u])
                sp=np.vstack([post,points[cumulative>sb]])
                qline=LineString(qp);sline=LineString(sp);lines=unary_union([qline,sline])
                if not qline.is_simple or not sline.is_simple:continue
                if min(lines.distance(st['byroute'][r['smp']])-.055,.3)<.15:continue
                if not outline.buffer(-.15).covers(lines.buffer(.055)):continue
                # C pad 1 and pad 2 are separate RF nodes; do not bridge its two lands.
                if qline.distance(Polygon(cap['pads'][0]['polygon_mm']))<.2:continue
                if sline.distance(Polygon(cap['pads'][1]['polygon_mm']))<.2:continue
                if lines.distance(Polygon(res['pads'][1]['polygon_mm']))<.3:continue
                body_gap=shape_rect(j+.85*v,-v,.6,.8)
                if lines.buffer(.055).intersects(body_gap):continue
                # Each branch terminates on its own capacitor pad, not under its body centre.
                cap_middle=shape_rect(c,u,1.9,1.8)
                if lines.buffer(.055).intersects(cap_middle):continue
                extra=(qline.length+sline.length+3)-line.length
                card=abs(math.sin(2*theta))<1e-5
                score=extra+.04*abs(s-line.length*.64)+(0 if card else 1.8)+.12*abs(offset)
                pool.append(dict(row=r,capacitor=cap,resistor=res,envelope=g,capg=cg,resg=rg,
                                 lines=lines,qd_to_c2=qp,smp_to_c1=sp,score=float(score),
                                 local_radius=min(ra,rb),cardinal=card,old_distance=s))
    pool.sort(key=lambda x:x['score'])
    return pool


def compatible(a,b):
    return (a['envelope'].distance(b['envelope'])>=.6 and
            a['lines'].distance(b['lines'])>=.26 and
            a['lines'].distance(b['envelope'])>=.405 and
            b['lines'].distance(a['envelope'])>=.405)


def solve(pools):
    chosen={};visits=0
    def assign(k):
        nonlocal visits
        if k==len(pools):return True
        best=None;options=None
        for i,pool in enumerate(pools):
            if i in chosen:continue
            valid=[p for p in pool if all(compatible(p,c) for c in chosen.values())]
            if not valid:return False
            if options is None or len(valid)<len(options):best=i;options=valid
        for c in options:
            visits+=1
            if visits>30000:raise RuntimeError('Candidate search limit')
            chosen[best]=c
            if assign(k+1):return True
            del chosen[best]
        return False
    if not assign(0):raise RuntimeError('No compatible all-pair placement')
    print('search visits',visits,flush=True)
    return [chosen[i] for i in range(len(pools))]


def as_component_geometry(c):
    return unary_union([Polygon(c['body_polygon_mm'])]+[Polygon(p['polygon_mm']) for p in c['pads']])


def audit(data,selected,st):
    comps=[c for s in selected for c in (s['capacitor'],s['resistor'])]
    env=[(c['ref'],as_component_geometry(c)) for c in comps]
    rc=min((a.distance(b),na,nb) for (na,a),(nb,b) in combinations(env,2))
    smp=min((g.distance(b),n,nb) for n,g in env for nb,b in st['smp_bodies'])
    qd=min((g.distance(b),n,str(nb)) for n,g in env for nb,b in st['qd'])
    mount=min((g.distance(b),n,nb) for n,g in env for nb,b in st['mounts'])
    rf=min((a['lines'].distance(b['lines'])-.11,a['row']['smp'],b['row']['smp']) for a,b in combinations(selected,2))
    foreign=min((a['lines'].distance(b['envelope'])-.055,a['row']['smp'],b['row']['smp']) for a in selected for b in selected if a is not b)
    for a,b in combinations(selected,2):assert compatible(a,b)
    assert len(comps)==32 and len(set(c['ref'] for c in comps))==32
    expected={r['smp']:r for r in data['rows']}
    terminal_checks=[]
    for s in selected:
        r=s['row'];c=s['capacitor'];res=s['resistor']
        assert r==expected[r['smp']]
        q=s['qd_to_c2'];sp=s['smp_to_c1']
        assert np.linalg.norm(q[0]-r['end'])<1e-8
        assert np.linalg.norm(q[-1]-c['pads'][1]['centre_mm'])<1e-8
        assert np.linalg.norm(sp[0]-c['pads'][0]['centre_mm'])<1e-8
        assert np.linalg.norm(sp[-1]-r['start'])<1e-8
        assert LineString(q).distance(Point(res['pads'][0]['centre_mm']))<1e-8
        assert s['lines'].distance(Polygon(res['pads'][1]['polygon_mm']))>=.3
        assert s['lines'].distance(st['byroute'][r['smp']])-.055>=.15
        u=np.subtract(c['pads'][0]['centre_mm'],c['pads'][1]['centre_mm'])/3
        v=np.subtract(res['pads'][1]['centre_mm'],res['pads'][0]['centre_mm'])/1.7
        assert abs(np.dot(u,v))<1e-8
        assert s['lines'].buffer(.055).disjoint(shape_rect(np.array(c['centre_mm']),u,1.9,1.8))
        # Only the intended resistor RF terminal is contacted. The inter-pad gap is excluded.
        assert s['lines'].buffer(.055).disjoint(shape_rect(np.array(res['centre_mm']),v,.6,.8))
        terminal_checks.append(dict(smp=r['smp'],qd_pad=r['qd_pad'],C=c['ref'],R=res['ref'],
                                    series_C_not_shorted=True,R_pad1_RF_junction=True,R_pad2_DC_isolated=True))
    return dict(placement_projection_passed=True,pairs=16,components=32,
                minimum_RC_envelope_gap_mm=rc,minimum_RC_to_SMP_body_mm=smp,
                minimum_RC_to_QD_pad_mm=qd,minimum_RC_to_mount_land_or_trial_head_mm=mount,
                minimum_guide_to_guide_edge_gap_mm=rf,minimum_guide_to_foreign_RC_mm=foreign,
                minimum_local_blend_radius_mm=min(a['local_radius'] for a in selected),
                route_crossings=0,RF_signal_vias=0,
                terminal_and_mapping_checks=terminal_checks,
                scope='2D body/pad/guide geometry only. Guide width 0.11 mm. Not native DRC or shield/copper-carrier cavity verification.')


def paint_shape(ax,g,**kwargs):
    if g.geom_type=='Polygon':ax.add_patch(Patch(list(g.exterior.coords),**kwargs))
    else:
        for p in g.geoms:paint_shape(ax,p,**kwargs)


def draw_component(ax,c,col,label=True):
    for p in c['pads']:
        paint_shape(ax,Polygon(p['polygon_mm']),fc='#dbb466',ec='#9b752e',lw=.4,zorder=7)
    paint_shape(ax,Polygon(c['body_polygon_mm']),fc='#f0dfb4' if c['kind']=='C1206' else '#334e55',
                ec=col,lw=.75,zorder=8)
    if label:
        x,y=c['centre_mm'];rot=90 if c['kind']=='R0603' and abs(math.sin(math.radians(c['angle_deg'])))>.7 else 0
        ax.text(x,y,c['ref'],ha='center',va='center',fontsize=7,rotation=rot,
            color='#273d44' if c['kind']=='C1206' else 'white',weight='bold',zorder=10,clip_on=True)
    if c['kind']=='R0603':
        x,y=c['pads'][1]['centre_mm'];ax.add_patch(Circle((x,y),.14,fc='#e9f9fd',ec='#28799c',lw=.7,zorder=10))


def paint(ax,data,selected,st,ylim=None):
    x0,y0,x1,y1=data['board_bounds_xy_mm']
    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#f0f5f2',ec='#288577',lw=1.3,zorder=0))
    ax.plot([9.75,9.75],[y0,y1],':',lw=.6,color='#a5b2b7')
    for m in data['mounts']:
        x,y=m['xy_mm'];rr=2.75 if m['name'][0]=='P' else 2.
        ax.add_patch(Circle((x,y),rr,fc='#e6d2a7',ec='#a48248',lw=.7))
        ax.add_patch(Circle((x,y),m['measured_diameter_mm']/2,fc='white',ec='#71868d',lw=.8))
        ax.text(x,y+rr+.35,m['name'],ha='center',va='bottom',fontsize=8,color='#63747b',weight='bold',clip_on=True)
    for r in data['rows']:
        x,y=r['start'];ax.add_patch(Rectangle((x-2.75,y-2.75),5.5,5.5,fc='#dce6e8',ec='#9fb4b9',lw=.6,ls=':'))
        ax.add_patch(Circle((x,y),2.75,fc='none',ec='#94adb5',lw=.7))
        ax.text(x,y+2.15,r['smp'],ha='center',va='center',fontsize=7.5,weight='bold',color='#2f545f',clip_on=True)
        ax.text(x,y-2.05,'QD '+str(r['qd_pad']),ha='center',va='center',fontsize=7,color='#466a73',clip_on=True)
    for name,num,g in st['smp_pads']:
        paint_shape(ax,g,fc='#e6c77e' if num=='1' else '#a6babd',ec='#6a858c',lw=.4,zorder=3)
    for n,g in st['qd']:paint_shape(ax,g,fc='#cfaf61',ec='#aa8c46',lw=.3,zorder=6)
    paint_shape(ax,st['cavity'],fc='#233f4b',ec='#233f4b',lw=.6,zorder=4)
    ax.text(*data['qd_centre_mm'],'QD',ha='center',va='center',fontsize=10,color='white',zorder=6,clip_on=True)
    for i,s in enumerate(selected):
        col=COLORS[i]
        for k in ('qd_to_c2','smp_to_c1'):
            xy=s[k];ax.plot(xy[:,0],xy[:,1],color=col,lw=1.1,zorder=5)
        draw_component(ax,s['capacitor'],col);draw_component(ax,s['resistor'],col)
    # The connector body uses the stored actual-model envelope.
    bounds=data['ZIF']['bounds_mm']
    ax.add_patch(Rectangle((bounds[0],bounds[1]),bounds[3]-bounds[0],bounds[4]-bounds[1],fc='#d3e1e5',ec='#66818b',lw=.8))
    ax.text(9.75,-7.05,'ZIF',ha='center',va='center',fontsize=9,color='#355460',clip_on=True)
    ax.set(xlim=(x0-1.2,x1+1.2),ylim=ylim or (y0-1.2,y1+1.2),aspect='equal')
    ax.set_xlabel('X (mm)',fontsize=9);ax.set_ylabel('Y (mm)',fontsize=9)
    ax.tick_params(labelsize=8);ax.grid(alpha=.13,lw=.5)


def render(data,sel,st,checks):
    fig=plt.figure(figsize=(15,12.6),dpi=200)
    gs=fig.add_gridspec(1,2,width_ratios=[.92,1.42],left=.055,right=.98,bottom=.11,top=.85,wspace=.13)
    ax=fig.add_subplot(gs[0,0]);paint(ax,data,sel,st)
    ax.set_title('Full outline | 32.60 x 99.025 mm',fontsize=12,pad=12)
    ax=fig.add_subplot(gs[0,1]);paint(ax,data,sel,st,(18.5,73.5))
    ax.set_title('All 16 bias-tee pairs | R0603 + C1206',fontsize=12,pad=12)
    fig.suptitle('16-RF carrier: R/C placement plan',fontsize=22,y=.97)
    fig.text(.5,.929,'Fixed SMP / QD / P1-P4 + A3-A4 / ZIF positions; latest mechanical outline retained',ha='center',fontsize=11)
    fig.text(.5,.900,'C: Yageo CC1206JKNPO9BN104   |   Gold = copper pads   |   Light C / dark R = bodies   |   Blue dots = resistor DC terminals',ha='center',fontsize=9.5)
    fig.text(.5,.071,'SMP -> C1 | C2 -> R1 / QD RF node | R2 -> DC. RF guide paths split at each series capacitor.',ha='center',fontsize=10)
    fig.text(.5,.047,f"32 component envelopes: no overlap | R/C minimum {checks['minimum_RC_envelope_gap_mm'][0]:.3f} mm | R/C to SMP minimum {checks['minimum_RC_to_SMP_body_mm'][0]:.3f} mm",ha='center',fontsize=10)
    fig.text(.5,.024,'PLAN ONLY — native PCB unchanged. DC routes, shielding, masks, carrier cavities and Altium DRC remain to be implemented/checked.',ha='center',fontsize=9,color='#96543f')
    fig.savefig(OUT/'All_16_RC_Overview.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,15.8),dpi=230);paint(ax,data,sel,st,(18.5,73.5))
    ax.set_title('All sixteen R/C pairs on the fixed SMP plan\nR: 0603  |  C: 1206 Yageo CC1206JKNPO9BN104',fontsize=14,pad=18)
    fig.text(.5,.022,'Conceptual RF guides; no RF signal vias. Native PCB / DC / masks / shields are not updated.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.99));fig.savefig(OUT/'All_16_RC_Enlarged.png');plt.close(fig)


def main():
    data=json.loads(SOURCE.read_text());st=build_static(data)
    protected=[SOURCE]+[ROOT/'QSTL_QD4_2SET_38PAD'/s for s in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','pin_mapping.csv')]
    before={str(p):digest(p) for p in protected}
    pools=[candidates(r,g,st,box(*data['board_bounds_xy_mm'])) for r,g in zip(data['rows'],data['routes'])]
    for r,p in zip(data['rows'],pools):print(r['smp'],len(p),'cardinal',sum(x['cardinal'] for x in p),flush=True)
    sel=solve(pools);checks=audit(data,sel,st)
    render(data,sel,st,checks)
    serial=[]
    for s in sel:
        serial.append({k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in s.items() if k not in ('envelope','capg','resg','lines')})
    assert before=={str(p):digest(p) for p in protected}
    result=dict(status='ALL_16_RC_PLACEMENT_PLAN_NOT_APPLIED',source_plan=str(SOURCE),source_hashes=before,
                native_files_unchanged=True,board_bounds_xy_mm=data['board_bounds_xy_mm'],groups=serial,checks=checks,
                fixed_geometry='All SMP/QD pads, mounting holes and ZIF unchanged from the source mechanical plan.',
                pending='Native PCB/schematic updates, DC routing, coplanar ground/shield fences, masks, carrier cavity fit, impedance and native DRC.')
    (OUT/'all_rc_placement_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'component_positions.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['channel','qd_pad','ref','package','x_mm','y_mm','angle_deg'])
        for s in sel:
            for c in (s['capacitor'],s['resistor']):w.writerow([s['row']['smp'],s['row']['qd_pad'],c['ref'],c['kind'],*c['centre_mm'],c['angle_deg']])
    print(json.dumps(checks,indent=2),flush=True)


def validate_and_redraw_saved():
    data=json.loads(SOURCE.read_text());st=build_static(data)
    path=OUT/'all_rc_placement_audit.json';saved=json.loads(path.read_text())
    assert saved['source_hashes']=={p:digest(Path(p)) for p in saved['source_hashes']}
    selected=[]
    for row in saved['groups']:
        s=dict(row)
        for k in ('qd_to_c2','smp_to_c1'):s[k]=np.asarray(s[k])
        s['envelope']=unary_union([as_component_geometry(s['capacitor']),as_component_geometry(s['resistor'])])
        s['lines']=unary_union([LineString(s['qd_to_c2']),LineString(s['smp_to_c1'])])
        selected.append(s)
    checks=audit(data,selected,st)
    render(data,selected,st,checks)
    saved['checks']=checks;saved['saved_plan_reopened_and_validated']=True
    path.write_text(json.dumps(saved,indent=2)+'\n')
    print(json.dumps({k:v for k,v in checks.items() if k!='terminal_and_mapping_checks'},indent=2))


if __name__=='__main__':
    if '--redraw-saved' in sys.argv:validate_and_redraw_saved()
    else:main()
