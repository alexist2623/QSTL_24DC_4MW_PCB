"""Smooth RF topology guides on fixed paired SMP coordinates; native read-only."""
from itertools import combinations, product
from pathlib import Path
import csv
import json
import math

import numpy as np
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from width23_outline_plan import ROOT, SOURCES, sha, plt
from rounded_smp_width32p6_plan import paint as base_paint
from latest_connection_plan import pg

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Paired_SMP_RF_First_Plan_20261015'
SOURCE=ROOT/'QSTL_QD4_2SET_38PAD/Paired_Straight_SMP_Plan_20261015/paired_straight_smp_audit.json'
TRACE_WIDTH=.11
EDGE_GAP=.15
MIN_BEND_RADIUS=1.0
COLORS=['#b66925','#23578b','#a13057','#4c7b27','#744bae','#147c80','#a24f2c','#5264a6',
        '#915523','#4b7c37','#a54883','#196a9d','#7f5625','#537e9c','#ab4b35','#316c5a']


def obstacle_sets(data,snapshot):
    template=[p for p in snapshot['pads'] if p['component']=='SMP35']
    origin=next(p for p in template if p['number']=='1')
    all_smp=[];bodies={}
    for r in data['rows']:
        sx,sy=r['start']
        bodies[r['smp']]=box(sx-2.75,sy-2.75,sx+2.75,sy+2.75)
        for p in template:
            p=dict(p,component=r['smp'],x=p['x']+sx-origin['x'],y=p['y']+sy-origin['y'])
            all_smp.append((r['smp'],p['number'],pg(p)))
    qd=[(int(p['number']),pg(p['after'])) for p in data['pads']]
    cavity=box(7.6,43.5,11.9,48.8)
    mount=unary_union([pg(p) for p in data['mounts']])
    obstacles={}
    for r in data['rows']:
        gs=[g for n,p,g in all_smp if not (n==r['smp'] and p=='1')]
        gs += [g for n,g in qd if n!=r['qd_pad']]
        gs += [g for n,g in bodies.items() if n!=r['smp']]
        gs += [cavity,mount]
        obstacles[r['smp']]=unary_union(gs)
    return obstacles,all_smp,qd


def entry_direction(r):
    row=int(r['position'][1]);left=r['position'].endswith('L')
    if row in (1,4):return np.array([0.,-1.])
    if row in (5,8):return np.array([0.,1.])
    return np.array([1. if left else -1.,0.])


def guide(r,a,b,escape=2.8,entry=None):
    e=np.array(r['end']);s=np.array(r['start']);u=np.array(r['outward'])
    v=entry_direction(r) if entry is None else np.asarray(entry,dtype=float)
    q=s+escape*v
    p1=e+a*u;p2=q+b*v
    t=np.linspace(0,1,241)[:,None]
    xy=(1-t)**3*e+3*(1-t)**2*t*p1+3*(1-t)*t*t*p2+t**3*q
    d1=3*((1-t)**2*(p1-e)+2*(1-t)*t*(p2-p1)+t*t*(q-p2))
    d2=6*((1-t)*(p2-2*p1+e)+t*(q-2*p2+p1))
    cross=np.abs(d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0])
    valid=cross>1e-10
    radius=float(np.min(np.linalg.norm(d1[valid],axis=1)**3/cross[valid]))
    xy=np.concatenate([xy,np.linspace(q,s,36)[1:]])
    line=LineString(xy)
    return dict(line=line,qd_control_mm=a,smp_control_mm=b,
                sampled_minimum_bend_radius_mm=radius,
                smp_straight_approach_mm=escape,control_points=[e.tolist(),p1.tolist(),p2.tolist(),q.tolist()],
                entry_outward=v.tolist())


def choose_routes(data,obstacles):
    all_candidates=[]
    for r in data['rows']:
        pool=[]
        for a,b in product((.5,1.,1.5,2.,3.,4.,5.,6.,8.,10.),(.5,1.,1.5,2.,3.,4.,5.,6.,8.,10.)):
            c=guide(r,a,b)
            if c['sampled_minimum_bend_radius_mm']<MIN_BEND_RADIUS:continue
            line=c['line'];gap=line.distance(obstacles[r['smp']])-TRACE_WIDTH/2
            if not line.is_simple or gap<EDGE_GAP:continue
            if not box(-6.55+.15,.15,26.05-.15,77.5-.15).covers(line.buffer(.055)):continue
            c['foreign_geometry_clearance_mm']=gap
            # Prefer simple, short fanout curves with reasonably broad controls.
            c['score']=line.length+.025*abs(a-b)+.15*(1/a+1/b)
            pool.append(c)
        pool.sort(key=lambda c:c['score'])
        if not pool:raise RuntimeError(f'No smooth candidate for {r["smp"]}')
        all_candidates.append(pool)
    # Assign the least flexible routes first, retaining exact physical channels.
    order=sorted(range(16),key=lambda i:len(all_candidates[i]))
    chosen={};visits=0
    def assign(k):
        nonlocal visits
        if k==len(order):return True
        i=order[k]
        for c in all_candidates[i]:
            visits+=1
            if visits>150000:raise RuntimeError('Candidate search limit reached')
            if any(c['line'].distance(v['line'])<TRACE_WIDTH+EDGE_GAP for v in chosen.values()):continue
            chosen[i]=c
            if assign(k+1):return True
            chosen.pop(i)
        return False
    if not assign(0):raise RuntimeError('No non-crossing route selection')
    return [chosen[i] for i in range(16)],dict(candidate_counts=[len(p) for p in all_candidates],search_visits=visits)


