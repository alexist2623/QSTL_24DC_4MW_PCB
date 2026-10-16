"""Change four SMP entries to horizontal while preserving the other RF guides."""
from itertools import product
import json

import numpy as np
from shapely.geometry import LineString, box

import paired_smp_rf_first_plan as rf
from width23_outline_plan import ROOT, SOURCES, sha, plt

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Four_End_SMP_Side_Entry_20261015'
SOURCE=ROOT/'QSTL_QD4_2SET_38PAD/Paired_SMP_RF_First_Plan_20261015/rf_first_audit.json'
ENTRIES={'SMP34':(1.,0.),'SMP32':(-1.,0.),'SMP15':(1.,0.),'SMP13':(-1.,0.)}


def load_routes(data):
    byname={c['smp']:c for c in data['routes']}
    return [dict(**{k:v for k,v in byname[r['smp']].items() if k!='points_mm'},
                 line=LineString(byname[r['smp']]['points_mm'])) for r in data['rows']]


def select(data,old,obstacles):
    changed=[i for i,r in enumerate(data['rows']) if r['smp'] in ENTRIES]
    fixed=[i for i in range(16) if i not in changed]
    pools={}
    for i in changed:
        r=data['rows'][i];pool=[]
        for a,b in product((.5,1.,1.5,2.,3.,4.,5.,6.,8.,10.,12.),(.5,1.,1.5,2.,3.,4.,5.,6.,8.)):
            c=rf.guide(r,a,b,entry=ENTRIES[r['smp']])
            l=c['line'];gap=l.distance(obstacles[r['smp']])-rf.TRACE_WIDTH/2
            if not l.is_simple or c['sampled_minimum_bend_radius_mm']<rf.MIN_BEND_RADIUS:continue
            if gap<rf.EDGE_GAP:continue
            if not box(-6.4,.15,25.9,77.35).covers(l.buffer(.055)):continue
            if any(l.distance(old[j]['line'])<rf.TRACE_WIDTH+rf.EDGE_GAP for j in fixed):continue
            c['foreign_geometry_clearance_mm']=gap
            c['score']=l.length+.025*abs(a-b)+.15*(1/a+1/b)
            pool.append(c)
        pool.sort(key=lambda c:c['score'])
        assert pool,f'No side-entry route for {r["smp"]}'
        pools[i]=pool
    order=sorted(changed,key=lambda i:len(pools[i]));chosen={};visits=0
    def assign(k):
        nonlocal visits
        if k==len(order):return True
        i=order[k]
        for c in pools[i]:
            visits+=1
            if any(c['line'].distance(v['line'])<rf.TRACE_WIDTH+rf.EDGE_GAP for v in chosen.values()):continue
            chosen[i]=c
            if assign(k+1):return True
            chosen.pop(i)
        return False
    assert assign(0),'Four new side entries cannot coexist'
    result=list(old)
    for i in changed:result[i]=chosen[i]
    for i in fixed:assert list(result[i]['line'].coords)==list(old[i]['line'].coords)
    for i in changed:
        last=np.array(result[i]['line'].coords[-1]);prev=np.array(result[i]['line'].coords[-2])
        assert abs(last[1]-prev[1])<1e-12 and abs(last[0]-prev[0])>0
        assert np.dot(last-prev,ENTRIES[data['rows'][i]['smp']])<0
    return result,dict(candidate_counts={data['rows'][i]['smp']:len(pools[i]) for i in changed},search_visits=visits)


def draw(ax,data,snapshot,routes,old,section=None):
    rf.draw(ax,data,snapshot,routes)
    for i,r in enumerate(data['rows']):
        if r['smp'] not in ENTRIES:continue
        if section=='upper' and r['start'][1]<46.15:continue
        if section=='lower' and r['start'][1]>46.15:continue
        if section:
            x,y=old[i]['line'].xy
            ax.plot(x,y,ls='--',color='#a1a8ad',lw=1.,zorder=4)
        s=np.array(r['start']);v=np.array(ENTRIES[r['smp']])
        ax.annotate('',xy=s+.35*v,xytext=s+2.6*v,
                    arrowprops=dict(arrowstyle='->',lw=1.5,color=rf.COLORS[i]),zorder=14)
    if section:
        for label in list(ax.texts):
            if label.get_text() in ('32.60 mm', 'Length: 77.50 mm'):
                label.remove()
        ax.set_xlim(-6.55,26.05)
        ax.set_ylim((60,73.5) if section=='upper' else (19,32.5))
        ax.set_title('Upper ends: SMP34 / SMP32' if section=='upper' else 'Lower ends: SMP15 / SMP13',fontsize=12,pad=12)
    else:
        ax.set_title('Four end SMPs: horizontal entry from the centre',fontsize=13,pad=14)


