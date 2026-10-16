"""Preview eight straight SMP pairs, without changing native design files."""
from copy import deepcopy
from itertools import combinations
import csv
import json
import math

from shapely.geometry import box
from width23_outline_plan import ROOT, SOURCES, PLAN, RC, ROD, sha, plt, line_dimension
from rounded_smp_width32p6_plan import paint as previous_paint
from latest_connection_plan import pg
from central_four_rc_placement import occupied

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Paired_Straight_SMP_Plan_20261015'
PREVIOUS=ROOT/'QSTL_QD4_2SET_38PAD/Rounded_SMP_Plan_20261015/rounded_smp_audit.json'
WIDTH,LENGTH,CX,CY=32.6,77.5,9.75,46.15
LEFT_X=[2.75,-3.25,-3.25,-3.25,-3.25,-3.25,-3.25,2.75]
ROW_Y=[69.45,65.70,58.20,52.20,40.10,34.10,26.60,22.85]
PAIR_ROWS=[(1,2),(3,4),(5,6),(7,8)]
PAIR_COLORS=['#b06a34','#37699c','#37699c','#b06a34']


def build(original):
    data=deepcopy(original)
    data.pop('paths',None)
    data.pop('checks',None)
    for r in data['rows']:
        i=int(r['position'][1])-1
        x=LEFT_X[i] if r['position'].endswith('L') else 2*CX-LEFT_X[i]
        r['old_start']=r['start'][:]
        r['start']=[x,ROW_Y[i]]
    data['status']='PAIRED_STRAIGHT_SMP_PLAN_NOT_APPLIED'
    return data


def shape(r):
    x,y=r['start']
    return box(x-2.75,y-2.75,x+2.75,y+2.75)


def inspect(original,data,groups,snapshot):
    rows=data['rows'];lookup={r['position']:r for r in rows}
    bodies=[(r['smp'],shape(r)) for r in rows]
    outline=box(CX-WIDTH/2,0,CX+WIDTH/2,LENGTH)
    pair_gaps=[];group_gaps=[]
    for side in ('L','R'):
        for k,(i,j) in enumerate(PAIR_ROWS):
            a,b=lookup[f'P{i}{side}'],lookup[f'P{j}{side}']
            dx=b['start'][0]-a['start'][0];dy=b['start'][1]-a['start'][1]
            pair_gaps.append(dict(pair=f'G{k+1}{side}',members=[a['smp'],b['smp']],
                arrangement='diagonal' if k in (0,3) else 'vertical',
                body_envelope_gap_mm=shape(a).distance(shape(b)),
                centre_distance_mm=math.hypot(dx,dy),
                angle_to_horizontal_degrees=math.degrees(math.atan2(abs(dy),abs(dx)))))
        for i,j in ((2,3),(6,7)):
            a,b=lookup[f'P{i}{side}'],lookup[f'P{j}{side}']
            group_gaps.append(dict(members=[a['smp'],b['smp']],gap_mm=shape(a).distance(shape(b))))
    gaps=sorted((a.distance(b),an,bn) for (an,a),(bn,b) in combinations(bodies,2))
    mountg=sorted((b.distance(pg(m)),n,m.get('concept_group','mount'))
                  for n,b in bodies for m in data['mounts'])
    qdg=min(b.distance(pg(p['after'])) for _,b in bodies for p in data['pads'])
    rcg=min(b.distance(occupied(c)) for _,b in bodies for g in groups
            for c in (g['resistor_component'],g['capacitor_component']))
    zifg=min(b.distance(pg(p)) for _,b in bodies for p in snapshot['pads'] if p['component']=='J1')
    edge=min(b.distance(outline.boundary) for _,b in bodies)
    mirror=max(abs(lookup[f'P{i}L']['start'][0]+lookup[f'P{i}R']['start'][0]-2*CX)
               for i in range(1,9))
    axial=max(abs(ROW_Y[i]+ROW_Y[7-i]-2*CY) for i in range(8))
    strip=box(5.5,0,14.,LENGTH)
    assert len(rows)==16 and len({r['smp'] for r in rows})==16
    assert all(outline.covers(b) for _,b in bodies)
    assert not any(b.intersection(strip).area>1e-8 for _,b in bodies)
    assert all(abs(p['body_envelope_gap_mm']-.5)<1e-8 for p in pair_gaps)
    assert all(abs(p['gap_mm']-2)<1e-8 for p in group_gaps)
    assert min(gaps[0][0],mountg[0][0],qdg,rcg,zifg,edge)>.24999
    assert max(mirror,axial)<1e-10
    assert data['pads']==original['pads'] and data['mounts']==original['mounts']
    for a,b in zip(original['rows'],rows):
        assert {k:v for k,v in a.items() if k!='start'}=={
            k:v for k,v in b.items() if k not in ('start','old_start')}
    return dict(nominal_SMP_body_size_mm=[5.5,5.5],pair_groups=pair_gaps,
                between_group_gaps=group_gaps,minimum_SMP_to_SMP_box_gap_mm=gaps[0],
                minimum_SMP_box_to_mount_land_gap_mm=mountg[0],
                minimum_SMP_box_to_QD_pad_gap_mm=qdg,
                minimum_SMP_box_to_retained_RC_gap_mm=rcg,
                minimum_SMP_box_to_ZIF_pad_gap_mm=zifg,
                minimum_SMP_box_to_outline_gap_mm=edge,
                SMP_free_longitudinal_strip_x_mm=[5.5,14.],
                SMP_free_longitudinal_strip_width_mm=8.5,
                QD_side_empty_band_y_mm=[42.85,49.45],
                QD_side_empty_band_height_mm=6.6,
                left_right_symmetry_error_mm=mirror,upper_lower_symmetry_error_mm=axial,
                QD_pads_mounts_and_channel_assignments_unchanged=True,
                preserved_four_RC_pairs=True,
                scope='2D placement with unrotated nominal square SMP envelopes; not routing or assembly-fit validation.')


