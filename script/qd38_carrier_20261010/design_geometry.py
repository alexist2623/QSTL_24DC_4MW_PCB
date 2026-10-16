"""Build the QD38 geometry and electrical plan in the copied project only."""
from pathlib import Path
import json, math, copy, hashlib, csv
import numpy as np
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import nearest_points
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPolygon, Circle

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
OUT=DEST/'review'; OUT.mkdir(exist_ok=True)
BASE=json.loads((H/'baseline_native.json').read_text())
SOURCE=ROOT/'deliverables/QD4_2SET_GDS_Preview_20261009/PCB_38pad_cavity_5p3x4p3mm_20261010_verification.json'
OLD=json.loads(SOURCE.read_text())
CENTER=np.array([9.75,42.5])
RF=[2,5,9,11,12,13,15,16,21,24,28,30,31,32,34,35]

def polygon(center, size, angle):
    t=math.radians(angle);u=np.array([math.cos(t),math.sin(t)]);v=np.array([-u[1],u[0]])
    return Polygon([np.array(center)+a*size[0]/2*u+b*size[1]/2*v for a,b in [(-1,-1),(1,-1),(1,1),(-1,1)]])

def generate():
    pads=[];bonds=[];physical=[]
    centers=np.array([p['center'] for p in OLD['pads']],dtype=float)
    for iteration in range(1500):
        polys=[]
        for k,p in enumerate(OLD['pads']):
            c=centers[k];u=c-np.array(p['chip']);u/=np.linalg.norm(u)
            support=.4*np.abs(u)+.125*np.abs([-u[1],u[0]])
            axes=[0] if p['side'] in ('LEFT','RIGHT') else [1] if p['side'] in ('TOP','BOTTOM') else [0,1]
            amount=max([0]+[((2.85 if d==0 else 2.35)+support[d]-abs(c[d]))/abs(u[d]) for d in axes])
            centers[k]+=amount*u
            polys.append(polygon(centers[k],[.8,.25],math.degrees(math.atan2(u[1],u[0]))))
        delta=np.zeros_like(centers);worst=1
        for k in range(38):
            j=(k+1)%38;g=polys[k].distance(polys[j]);worst=min(worst,g)
            if g<.16001:
                pa,pb=nearest_points(polys[k],polys[j]);d=np.array(pb.coords[0])-np.array(pa.coords[0]);d/=np.linalg.norm(d)
                delta[k]-=(.16001-g)*.55*d;delta[j]+=(.16001-g)*.55*d
        centers+=delta
        if worst>=.16:break
    else:raise ValueError('Pad spacing optimization did not converge')
    # Preserve the original wire ray and rotate the long pad axis onto it.
    # Translate outward on that ray only when its rotated corner needs clearance.
    for k,old in enumerate(OLD['pads']):
        p=copy.deepcopy(old);chip=np.array(p['chip']);initial=centers[k]
        u=initial-chip;u/=np.linalg.norm(u)
        c=initial.copy();support=.4*np.abs(u)+.125*np.abs([-u[1],u[0]])
        axes=[0] if p['side'] in ('LEFT','RIGHT') else [1] if p['side'] in ('TOP','BOTTOM') else [0,1]
        shift=max([0]+[((2.85 if k==0 else 2.35)+support[k]-abs(c[k]))/abs(u[k]) for k in axes])
        c+=max(0,shift)*u;angle=math.degrees(math.atan2(u[1],u[0]))%360
        poly=polygon(c,[.8,.25],angle);bond=c-.25*u
        p.update(center=c.tolist(),normal=u.tolist(),rotation=angle,polygon=list(poly.exterior.coords)[:-1],bond=bond.tolist(),rf=p['number'] in RF)
        p['absolute_center']=(c+CENTER).tolist();p['absolute_bond']=(bond+CENTER).tolist()
        p['absolute_chip']=(chip+CENTER).tolist()
        p['net_name']=('MW' if p['rf'] else 'DC')+str(p['number']).zfill(2)
        pads.append(p);physical.append(poly);bonds.append(LineString([chip,bond]))
    gap,gapi,gapj=min((a.distance(b),i,j) for i,a in enumerate(physical) for j,b in enumerate(physical) if i<j)
    cavity=box(-2.65,-2.15,2.65,2.15)
    cavity_gap=min(p.distance(cavity) for p in physical)
    crosses=[(i+1,j+1) for i,a in enumerate(bonds) for j,b in enumerate(bonds) if i<j and a.intersects(b)]
    assert gap>=.15,(gap,gapi,gapj)
    assert cavity_gap>=.2-1e-8,cavity_gap
    assert not crosses,crosses
    assert all(not a.intersects(physical[j]) for i,a in enumerate(bonds) for j in range(38) if i!=j)

    # The staggered outer row retains >=6 mm centre spacing while opening
    # the inner-layer routing corridor above the lower large mounting holes.
    top=[(x,y) for y in [50.5,56.5] for x in [3.75,9.75,15.75]]+[(6.75,61.7),(12.75,61.7)]
    banks=[top,[(x,85-y) for x,y in top]]
    smps=[]
    for bank,selected in zip(banks,[RF[:8],RF[8:]]):
        cost=np.array([[math.dist(pads[q-1]['absolute_center'],xy) for xy in bank] for q in selected])
        rows,cols=linear_sum_assignment(cost)
        for i,j in zip(rows,cols):
            q=selected[i]; x,y=bank[j]
            smps.append(dict(ref=f'SMP{q:02}',q=q,x=x,y=y,body_diameter=5.5,pattern='RF_Con',layer=1,rotation=0))
    smps.sort(key=lambda x:x['q'])
    body_gap=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-5.5 for i,a in enumerate(smps) for b in smps[i+1:])
    mounts=[p for p in BASE['pads'] if p['component'] is None]
    body_mount_gap=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-2.75-b['hole']/2 for a in smps for b in mounts)
    assert body_gap>=.49999 and body_mount_gap>0,(body_gap,body_mount_gap)
    plan=dict(status='WORK_IN_PROGRESS_NOT_NATIVE_VALIDATED',source_concept=str(SOURCE),board_outline=BASE['board_outline'],sample_center=CENTER.tolist(),cavity_mm=[5.3,4.3],cavity_depth_mm=1.2,pads=pads,smp=smps,mounts=mounts,
        checks=dict(pad_gap_mm=gap,pad_gap_pair=[gapi+1,gapj+1],cavity_gap_mm=cavity_gap,wire_crossings=crosses,smp_body_gap_mm=body_gap,smp_body_to_mount_hole_mm=body_mount_gap,rf_upper_count=8,rf_lower_count=8),
        stack='Unchanged source six-layer stack',rf_width_mm=.11,dc_width_mm=.125,rf_ground_gap_mm=.2,dc_clearance_mm=.15)
    (DEST/'design_plan.json').write_text(json.dumps(plan,indent=2))
    render(plan)
    print(json.dumps(plan['checks'],indent=2))