def audit(data,routes,obstacles):
    rows=data['rows'];paths=[c['line'] for c in routes]
    crossings=[(rows[i]['smp'],rows[j]['smp']) for i,j in combinations(range(16),2) if paths[i].intersects(paths[j])]
    pairgap=min((paths[i].distance(paths[j])-TRACE_WIDTH,rows[i]['smp'],rows[j]['smp'])
                for i,j in combinations(range(16),2))
    obgap=min((c['line'].distance(obstacles[r['smp']])-TRACE_WIDTH/2,r['smp'])
              for r,c in zip(rows,routes))
    endpoint=max(max(np.linalg.norm(np.array(c['line'].coords[0])-r['end']),
                     np.linalg.norm(np.array(c['line'].coords[-1])-r['start'])) for r,c in zip(rows,routes))
    tangent=max(abs((c['control_points'][1][0]-r['end'][0])*r['outward'][1]
                    -(c['control_points'][1][1]-r['end'][1])*r['outward'][0])
                for r,c in zip(rows,routes))
    assert not crossings and min(pairgap[0],obgap[0])>=EDGE_GAP and endpoint<1e-8 and tangent<1e-8
    return dict(guide_count=16,guide_crossings=crossings,
        nominal_RF_width_mm=TRACE_WIDTH,minimum_RF_to_RF_edge_gap_mm=pairgap,
        minimum_RF_to_foreign_geometry_edge_gap_mm=obgap,
        endpoint_error_mm=float(endpoint),QD_tangent_cross_product_error=float(tangent),
        minimum_sampled_bend_radius_mm=min(c['sampled_minimum_bend_radius_mm'] for c in routes),
        all_guides_single_continuous_bezier_plus_straight_SMP_approach=True,
        QD15_curves_directly_from_pad_end=True,RF_signal_vias=0,
        unchanged_SMP_QD_mounts_and_circuit_membership=True,
        RC_placement_and_complete_bias_tee_routing_deferred=True,
        full_GND_fence_DC_mask_impedance_and_native_DRC_not_validated=True)


def draw(ax,data,snapshot,routes,zoom=False):
    base_paint(ax,data,[],snapshot,False)
    # The previous four trial R/C pairs are deliberately omitted: this pass is
    # RF topology first. Capacitor and DC-bias junction positions remain pending.
    for i,(r,c) in enumerate(zip(data['rows'],routes)):
        x,y=c['line'].xy
        ax.plot(x,y,color=COLORS[i],lw=1.2 if not zoom else 1.7,zorder=5)
        e=r['end'];ax.scatter(*e,s=6 if not zoom else 12,c=COLORS[i],zorder=7)
    ax.set_title('Proposed RF connections on fixed SMP pairs',fontsize=13,pad=14)
    if zoom:
        ax.set_xlim(4.8,14.7);ax.set_ylim(40.8,51.5)
        for r in data['rows']:
            e=np.array(r['end']);u=np.array(r['outward'])
            q=e+.42*u
            ax.text(*q,str(r['qd_pad']),ha='center',va='center',fontsize=7.5,
                    bbox=dict(fc='white',ec='none',alpha=.85,pad=.1),zorder=12)
        ax.set_title('QD pad departures — smooth tangent curves',fontsize=12,pad=12)