def vertical_dimension(ax,x,y0,y1,label):
    ax.annotate('',xy=(x,y1),xytext=(x,y0),
                arrowprops=dict(arrowstyle='<->',lw=.9,color='#49717d'))
    ax.text(x+.3,(y0+y1)/2,label,ha='left',va='center',fontsize=8,color='#49717d',
            bbox=dict(fc='white',ec='none',pad=.5,alpha=.85))


def paint(ax,data,groups,snapshot):
    previous_paint(ax,data,groups,snapshot,False)
    lookup={r['position']:r for r in data['rows']}
    for side in ('L','R'):
        for k,(i,j) in enumerate(PAIR_ROWS):
            a,b=lookup[f'P{i}{side}']['start'],lookup[f'P{j}{side}']['start']
            ax.plot([a[0],b[0]],[a[1],b[1]],color=PAIR_COLORS[k],ls=(0,(4,3)),lw=1.5,zorder=2.5)
    for x in (5.5,14):
        ax.plot([x,x],[21,73],color='#198b76',ls=(0,(3,4)),lw=.85,zorder=2)
    line_dimension(ax,5.5,14,73.,'8.50 mm SMP-free',color='#197e6d',size=8.5)
    # The nearest adjacent pairs have 2 mm clear body-envelope separation.
    vertical_dimension(ax,1.2,60.95,62.95,'2.00 mm')
    vertical_dimension(ax,1.2,29.35,31.35,'2.00 mm')
    vertical_dimension(ax,-1.3,42.85,49.45,'6.60 mm')
    ax.set_title('Proposed: straight groups of two',fontsize=13,pad=14)


