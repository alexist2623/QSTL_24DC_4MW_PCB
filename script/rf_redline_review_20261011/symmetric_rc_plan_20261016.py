"""Fixed-angle, mirror-symmetric R/C placement and checked RF guide plan."""
import json
import math
import csv
import sys
from itertools import product, combinations
from pathlib import Path
import numpy as np
from shapely.geometry import Point, LineString, Polygon, box
from shapely.affinity import scale
from shapely.ops import unary_union
import all_rc_placement_20261016 as base

ROOT=base.ROOT
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Symmetric_RC_Placement_20261016'
OUT.mkdir(exist_ok=True)
CX,CY=9.75,46.15
PAIRS=[('SMP05','SMP21'),('SMP02','SMP24'),('SMP09','SMP30'),('SMP35','SMP31'),
       ('SMP34','SMP32'),('SMP11','SMP28'),('SMP12','SMP16'),('SMP15','SMP13')]
QUADS=[('SMP02','SMP24','SMP05','SMP21',0.,.735,44.25),
       ('SMP11','SMP28','SMP09','SMP30',30.,2.4,37.5),
       ('SMP12','SMP16','SMP35','SMP31',60.,4.,31.8),
       ('SMP15','SMP13','SMP34','SMP32',90.,7.75,26.7)]


def build_groups(data):
    rows={r['smp']:r for r in data['rows']};groups={}
    for ll,lr,ul,ur,angle,x,y in QUADS:
        theta=math.radians(angle);u=np.array([-math.cos(theta),-math.sin(theta)])
        v=np.array([u[1],-u[0]])
        if angle==0:v=-v
        for name,sx,sy in ((ll,1,1),(lr,-1,1),(ul,1,-1),(ur,-1,-1)):
            c=np.array([CX+sx*(x-CX),CY+sy*(y-CY)]);cu=u*np.array([sx,sy]);rv=v*np.array([sx,sy])
            j=c-3*cu;r=rows[name]
            cap,cg=base.component(r['capacitor'],c,cu,3.,(1.,1.8),(3.5,1.8),'C1206')
            res,rg=base.component(r['resistor'],j+.85*rv,-rv,1.7,(1.1,1.),(1.6,.8),'R0603')
            groups[name]=dict(row=r,capacitor=cap,resistor=res,envelope=cg.union(rg),capg=cg,resg=rg,
                              u=cu,j=j,acute_angle_deg=angle)
    return [groups[r['smp']] for r in data['rows']]


def bezier(a,b,ua,ub,ca,cb):
    p1=a+ca*ua;p2=b-cb*ub;t=np.linspace(0,1,201)[:,None]
    xy=(1-t)**3*a+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*b
    d1=3*((1-t)**2*(p1-a)+2*(1-t)*t*(p2-p1)+t*t*(b-p2))
    d2=6*((1-t)*(p2-2*p1+a)+t*(b-2*p2+p1));z=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0]);ok=z>1e-9
    radius=float(np.min(np.linalg.norm(d1[ok],axis=1)**3/z[ok])) if ok.any() else 1e6
    return xy,radius


def placement_check(data,groups,st):
    comps=[(c['ref'],base.as_component_geometry(c)) for g in groups for c in (g['capacitor'],g['resistor'])]
    clashes=[]
    for (na,a),(nb,b) in combinations(comps,2):
        if a.distance(b)<.35:clashes.append([na,nb,a.distance(b)])
    for n,g in comps:
        if g.distance(st['static'])<.3:clashes.append([n,'static',g.distance(st['static'])])
    return clashes


