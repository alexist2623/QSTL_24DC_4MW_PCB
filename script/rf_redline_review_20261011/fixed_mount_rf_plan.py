"""Offline RF connection proposal with fixed lower M2 and curved pad-15 exit."""
import csv
import json
import math
from copy import deepcopy
from itertools import combinations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import LineString, box
from outline_mount_concept import ROOT, OUT, build, draw, sha, annotate_pair, RED
from latest_connection_plan import rounded, check, pg

COLORS=['#147eab','#187657','#a65e10','#964e38','#3a7834','#146b77',
        '#b04b44','#734d9b','#8d50a2','#28765c','#626a21','#9a5e29',
        '#c13b86','#425b9a','#5a6771','#8c6530']


def geometry():
    old,rows,pads,om,_,_,snapshot=build()
    mounts=deepcopy(om)
    for a,b in zip(om,mounts):
        if abs(a['hole']-2.1)<.01 and a['y']>60:
            b['y']=70.;b['concept_group']='upper_M2'
        elif abs(a['hole']-2.1)<.01:
            b['concept_group']='fixed_lower_M2'
            assert all(a[k]==b[k] for k in ('x','y','hole','size_x','size_y'))
        elif abs(a['hole']-4)<.01:
            b['y']=a['y']-.75;b['concept_group']='large_lower_mount'
        else:b['concept_group']='retained_M1'
    # Raise the four lower rows together to retain 5.75 mm SMP pitch after
    # moving the end pair outward, while clearing the large mounting lands.
    for r in rows:
        if r['position'].startswith(('P5','P6','P7','P8')):r['start'][1]+=.60
    return old,rows,pads,om,mounts,snapshot


def routes(rows):
    buses={'P1L':8.05,'P1R':11.30,'P2L':6.75,'P2R':12.95,
           'P3L':5.85,'P3R':13.75,'P4L':4.95,'P4R':14.65,
           'P5L':4.95,'P5R':14.65,'P6L':5.80,'P6R':13.75,
           'P7L':6.65,'P7R':12.85,'P8L':8.20,'P8R':10.90}
    result=[];arc_report=None
    for r in rows:
        s=np.array(r['start']);e=np.array(r['end']);u=np.array(r['outward'])
        upper='upper' in r['kind'];sgn=1 if upper else -1
        if r['qd_pad']==15:
            radius=1.5
            theta0=math.atan2(u[1],u[0]);theta1=-math.pi/2
            # Exact circular arc starts at the outward pad-end midpoint.
            # Its start tangent equals the pad axis and final tangent is -Y.
            t=np.linspace(theta0,theta1,301)
            arc=e+radius*np.column_stack((np.sin(t)-math.sin(theta0),
                                        -np.cos(t)+math.cos(theta0)))
            v=arc[-1]
            lead=rounded([s,[v[0],s[1]],v],trim=.4)
            result.append(LineString(list(lead.coords)+[tuple(p) for p in arc[-2::-1]]))
            arc_report=dict(qd_pad=15,smp=r['smp'],radius_mm=radius,
                start_mm=list(e),end_mm=list(v),start_tangent=list(u),
                final_tangent=[0.,-1.],straight_lead_out_mm=0.,
                curved_sweep_deg=math.degrees(theta1-theta0),
                scope='Illustrative circular departure; radius is a planning value.')
        else:
            e1=e+u*.65;b=buses[r['position']]
            result.append(rounded([s,[b,s[1]],[b,e1[1]+sgn*.45],e1,e]))
    return result,arc_report


def mechanics(rows,mounts):
    bodies=[(r['smp'],box(r['start'][0]-2.75,r['start'][1]-2.75,
                          r['start'][0]+2.75,r['start'][1]+2.75)) for r in rows]
    body_gap=min((a.distance(b),an,bn) for (an,a),(bn,b) in combinations(bodies,2))
    mount_gap=min((pg(a).distance(pg(b)),a['concept_group'],b['concept_group'])
                  for a,b in combinations(mounts,2))
    body_mount=min((body.distance(pg(p)),name,p['concept_group']) for name,body in bodies for p in mounts)
    return dict(SMP_bounding_box_gap_mm=body_gap,mount_land_gap_mm=mount_gap,
                SMP_bounding_box_to_mount_land_gap_mm=body_mount)


def overlay(ax,rows,paths,pads,number=True):
    bypad={r['qd_pad']:i for i,r in enumerate(rows)}
    for i,(r,l) in enumerate(zip(rows,paths)):
        x,y=l.xy;ax.plot(x,y,color=COLORS[i],lw=1.25,zorder=12)
    if number:
        for pr in pads:
            p=pr['after'];n=int(pr['number'])
            ax.text(p['x'],p['y'],str(n),ha='center',va='center',fontsize=6.7,
                    color='#182a30',zorder=14,clip_on=True,
                    fontweight='bold' if n in bypad else 'normal')


