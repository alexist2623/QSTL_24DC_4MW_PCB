"""Preview two SMP arcs with an open longitudinal centre; no native edits."""
from copy import deepcopy
from itertools import combinations
import csv
import json
import math

import numpy as np
from shapely.geometry import box
from matplotlib.patches import Rectangle

from width23_outline_plan import ROOT, SOURCES, PLAN, RC, ROD, sha, plt, line_dimension
from width32p6_outline_plan import preview
from latest_connection_plan import pg
from central_four_rc_placement import occupied

OUT = ROOT/'QSTL_QD4_2SET_38PAD/Rounded_SMP_Plan_20261015'
WIDTH, LENGTH, CX, CY = 32.6, 77.5, 9.75, 46.15
RX = 12.8
RY = 23.3/math.sqrt(1-(7/RX)**2)


def make_plan(original):
    proposed = deepcopy(original)
    # Previous RF guides are invalid after moving endpoints and are explicitly
    # omitted. Electrical membership and each row's Y coordinate are preserved.
    proposed.pop('paths', None)
    proposed.pop('checks', None)
    for r in proposed['rows']:
        old_x, y = r['start']
        side = -1 if r['position'].endswith('L') else 1
        offset = RX*math.sqrt(1-((y-CY)/RY)**2)
        r['old_start'] = [old_x, y]
        r['start'] = [CX+side*offset, y]
    proposed['status'] = 'ROUNDED_SMP_PLACEMENT_ONLY_NOT_APPLIED'
    return proposed


def inspect(original, proposed, groups, snapshot):
    bodies = [(r['smp'], box(r['start'][0]-2.75,r['start'][1]-2.75,
                            r['start'][0]+2.75,r['start'][1]+2.75)) for r in proposed['rows']]
    outline = box(CX-WIDTH/2, 0, CX+WIDTH/2, LENGTH)
    pairs = sorted((a.distance(b),an,bn) for (an,a),(bn,b) in combinations(bodies,2))
    mounts = sorted((b.distance(pg(m)),name,str(m.get('concept_group','mount')))
                    for name,b in bodies for m in proposed['mounts'])
    qd = sorted((b.distance(pg(p['after'])),name,p['number'])
                for name,b in bodies for p in proposed['pads'])
    rc = sorted((b.distance(occupied(c)),name,c['ref']) for name,b in bodies
                for g in groups for c in (g['capacitor_component'],g['resistor_component']))
    zif = min(b.distance(pg(p)) for _,b in bodies for p in snapshot['pads'] if p['component']=='J1')
    edge = min(b.distance(outline.boundary) for _,b in bodies)
    assert all(outline.covers(b) for _,b in bodies)
    assert min(pairs[0][0],mounts[0][0],qd[0][0],rc[0][0],zif,edge) >= .249999
    bypos = {r['position']:r for r in proposed['rows']}
    mirror_error = max(abs(bypos[f'P{i}L']['start'][0]+bypos[f'P{i}R']['start'][0]-2*CX)
                       for i in range(1,9))
    centre_strip = box(5.5,0,14.,LENGTH)
    strip_intersections = [n for n,b in bodies if b.intersection(centre_strip).area > 1e-8]
    assert not strip_intersections and mirror_error < 1e-10
    assert proposed['pads'] == original['pads'] and proposed['mounts'] == original['mounts']
    for a,b in zip(original['rows'],proposed['rows']):
        assert a['start'][1] == b['start'][1]
        assert {k:v for k,v in a.items() if k!='start'} == {
            k:v for k,v in b.items() if k not in ('start','old_start')}
    return dict(
        nominal_5p5mm_SMP_envelope_checks_passed=True,
        minimum_SMP_box_to_box_gap_mm=pairs[0],
        minimum_SMP_box_to_mount_land_gap_mm=mounts[0],
        minimum_SMP_box_to_QD_pad_gap_mm=qd[0],
        minimum_SMP_box_to_trial_RC_gap_mm=rc[0],
        minimum_SMP_box_to_ZIF_pad_gap_mm=zif,
        minimum_SMP_box_to_board_edge_gap_mm=edge,
        SMP_free_longitudinal_strip_x_mm=[5.5,14.],
        SMP_free_longitudinal_strip_width_mm=8.5,
        QD_side_empty_band_y_mm=[42.85,49.45],
        QD_side_empty_band_height_mm=6.6,
        left_right_mirror_error_mm=mirror_error,
        all_SMP_Y_coordinates_preserved=True,
        QD_ZIF_mount_RC_positions_preserved=True,
        circuit_membership_preserved=True,
        scope='Nominal 2D placement only; excludes screw heads, plugs, RF/DC routing and CAD interference.')