def main():
    OUT.mkdir(exist_ok=True)
    data=json.loads(SOURCE.read_text());snapshot=json.loads(SOURCES['snapshot'].read_text())
    protect=[SOURCE,SOURCES['snapshot']]
    protect += [ROOT/'QSTL_QD4_2SET_38PAD'/n for n in (
        'QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv')]
    protect += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/n for n in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p):sha(p) for p in protect}
    geometry_before=json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts']),sort_keys=True)
    old=load_routes(data);obstacles,_,_=rf.obstacle_sets(data,snapshot)
    routes,search=select(data,old,obstacles);checks=rf.audit(data,routes,obstacles)
    changes=[]
    for i,r in enumerate(data['rows']):
        if r['smp'] not in ENTRIES:continue
        changes.append(dict(smp=r['smp'],qd_pad=r['qd_pad'],entry_from='right' if ENTRIES[r['smp']][0]>0 else 'left',
            old_length_mm=old[i]['line'].length,new_length_mm=routes[i]['line'].length,
            length_change_mm=routes[i]['line'].length-old[i]['line'].length))
    fig=plt.figure(figsize=(14,13),dpi=220)
    gs=fig.add_gridspec(2,2,width_ratios=(1,1.2),height_ratios=(1,1),
                       left=.05,right=.97,top=.865,bottom=.16,wspace=.23,hspace=.16)
    full=fig.add_subplot(gs[:,0]);upper=fig.add_subplot(gs[0,1]);lower=fig.add_subplot(gs[1,1])
    draw(full,data,snapshot,routes,old)
    draw(upper,data,snapshot,routes,old,'upper');draw(lower,data,snapshot,routes,old,'lower')
    fig.suptitle('SMP34 / SMP32 / SMP15 / SMP13: side entry',fontsize=20,y=.975)
    fig.text(.5,.938,'Left connectors enter from the right; right connectors enter from the left.',ha='center',fontsize=11)
    fig.text(.5,.908,'Only these four guides change. All positions, channel mappings and the other twelve paths are preserved.',ha='center',fontsize=10.5)
    fig.text(.5,.101,'Detail views: coloured curves = revised horizontal entry; grey dashed curves = previous vertical entry.',ha='center',fontsize=10)
    fig.text(.5,.072,f'0 crossings | 0.11 mm projected RF width | min RF-RF edge gap {checks["minimum_RF_to_RF_edge_gap_mm"][0]:.3f} mm | '
             f'min foreign-geometry gap {checks["minimum_RF_to_foreign_geometry_edge_gap_mm"][0]:.3f} mm',ha='center',fontsize=10)
    fig.text(.5,.039,'PLAN ONLY: R/C placement deferred, no RF signal vias, native PCB/CAD unchanged; full routing and DRC remain pending.',ha='center',fontsize=9.6,color='#9b5038')
    fig.savefig(OUT/'Four_End_SMP_Side_Entry_Review.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,13),dpi=230)
    draw(ax,data,snapshot,routes,old)
    ax.set_title('RF plan: four end SMPs enter from the side\nSMP34 / 32 / 15 / 13',fontsize=15,pad=16)
    fig.text(.5,.050,'Other twelve RF paths and all positions retained | R/C placement deferred',ha='center',fontsize=10)
    fig.text(.5,.026,'Connection guides only; native PCB unchanged',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.08,1,.985));fig.savefig(OUT/'RF_Side_Entry_Enlarged.png');plt.close(fig)
    assert geometry_before==json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts']),sort_keys=True)
    assert hashes=={str(p):sha(p) for p in protect}
    records=[]
    for r,c in zip(data['rows'],routes):
        d={k:v for k,v in c.items() if k not in ('line','score')}
        d.update(smp=r['smp'],qd_pad=r['qd_pad'],length_mm=c['line'].length,points_mm=list(c['line'].coords))
        records.append(d)
    result=dict(status='FOUR_END_SMP_HORIZONTAL_ENTRY_PLAN_NOT_APPLIED',changes=changes,
        checks=checks,search=search,rows=data['rows'],pads=data['pads'],mounts=data['mounts'],
        qd_centre_mm=data['qd_centre_mm'],routes=records,other_twelve_guides_exactly_unchanged=True,
        source_hashes=hashes,native_and_reference_files_unchanged=True,
        known_carrier_mounting_conflicts_remain=True)
    (OUT/'side_entry_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUT/'README.md').write_text(
        '# Four end SMPs: horizontal entry\n\n'
        'SMP34 (QD2) and SMP15 (QD16) now enter from the right; SMP32 (QD35) and SMP13 '
        '(QD21) enter from the left. These directions point from the board-centre side '
        'toward each signal pad. Only four conceptual guides change. Other twelve sampled '
        'paths, all component/pad/mount coordinates and electrical membership are retained.\n\n'
        '[Review with before/after details](Four_End_SMP_Side_Entry_Review.png) | '
        '[Enlarged plan](RF_Side_Entry_Enlarged.png) | [Audit](side_entry_audit.json)\n\n'
        'Each new path retains a tangent cubic QD departure and finishes with a 2.80 mm '
        'horizontal approach. All sixteen guides are checked together at 0.11 mm width '
        'against foreign pad copper, other SMP envelopes, mounting lands, cavity and board '
        'edges. A sampled minimum 1.00 mm bend radius is enforced for the proposed curves. '
        'This does not establish electrical or manufacturing superiority over the previous entry.\n\n'
        'R/C placement is deferred. No native PCB/CAD changes or RF signal vias are introduced. '
        'Final bias tees, DC/GND/fences/masks, impedance, Altium DRC, plugs and fasteners '
        'remain unvalidated; existing carrier mounting conflicts remain open.\n',encoding='utf-8')
    print(json.dumps(dict(changes=changes,checks=checks,search=search,
                         other_twelve_guides_exactly_unchanged=True,native_files_unchanged=True),indent=2))


if __name__=='__main__':main()