def render(rows,paths,pads,mounts,snapshot,arc):
    fig=plt.figure(figsize=(13,16),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(.92,1.22),height_ratios=(1,1.04),
                       top=.91,bottom=.14,left=.065,right=.96,wspace=.23,hspace=.28)
    full=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);lower=fig.add_subplot(gs[1,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,73.5))
    overlay(full,rows,paths,pads,False)
    full.set_title('Proposed RF connections\n19.50 x 72.50 mm (trial)',fontsize=13)
    draw(detail,rows,pads,mounts,snapshot,True,ylim=(36.8,47.2))
    detail.set_xlim(4.5,15.0);overlay(detail,rows,paths,pads)
    detail.set_title('QD detail: pad 15 curves immediately\nPad positions and circuit identities retained',fontsize=12)
    p15=arc['start_mm']
    detail.annotate('15: no straight lead-out',xy=(p15[0]-.1,p15[1]-.17),xytext=(8.15,37.4),
                    fontsize=9,color=COLORS[12],arrowprops=dict(arrowstyle='->',color=COLORS[12]),zorder=20)
    draw(lower,rows,pads,mounts,snapshot,True,ylim=(10.2,31.2))
    overlay(lower,rows,paths,pads,False)
    lower.set_title('Lower mounting and SMP arrangement\nLower M2 remains at its original position',fontsize=12)
    annotate_pair(lower,13.19,'M2 FIXED\nY = 13.19 mm','#235c99')
    annotate_pair(lower,17.34,'M2.5 location\n18.09 -> 17.34 mm',RED)
    annotate_pair(lower,25.6,'SMP12 / SMP16: Y = 28.60\nSMP15 / SMP13: Y = 22.85','#285b61')
    fig.suptitle('Revised proposed RF connection plan',fontsize=20,y=.976)
    fig.text(.5,.948,'Lower M2 fixed | Large mounting pair: -0.75 mm | Pad 15: tangent curve begins at the pad end',ha='center',fontsize=11)
    fig.text(.5,.103,'Lower SMP rows: Y = 40.10 / 34.35 / 28.60 / 22.85 mm; 5.75 mm pitch. Upper rows unchanged from the extension concept.',ha='center',fontsize=9.6)
    fig.text(.5,.078,'Each connection represents SMP -> C1206 -> R0603 bias junction -> QD; R/C placement is not drawn or verified here.',ha='center',fontsize=10)
    fig.text(.5,.052,'Mount labels follow the user terminology; actual retained drills: M2 positions 2.10 mm, large positions 4.00 mm.',ha='center',fontsize=9.5)
    fig.text(.5,.025,'PLANNING ONLY: native PCB/CAD unchanged. Copper-carrier revision, screw heads, DC/GND/shields and native DRC remain pending.',ha='center',fontsize=9.4,color=RED)
    fig.savefig(OUT/'Revised_M2p5_Proposed_RF_Connections.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,8),dpi=190)
    draw(ax,rows,pads,mounts,snapshot,True,ylim=(36.8,40.1));ax.set_xlim(5.7,8.35)
    overlay(ax,rows,paths,pads)
    e=np.array(arc['start_mm']);u=np.array(arc['start_tangent'])
    ax.plot([e[0],e[0]+u[0]*.65],[e[1],e[1]+u[1]*.65],ls='--',color='#919b9d',lw=1,
            label='Pad-axis tangent reference (not copper)')
    ax.scatter(*e,c=COLORS[12],s=22,zorder=20)
    ax.set_title('QD pad 15: curvature starts at the pad end\nNo straight segment before the first bend',fontsize=13)
    ax.legend(fontsize=8,loc='lower right')
    fig.text(.5,.032,'R = 1.50 mm is an illustrative planning radius; existing pad position and angle are preserved.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.055,1,.98));fig.savefig(OUT/'QD15_Immediate_Curved_Departure.png');plt.close(fig)


def main():
    protected=[ROOT/'QSTL_QD4_2SET_38PAD'/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc',
        'QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv','full_copper_candidate.json')]
    protected += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    old,rows,pads,om,mounts,snapshot=geometry();lines,arc=routes(rows)
    route_check,_=check(rows,lines,pads);mech=mechanics(rows,mounts)
    result=dict(status='PICTURE_ONLY_REVISED_CONNECTION_PLAN',native_unchanged=True,
                native_source_hashes=hashes,routing_guide_checks=route_check,
                nominal_2D_mechanical_checks=mech,pad15_departure=arc,
                lower_M2_fixed=True,large_mount_shift_mm=-.75,
                proposed_mounts=mounts,
                paths=[dict(**r,points_mm=list(l.coords)) for r,l in zip(rows,lines)])
    print(json.dumps({k:v for k,v in result.items() if k not in ('paths','proposed_mounts','native_source_hashes')},indent=2))
    assert not route_check['centerline_crossings']
    assert not route_check['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps']
    assert all(v[0]>.2 for v in mech.values())
    render(rows,lines,pads,mounts,snapshot,arc)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protected}
    (OUT/'revised_mount_rf_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'Revised_SMP_QD_Mapping.csv').open('w',newline='') as f:
        fields=['position','smp','qd_pad','capacitor','resistor','rf_net','dc_net','zif_pin','x_mm','y_mm']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({**{k:r[k] for k in fields if k in r},'x_mm':r['start'][0],'y_mm':r['start'][1]})
    print(str(OUT/'Revised_M2p5_Proposed_RF_Connections.png'))


if __name__=='__main__':main()