def routes_for_group(data,g,groups,st):
    r=g['row'];u=g['u'];j=g['j'];e=np.array(r['end']);eu=np.array(r['outward']);s=np.array(r['start'])
    old=next(r for r in data['routes'] if r['smp']==g['row']['smp']);v=np.array(old['entry_outward']);q=s+2.8*v
    c1=np.array(g['capacitor']['pads'][0]['centre_mm']);c2=np.array(g['capacitor']['pads'][1]['centre_mm'])
    foreign=unary_union([other['envelope'] for other in groups if other is not g])
    obs=st['byroute'][r['smp']]
    own_body=unary_union([base.shape_rect(np.array(g['capacitor']['centre_mm']),u,1.9,1.8),
                         base.shape_rect(np.array(g['resistor']['centre_mm']),np.array([-u[1],u[0]]),.6,.8)])
    dc=Polygon(g['resistor']['pads'][1]['polygon_mm'])
    sets=[];controls=(.4,.7,1.,1.5,2.,2.5,3.,4.,5.,6.,8.,10.,12.,15.)
    for mode in ('qd','smp'):
        pool=[]
        for ca,cb in product(controls,repeat=2):
            xy,rad=bezier(e,j,eu,u,ca,cb) if mode=='qd' else bezier(c1,q,u,-v,ca,cb)
            if rad<.5:continue
            xy=np.vstack([xy,c2]) if mode=='qd' else np.vstack([xy,s])
            line=LineString(xy)
            if not line.is_simple:continue
            if line.distance(obs)<.205:continue
            if line.distance(foreign)<.405:continue
            if line.distance(dc)<.3:continue
            if not line.buffer(.055).disjoint(own_body):continue
            otherpad=g['capacitor']['pads'][0 if mode=='qd' else 1]
            if line.distance(Polygon(otherpad['polygon_mm']))<.2:continue
            pool.append(dict(points=xy,line=line,radius=rad,score=line.length+.02*(ca+cb)))
        pool.sort(key=lambda a:a['score']);sets.append(pool)
    print(r['smp'],'segments',*[len(p) for p in sets],flush=True)
    combos=[]
    for a,b in product(*sets):
        if a['line'].distance(b['line'])<.26:continue
        combos.append(dict(**g,qd_to_c2=a['points'],smp_to_c1=b['points'],lines=unary_union([a['line'],b['line']]),
                           local_radius=min(a['radius'],b['radius']),score=a['score']+b['score']))
    combos.sort(key=lambda a:a['score'])
    return combos[:160]


def symmetry_check(groups):
    by={g['row']['smp']:g for g in groups};pairs=[]
    for l,r in PAIRS:
        a=by[l];b=by[r]
        errors=[]
        for k in ('capacitor','resistor'):
            ga=base.as_component_geometry(a[k]);gb=base.as_component_geometry(b[k])
            errors.append(scale(ga,xfact=-1,yfact=1,origin=(CX,0)).hausdorff_distance(gb))
            for pa,pb in zip(a[k]['pads'],b[k]['pads']):
                errors.append(np.linalg.norm(np.array([2*CX-pa['centre_mm'][0],pa['centre_mm'][1]])-pb['centre_mm']))
        for g in (a,b):
            theta=abs(g['capacitor']['angle_deg'])%180
            actual=min(theta,180-theta)
            assert abs(actual-g['acute_angle_deg'])<1e-10
        assert max(errors)<1e-10
        pairs.append(dict(left=l,right=r,acute_C_axis_angle_deg=a['acute_angle_deg'],mirror_error_mm=max(errors)))
    centres={}
    for n,target in [('SMP02',1.485),('SMP05',1.485),('SMP21',18.015),('SMP24',18.015)]:
        bounds=by[n]['envelope'].bounds;x=(bounds[0]+bounds[2])/2
        assert abs(x-target)<1e-10,(n,x,target)
        centres[n]=x
    return dict(mirror_axis_x_mm=CX,pairs=pairs,central_group_x_mm=centres,
                midpoint_basis='Inward edge of measured 2.00 mm A3/A4 bore to aligned QD bond-pad outer-end midpoint line.')