def main():
    OUT.mkdir(exist_ok=True)
    data=json.loads(SOURCE.read_text());snapshot=json.loads(SOURCES['snapshot'].read_text())
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protect=[SOURCE,SOURCES['snapshot']]+[native/n for n in (
        'QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv')]
    protect += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/n for n in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p):sha(p) for p in protect}
    source_coords=json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts']),sort_keys=True)
    with (native/'pin_mapping.csv').open(newline='') as f:pinmap={int(r['qd_pad']):r for r in csv.DictReader(f)}
    for r in data['rows']:
        m=pinmap[r['qd_pad']]
        assert m['smp']==r['smp'] and m['resistor']==r['resistor'] and m['capacitor']==r['capacitor']
    obstacles,_,_=obstacle_sets(data,snapshot)
    routes,search=choose_routes(data,obstacles);checks=audit(data,routes,obstacles)
    fig=plt.figure(figsize=(14,13),dpi=220)
    gs=fig.add_gridspec(2,2,width_ratios=(1,1.2),height_ratios=(1,.8),
                       left=.05,right=.97,top=.865,bottom=.16,wspace=.23,hspace=.16)
    full=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);tableax=fig.add_subplot(gs[1,1])
    draw(full,data,snapshot,routes);draw(detail,data,snapshot,routes,True)
    tableax.axis('off')
    cells=[]
    for k in range(8):
        a,b=data['rows'][2*k:2*k+2]
        cells.append([f'Pair row {k+1}',f'{a["smp"]} -> QD {a["qd_pad"]}',f'{b["smp"]} -> QD {b["qd_pad"]}'])
    table=tableax.table(cellText=cells,colLabels=['Position','Left circuit','Right circuit'],cellLoc='center',bbox=[0,.14,1,.84])
    table.auto_set_font_size(False);table.set_fontsize(9.5)
    for (i,j),cell in table.get_celld().items():
        cell.set_edgecolor('#cad6d9');cell.set_facecolor('#dce9e8' if i==0 else '#f4f7f6')
    tableax.text(.5,.02,'Circuit membership and all pad/connector coordinates preserved',ha='center',fontsize=9)
    fig.suptitle('RF first: sixteen smooth connection guides',fontsize=20,y=.975)
    fig.text(.5,.94,'Fixed straight-pair SMP placement | 32.60 x 77.50 mm | Bottom-side topology, no RF signal vias',ha='center',fontsize=11)
    fig.text(.5,.911,'R0603/C1206 placement is deferred; these guides are not completed bias-tee copper.',ha='center',fontsize=10.5)
    fig.text(.5,.098,f'0 crossings | At 0.11 mm guide width: min RF-RF edge gap {checks["minimum_RF_to_RF_edge_gap_mm"][0]:.3f} mm; '
             f'min foreign-geometry gap {checks["minimum_RF_to_foreign_geometry_edge_gap_mm"][0]:.3f} mm.',ha='center',fontsize=10)
    fig.text(.5,.069,'Curves leave QD pads tangentially and join straight cardinal approaches into SMP signal centres.',ha='center',fontsize=10)
    fig.text(.5,.039,'PLAN ONLY: native PCB/CAD unchanged. Final R/C, DC, GND shielding, mask, impedance and Altium DRC remain pending.',ha='center',fontsize=9.5,color='#9b5038')
    fig.savefig(OUT/'Paired_SMP_Proposed_RF_Connections.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,13),dpi=230)
    draw(ax,data,snapshot,routes)
    ax.set_title('RF connections on the paired SMP plan\nR/C placement deferred',fontsize=15,pad=16)
    fig.text(.5,.05,'16 continuous guides | Smooth QD departures | No connector or pad movement',ha='center',fontsize=10)
    fig.text(.5,.025,'Topology only; native PCB unchanged, not a manufacturing release',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.08,1,.98));fig.savefig(OUT/'Paired_SMP_RF_Enlarged.png');plt.close(fig)
    assert source_coords==json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts']),sort_keys=True)
    assert hashes=={str(p):sha(p) for p in protect}
    records=[]
    for r,c in zip(data['rows'],routes):
        records.append(dict(smp=r['smp'],qd_pad=r['qd_pad'],length_mm=c['line'].length,
                            **{k:v for k,v in c.items() if k not in ('line','score')},
                            points_mm=list(c['line'].coords)))
    result=dict(status='RF_GUIDES_ONLY_RC_DEFERRED_NOT_APPLIED',checks=checks,search=search,
        rows=data['rows'],pads=data['pads'],mounts=data['mounts'],qd_centre_mm=data['qd_centre_mm'],
        routes=records,source_hashes=hashes,native_and_reference_files_unchanged=True,
        saved_mapping_correspondence_checked=True,known_carrier_mounting_conflicts_remain=True)
    (OUT/'rf_first_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'README.md').write_text(
        '# RF-first topology on the straight SMP pairs\n\n'
        'The user deferred R/C placement and requested RF first. All sixteen SMP centres, '
        'QD pad geometry, mounting axes, board outline and circuit assignments are retained '
        'from the paired-straight proposal. Existing R/C designators remain associated with '
        'their circuits, but the four old trial pairs are omitted in this RF-first picture.\n\n'
        'Each guide is one cubic Bezier leaving the QD pad tangentially, followed by a '
        '2.80 mm cardinal straight approach into its SMP signal pad. QD15 curves immediately '
        'from its outer end. No RF signal via or layer change is introduced. The dashed '
        'pair-alignment guides from the earlier picture are omitted.\n\n'
        '[Overview and mapping](Paired_SMP_Proposed_RF_Connections.png) | '
        '[Enlarged routing picture](Paired_SMP_RF_Enlarged.png) | [Audit](rf_first_audit.json)\n\n'
        'Sampled 0.11 mm guide geometry is checked against other guides, all foreign QD/SMP '
        'pads, other SMP body envelopes, mounting lands, cavity and board edges. This '
        'is not completed electrical copper: series capacitors and resistor DC-bias junctions '
        'will be placed in a subsequent stage. DC, GND fences/reference geometry, masks, '
        'impedance and Altium DRC are not verified by this illustration. Native and reference '
        'files remain unchanged, and known carrier mounting conflicts remain open.\n',encoding='utf-8')
    print(json.dumps(dict(checks=checks,search=search,native_files_unchanged=True),indent=2))


if __name__=='__main__':main()