def paint(ax, data, groups, snapshot, proposed, zoom=False):
    preview(ax,data,groups,snapshot,WIDTH)
    # Remove outline-comparison marks and overlays: moved SMPs now occupy the
    # added board areas and should not be tinted by the previous width bands.
    for patch in list(ax.patches):
        if isinstance(patch,Rectangle) and abs(patch.get_height()-LENGTH)<1e-8 and abs(patch.get_width()-6.55)<1e-8:
            patch.remove()
    for line in list(ax.lines):
        xd = list(line.get_xdata())
        if len(xd)==2 and xd[0]==xd[1] and any(abs(xd[0]-v)<1e-8 for v in (-1.75,0,19.5,21.25)):
            line.remove()
    for t in list(ax.texts):
        if t.get_text()=='+6.55 mm':t.remove()
    if proposed:
        for y0,y1 in ((22.85,40.1),(52.2,69.45)):
            yy=np.linspace(y0,y1,180)
            xx=RX*np.sqrt(1-((yy-CY)/RY)**2)
            for sign in (-1,1):
                ax.plot(CX+sign*xx,yy,color='#647fa6',ls='--',lw=1.2,zorder=2.5)
        for x in (5.5,14):
            ax.plot([x,x],[21,73.1],color='#198b76',ls=(0,(3,4)),lw=.85,zorder=2)
        line_dimension(ax,5.5,14,73.0,'8.50 mm SMP-free',color='#197e6d',size=8.5)
        for x in (-1.7,21.2):
            ax.annotate('',xy=(x,49.45),xytext=(x,42.85),
                        arrowprops=dict(arrowstyle='<->',lw=1,color='#5570a1'))
            ax.text(x+.45,46.15,'6.60 mm',rotation=90,va='center',ha='left',
                    fontsize=8,color='#5570a1')
        ax.set_title('Proposed: two curved SMP arcs',fontsize=13,pad=14)
    else:
        ax.set_title('Previous: two straight SMP columns',fontsize=13,pad=14)
    if zoom:
        ax.set_ylim(19,74)
        ax.set_title('Rounded SMP placement — enlarged',fontsize=15,pad=16)