def main():
    OUT.mkdir(exist_ok=True)
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protect=[PLAN,RC,ROD,PREVIOUS,SOURCES['snapshot']]+[native/n for n in (
        'QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv')]
    protect += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/n for n in (
        'Bottom_reference.step','Top_ForFridge_reference.step','Probe_H_Frame/Probe_H_Frame.step')]
    hashes={str(p):sha(p) for p in protect}
    original=json.loads(PLAN.read_text());previous=json.loads(PREVIOUS.read_text())
    previous['qd_centre_mm']=[CX,CY]
    groups=json.loads(RC.read_text())['groups'];snapshot=json.loads(SOURCES['snapshot'].read_text())
    data=build(original);checks=inspect(original,data,groups,snapshot)
    fig,axes=plt.subplots(1,2,figsize=(13.5,13),dpi=220)
    fig.subplots_adjust(left=.07,right=.96,top=.87,bottom=.14,wspace=.18)
    previous_paint(axes[0],previous,groups,snapshot,True)
    axes[0].set_title('Previous: continuous curved arrangement',fontsize=13,pad=14)
    paint(axes[1],data,groups,snapshot)
    fig.suptitle('16 SMPs in eight straight pairs',fontsize=20,y=.976)
    fig.text(.5,.938,'Diagonal pairs at the upper/lower ends; vertical pairs beside the central region',ha='center',fontsize=11)
    fig.text(.5,.909,'32.60 x 77.50 mm | QD, ZIF, mounts, channel mapping and four trial central R/C pairs retained',ha='center',fontsize=10.5)
    fig.text(.5,.100,'Illustrative body-envelope gaps: 0.50 mm within each pair; 2.00 mm between adjacent pairs.',ha='center',fontsize=10.5)
    fig.text(.5,.071,'Dashed straight segments mark pair alignment, not RF copper. Connector footprints keep their original orientation.',ha='center',fontsize=10)
    fig.text(.5,.039,'PLAN ONLY: native PCB/CAD unchanged. Plugs, screw heads, complete routing and carrier fit are not validated.',ha='center',fontsize=9.8,color='#9b5038')
    fig.savefig(OUT/'Paired_Straight_SMP_Comparison.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,13),dpi=220)
    paint(ax,data,groups,snapshot)
    ax.set_title('32.60 mm PCB: straight SMP pairs\nEight groups of two; longitudinal centre kept open',fontsize=15,pad=16)
    fig.text(.5,.063,'Body-envelope gaps: within pair 0.50 mm | between adjacent pairs 2.00 mm',ha='center',fontsize=10)
    fig.text(.5,.039,'End pairs: diagonal | Middle pairs: vertical | QD-side empty band: 6.60 mm',ha='center',fontsize=10)
    fig.text(.5,.018,'Placement plan only; native PCB/CAD unchanged',ha='center',fontsize=9.5)
    fig.tight_layout(rect=(0,.09,1,.985));fig.savefig(OUT/'Paired_Straight_SMP_Plan.png');plt.close(fig)
    assert hashes=={str(p):sha(p) for p in protect}
    audit=dict(status=data['status'],board_mm=[WIDTH,LENGTH],qd_centre_mm=[CX,CY],
        rows=data['rows'],pads=data['pads'],mounts=data['mounts'],retained_trial_RC_groups=groups,
        checks=checks,source_hashes=hashes,native_and_reference_files_unchanged=True,
        old_RF_guides_invalidated=True,RF_routes_generated=False,
        known_carrier_mounting_conflicts_remain=True,
        gap_values_are_illustrative=True,footprint_rotations_unchanged=True)
    (OUT/'paired_straight_smp_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    prior={r['smp']:r for r in previous['rows']}
    with (OUT/'SMP_placement_plan.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['SMP','QD pad','Pair','Previous X','Previous Y','Proposed X','Proposed Y'])
        for r in data['rows']:
            group=(int(r['position'][1])+1)//2
            w.writerow([r['smp'],r['qd_pad'],f'G{group}{r["position"][-1]}',
                        *prior[r['smp']]['start'],*r['start']])
    (OUT/'README.md').write_text(
        '# Straight two-SMP groups\n\n'
        'Follow the user-marked grouping: each side has four pairs. End pairs are diagonal; '
        'the two middle pairs are vertical. The plan keeps the 32.60 x 77.50 mm outline, '
        'QD and its pads, ZIF, mounting holes, channel assignments and four trial central R/C pairs.\n\n'
        'Nominal unrotated 5.50 mm square SMP envelopes have 0.50 mm clearance within each '
        'pair and 2.00 mm between an end pair and its adjacent middle pair. These are '
        'assistant-selected trial distances. The 6.60 mm QD-side band and 8.50 mm '
        'longitudinal SMP-free strip are retained. End-pair centre spacing is about '
        '7.08 mm at 32.0 degrees to horizontal; vertical-pair centre spacing is 6.00 mm. '
        'The footprint orientations themselves are unchanged.\n\n'
        '[Plan](Paired_Straight_SMP_Plan.png) | [Comparison](Paired_Straight_SMP_Comparison.png) | '
        '[Coordinates](SMP_placement_plan.csv) | [Audit](paired_straight_smp_audit.json)\n\n'
        'Saved native and reference files are unchanged. This is a placement picture, '
        'not full routing or an Altium DRC result. Other twelve R/C pairs, mating plugs '
        'and screw heads are outside the check. Known copper-carrier mounting conflicts '
        'remain unresolved.\n',encoding='utf-8')
    print(json.dumps(dict(checks=checks,native_files_unchanged=True),indent=2))


if __name__=='__main__':main()