def add_guides(ax,groups):
    ax.axvline(CX,color='#c14739',ls='--',lw=.8,alpha=.6)
    for x in (1.485,18.015):
        ax.plot([x,x],[42.7,50.4],color='#4a87b0',lw=.85,ls='--',zorder=12)
        ax.text(x,50.5,f'X={x:.3f}',fontsize=8,color='#28658e',ha='center',clip_on=True)
    for a,b,cy in [(-3.55,6.52,46.15),(12.98,23.05,46.15)]:
        ax.annotate('',xy=(a,cy),xytext=(b,cy),arrowprops=dict(arrowstyle='<->',color='#5a7581',lw=.7),zorder=15)
    for x in (-3.55,23.05):
        ax.plot([x,x],[45.45,46.3],color='#5a7581',lw=.6,zorder=15)
        ax.plot(x,45.45,'o',ms=2,color='#5a7581',zorder=15)
    for g in groups:
        if g['row']['smp'] in ('SMP11','SMP12','SMP15','SMP09','SMP35','SMP34'):
            x,y=g['capacitor']['centre_mm']
            ax.text(x-1.8,y+.1,f"{g['acute_angle_deg']:.0f}°",ha='right',va='center',fontsize=8,color='#52717e',clip_on=True)


def render(data,sel,st,checks):
    fig,ax=base.plt.subplots(figsize=(10.5,15.8),dpi=230)
    base.paint(ax,data,sel,st,(18.5,73.5));add_guides(ax,sel)
    ax.set_title('Symmetric R/C plan | fixed 30° / 60° / 90° angles\nR0603 + Yageo CC1206JKNPO9BN104 C1206',fontsize=14,pad=18)
    fig.text(.5,.027,'Mirrored about X=9.75 mm. Central RC groups aligned to hole-edge / QD-end midpoints.',ha='center',fontsize=9)
    fig.text(.5,.011,'PLAN ONLY: native PCB unchanged; DC, ground/shielding, masks and native DRC pending.',ha='center',fontsize=9,color='#995b44')
    fig.tight_layout(rect=(0,.045,1,.99));fig.savefig(OUT/'Symmetric_RC_Enlarged.png');base.plt.close(fig)
    fig=base.plt.figure(figsize=(15,12.6),dpi=200)
    gs=fig.add_gridspec(1,2,width_ratios=(.9,1.4),left=.05,right=.98,bottom=.105,top=.86,wspace=.13)
    ax=fig.add_subplot(gs[0,0]);base.paint(ax,data,sel,st);ax.set_title('32.60 x 99.025 mm | fixed outline / holes / ZIF',fontsize=11,pad=12)
    ax=fig.add_subplot(gs[0,1]);base.paint(ax,data,sel,st,(18.5,73.5));add_guides(ax,sel);ax.set_title('Mirror-symmetric R/C placement',fontsize=12,pad=12)
    fig.suptitle('16-channel R/C plan: explicit angles and symmetry',fontsize=21,y=.97)
    fig.text(.5,.925,'30°: 11/28 + 09/30   |   60°: 12/16 + 35/31   |   90°: 15/13 + 34/32',ha='center',fontsize=11)
    fig.text(.5,.900,'Centre lines: 02/05 at X=1.485 mm; 21/24 at X=18.015 mm. All angles measured from horizontal.',ha='center',fontsize=10)
    fig.text(.5,.064,'Exact left/right component symmetry; existing QD endpoints and electrical membership retained.',ha='center',fontsize=10)
    fig.text(.5,.042,f"2D check: no component overlaps / guide crossings | Minimum R/C gap {checks['minimum_RC_envelope_gap_mm'][0]:.3f} mm",ha='center',fontsize=10)
    fig.text(.5,.020,'PLAN ONLY — native PCB, DC routing, shield fences, masks and Altium DRC not updated.',ha='center',fontsize=9,color='#995b44')
    fig.savefig(OUT/'Symmetric_RC_Overview.png');base.plt.close(fig)
    fig,ax=base.plt.subplots(figsize=(13,6),dpi=220)
    base.paint(ax,data,sel,st,(41.4,51.1));add_guides(ax,sel)
    ax.set_xlim(-6.8,26.3)
    for g in sel:
        if g['row']['smp'] in ('SMP02','SMP05','SMP21','SMP24'):
            x0,y0,x1,y1=g['envelope'].bounds
            ax.add_patch(base.Rectangle((x0,y0),x1-x0,y1-y0,fc='none',ec='#2b7199',lw=.75,ls='--',zorder=12))
            ax.plot((x0+x1)/2,(y0+y1)/2,'+',color='#2b7199',ms=8,zorder=14)
    ax.set_title('Central RC alignment: centre of each complete pair envelope\nMidpoint between inward hole edge and QD pad-end line',fontsize=14,pad=16)
    fig.text(.5,.080,'Left: (-3.55 + 6.52) / 2 = 1.485 mm     |     Right: (12.98 + 23.05) / 2 = 18.015 mm',ha='center',fontsize=11)
    fig.text(.5,.037,'Dashed boxes = complete R/C pad + body envelopes; crosses = group centres. A3/A4 measured hole diameter: 2.00 mm.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.12,1,.99));fig.savefig(OUT/'Central_RC_Alignment.png');base.plt.close(fig)


def main():
    data=json.loads(base.SOURCE.read_text());st=base.build_static(data);groups=build_groups(data)
    protected=[base.SOURCE]+[ROOT/'QSTL_QD4_2SET_38PAD'/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','pin_mapping.csv')]
    hashes={str(p):base.digest(p) for p in protected}
    sym=symmetry_check(groups);clashes=placement_check(data,groups,st)
    print('placement clashes',clashes,flush=True)
    assert not clashes
    pools=[routes_for_group(data,g,groups,st) for g in groups]
    if any(not p for p in pools):raise RuntimeError('A fixed-angle group requires a revised symmetric position')
    sel=base.solve(pools);checks=base.audit(data,sel,st);render(data,sel,st,checks)
    serial=[]
    for s in sel:
        serial.append({k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in s.items() if k not in ('envelope','capg','resg','lines')})
    assert hashes=={str(p):base.digest(p) for p in protected}
    record=dict(status='SYMMETRIC_RC_PLAN_NOT_APPLIED',source_hashes=hashes,groups=serial,checks=checks,
                symmetry=sym,native_files_unchanged=True,board_bounds_xy_mm=data['board_bounds_xy_mm'])
    (OUT/'symmetric_rc_audit.json').write_text(json.dumps(record,indent=2)+'\n')
    with (OUT/'component_positions.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['channel','qd_pad','ref','package','x_mm','y_mm','rotation_deg','C_axis_acute_deg'])
        for s in sel:
            for c in (s['capacitor'],s['resistor']):w.writerow([s['row']['smp'],s['row']['qd_pad'],c['ref'],c['kind'],*c['centre_mm'],c['angle_deg'],s['acute_angle_deg']])
    print(json.dumps({k:v for k,v in checks.items() if k!='terminal_and_mapping_checks'},indent=2))


def validate_saved():
    path=OUT/'symmetric_rc_audit.json';rec=json.loads(path.read_text());data=json.loads(base.SOURCE.read_text());st=base.build_static(data)
    groups=[]
    for item in rec['groups']:
        g=dict(item)
        for k in ('qd_to_c2','smp_to_c1','u','j'):g[k]=np.asarray(g[k])
        g['envelope']=unary_union([base.as_component_geometry(g['capacitor']),base.as_component_geometry(g['resistor'])])
        g['lines']=unary_union([LineString(g['qd_to_c2']),LineString(g['smp_to_c1'])])
        groups.append(g)
    assert not placement_check(data,groups,st)
    sym=symmetry_check(groups);checks=base.audit(data,groups,st)
    assert rec['source_hashes']=={p:base.digest(Path(p)) for p in rec['source_hashes']}
    render(data,groups,st,checks)
    rec['symmetry']=sym;rec['checks']=checks;rec['saved_plan_reopened_and_validated']=True
    path.write_text(json.dumps(rec,indent=2)+'\n')
    print('Saved plan: angle, mirror, midpoint, topology and geometry checks passed. Native source hashes unchanged.')


if __name__=='__main__':
    if '--validate-saved' in sys.argv:validate_saved()
    else:main()