def render(plan):
    fig,(a,b)=plt.subplots(1,2,figsize=(12,10),gridspec_kw={'width_ratios':[1,1.9]})
    for ax in (a,b): ax.set_aspect('equal');ax.set_facecolor('#122a2b');ax.tick_params(labelsize=8)
    a.add_patch(MPolygon(plan['board_outline'],closed=True,facecolor='#164431',edgecolor='#ccdccc'))
    for p in plan['mounts']: a.add_patch(Circle((p['x'],p['y']),p['hole']/2,color='#e5e5e5'))
    for s in plan['smp']:
        a.add_patch(Circle((s['x'],s['y']),2.75,edgecolor='#cfd5da',facecolor='#64717c',alpha=.8))
        a.text(s['x'],s['y'],f"RF {s['q']}",ha='center',va='center',fontsize=7,color='white')
    for ax,off in [(a,CENTER),(b,np.zeros(2))]:
        ax.add_patch(MPolygon(np.array([[-2.65,-2.15],[2.65,-2.15],[2.65,2.15],[-2.65,2.15]])+off,facecolor='#253746',edgecolor='white'))
        for p in plan['pads']:
            color='#ec9f57' if p['category']=='ohmic' and p['rf'] else '#de94df' if p['rf'] else '#d1c078'
            ax.add_patch(MPolygon(np.array(p['polygon'])+off,facecolor=color,edgecolor='#ffffff',linewidth=.25))
            chip=np.array(p['chip'])+off;end=np.array(p['bond'])+off
            ax.plot([chip[0],end[0]],[chip[1],end[1]],color=color,lw=.6)
            if ax==b:
                loc=np.array(p['center'])+.60*np.array(p['normal'])
                ax.text(*loc,str(p['number']),ha='center',va='center',fontsize=8,color='#15242d')
    a.set(xlim=(-.5,20),ylim=(-.5,68.4),title='Proposed SMP positions: 8 above + 8 below',xlabel='Board X / mm',ylabel='Board Y / mm')
    b.set(xlim=(-4.65,4.65),ylim=(-4,4),title='QD38: pad long axes parallel to bond wires',xlabel='X relative to sample / mm',ylabel='Y relative to sample / mm')
    b.text(0,0,'5.3 x 4.3 mm\nBottom blind pocket\n1.2 mm deep',ha='center',va='center',color='white',fontsize=10)
    fig.suptitle('Copied QD38 carrier — placement preparation (routing not yet validated)',fontsize=14)
    fig.text(.42,.17,f"38 independent DC channels\n16 additional RF bias-tee channels\nMinimum rotated-pad gap: {plan['checks']['pad_gap_mm']:.3f} mm\nCavity clearance: {plan['checks']['cavity_gap_mm']:.3f} mm",fontsize=11)
    fig.tight_layout(rect=[0,.025,1,.95]);fig.savefig(OUT/'QD38_placement_preparation.png',dpi=180);plt.close(fig)

if __name__=='__main__':generate()