def main():
    OUT.mkdir(exist_ok=True)
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protect=[PLAN,RC,ROD,SOURCES['snapshot']]+[native/n for n in (
        'QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc',
        'QD4_2SET_38.PcbLib','pin_mapping.csv')]
    protect += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/n for n in (
        'Bottom_reference.step','Top_ForFridge_reference.step','Probe_H_Frame/Probe_H_Frame.step')]
    hashes={str(p):sha(p) for p in protect}
    original=json.loads(PLAN.read_text())
    groups=json.loads(RC.read_text())['groups']
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    proposed=make_plan(original)
    checks=inspect(original,proposed,groups,snapshot)

    fig, axes=plt.subplots(1,2,figsize=(13.5,13),dpi=220)
    fig.subplots_adjust(left=.07,right=.96,top=.87,bottom=.14,wspace=.18)
    paint(axes[0],original,groups,snapshot,False)
    paint(axes[1],proposed,groups,snapshot,True)
    fig.suptitle('16 RF connectors on curved arcs — centre kept open',fontsize=19,y=.975)
    fig.text(.5,.938,'32.60 x 77.50 mm | Move only SMP X coordinates | Keep row heights and all channel assignments',
             ha='center',fontsize=11)
    fig.text(.5,.910,'QD, ZIF, mounting holes and the four trial central R/C pairs retain their previous positions.',
             ha='center',fontsize=10.5)
    fig.text(.5,.100,'Dashed blue arcs are placement guides, not RF copper. Green lines bound the longitudinal SMP-free strip.',
             ha='center',fontsize=10)
    fig.text(.5,.071,f'Nominal 5.5 mm SMP boxes: minimum mutual gap {checks["minimum_SMP_box_to_box_gap_mm"][0]:.2f} mm; '
             f'minimum board-edge gap {checks["minimum_SMP_box_to_board_edge_gap_mm"]:.2f} mm. Rod side clearance: 3.20 mm.',
             ha='center',fontsize=10)
    fig.text(.5,.039,'PLAN ONLY: no native PCB/CAD changes. Full R/C routing, plugs, fasteners and carrier fit remain unverified.',
             ha='center',fontsize=9.7,color='#9b5038')
    fig.savefig(OUT/'Rounded_SMP_Comparison.png');plt.close(fig)

    fig,ax=plt.subplots(figsize=(9,13),dpi=220)
    paint(ax,proposed,groups,snapshot,True)
    ax.set_title('32.60 mm PCB: rounded SMP placement\nLongitudinal centre kept free of SMP bodies',fontsize=15,pad=16)
    fig.text(.5,.055,'16 SMPs | Existing Y positions and electrical mapping retained',ha='center',fontsize=10)
    fig.text(.5,.032,'Placement guides only; native PCB/CAD unchanged',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.08,1,.985))
    fig.savefig(OUT/'Rounded_SMP_Plan.png');plt.close(fig)

    assert hashes=={str(p):sha(p) for p in protect}
    result=dict(status=proposed['status'],board_mm=[WIDTH,LENGTH],
                ellipse_centre_mm=[CX,CY],ellipse_semiaxes_mm=[RX,RY],
                description='Two side arcs with no SMP at either longitudinal-axis apex.',
                checks=checks,rows=proposed['rows'],pads=proposed['pads'],
                mounts=proposed['mounts'],retained_trial_RC_groups=groups,
                source_hashes=hashes,native_and_reference_files_unchanged=True,
                known_carrier_mounting_conflicts_remain=True,
                old_RF_guides_invalidated=True,RF_routes_generated=False)
    (OUT/'rounded_smp_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'SMP_placement_plan.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['SMP','QD pad','Old X mm','New X mm','Retained Y mm','Delta X mm'])
        for r in proposed['rows']:
            w.writerow([r['smp'],r['qd_pad'],r['old_start'][0],r['start'][0],r['start'][1],r['start'][0]-r['old_start'][0]])
    (OUT/'README.md').write_text(
        '# Rounded SMP placement proposal\n\n'
        'On the retained 32.60 x 77.50 mm proposal, move the sixteen SMP connectors '
        'onto two symmetric elliptical side arcs. Keep every existing SMP Y coordinate, '
        'QD/ZIF/mount position, circuit assignment and the four trial central R/C pairs. '
        'The ellipse is a planning choice, not a required manufacturing dimension.\n\n'
        'Retain an 8.50 mm longitudinal strip without SMP bodies and a 6.60 mm '
        'SMP-free lateral band around the QD. The previously fixed corner SMPs also '
        'retain X; the middle connectors move outward.\n\n'
        '[Comparison](Rounded_SMP_Comparison.png) | [Full plan](Rounded_SMP_Plan.png) | '
        '[Coordinates](SMP_placement_plan.csv) | [Audit](rounded_smp_audit.json)\n\n'
        'The audit checks nominal 5.50 mm square body envelopes against one another, '
        'board edges, existing mount lands, QD pads, ZIF pads and the eight shown R/C bodies/pads. '
        'It does not validate actual plugs or screw heads. Old RF guides are invalid after '
        'endpoint movement and are not reused or shown; no final RF/DC routing or DRC is claimed. '
        'The other twelve R/C pairs remain outside this placement study.\n\n'
        'Native PCB/schematic/library/mapping and reference CAD hashes are unchanged. '
        'The known copper-carrier mounting conflicts remain unresolved.\n',encoding='utf-8')
    print(json.dumps(dict(ellipse_semiaxes_mm=[RX,RY],checks=checks,
                         native_files_unchanged=True),indent=2))


if __name__=='__main__':main()
