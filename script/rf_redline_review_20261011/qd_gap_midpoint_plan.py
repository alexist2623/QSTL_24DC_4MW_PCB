"""Centre the proposed QD on the line between the two central SMP gap midpoints."""
import json
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from fixed_mount_rf_plan import geometry, routes, overlay
from outline_mount_concept import ROOT, OUT, draw, sha, RED
from latest_connection_plan import check

CYAN='#087d91'


def midpoint_geometry(rows):
    gaps=[]
    for side in ('L','R'):
        upper=min((r for r in rows if r['position'].endswith(side) and int(r['position'][1])<=4),key=lambda r:r['start'][1])
        lower=max((r for r in rows if r['position'].endswith(side) and int(r['position'][1])>=5),key=lambda r:r['start'][1])
        assert abs(upper['start'][0]-lower['start'][0])<1e-10
        lo=lower['start'][1]+2.75;hi=upper['start'][1]-2.75
        assert hi>lo
        gaps.append(dict(side=side,upper_smp=upper['smp'],lower_smp=lower['smp'],
            lower_edge_y_mm=lo,upper_edge_y_mm=hi,height_mm=hi-lo,
            midpoint_mm=[upper['start'][0],(lo+hi)/2]))
    return gaps,np.mean([g['midpoint_mm'] for g in gaps],axis=0)


def centre_marks(ax,gaps,centre,show_old=False):
    lo=gaps[0]['lower_edge_y_mm'];hi=gaps[0]['upper_edge_y_mm']
    for g in gaps:
        x,y=g['midpoint_mm']
        ax.add_patch(Rectangle((x-2.75,lo),5.5,hi-lo,fc='#b6e4dc',ec=CYAN,lw=.6,alpha=.27,zorder=2))
        ax.annotate('',xy=(x,hi),xytext=(x,lo),arrowprops=dict(arrowstyle='<->',color=CYAN,lw=1.3),zorder=20)
        ax.scatter(x,y,s=32,c=CYAN,zorder=23)
        ax.text(x,y+.72,f"{g['side']} gap midpoint",ha='center',fontsize=8.5,color=CYAN,zorder=23)
        ax.text(x,y-.72,f'({x:.2f}, {y:.2f})',ha='center',fontsize=8,color=CYAN,zorder=23)
    ax.plot([gaps[0]['midpoint_mm'][0],gaps[1]['midpoint_mm'][0]],
            [gaps[0]['midpoint_mm'][1],gaps[1]['midpoint_mm'][1]],ls='--',color='#ea8668',lw=1.3,zorder=22)
    ax.scatter(*centre,s=70,marker='+',linewidths=1.8,c='#ffe5a4',zorder=24)
    ax.text(centre[0],centre[1]-.7,f'Centre ({centre[0]:.2f}, {centre[1]:.2f})',
            ha='center',color='white',fontsize=8,zorder=24)
    if show_old:
        ax.scatter(9.75,42.5,s=30,marker='x',c='#858d91',zorder=24)
        ax.annotate('',xy=(9.75,centre[1]-.12),xytext=(9.75,42.5),
            arrowprops=dict(arrowstyle='->',color='#858d91',lw=1.1),zorder=23)
        ax.text(10.3,43.25,'Old centre\nY = 42.50',fontsize=8,color='#687e85',zorder=25)


def render(rows,paths,pads,mounts,snapshot,gaps,centre):
    fig=plt.figure(figsize=(13,15),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(.84,1.25),height_ratios=(1,.95),
            left=.065,right=.965,top=.91,bottom=.12,wspace=.25,hspace=.26)
    full=fig.add_subplot(gs[:,0]);measure=fig.add_subplot(gs[0,1]);detail=fig.add_subplot(gs[1,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,79),height=77.5,qd_center=centre)
    overlay(full,rows,paths,pads,False)
    full.axhline(centre[1],color=CYAN,lw=.8,ls='--')
    full.scatter(*centre,s=30,marker='+',c='white',zorder=20)
    full.set_title('Updated proposed RF connections\nQD moved upward by 3.65 mm',fontsize=12)
    full.text(9.75,75,'Upper M2 retained',ha='center',va='center',fontsize=8,color='#986b22')
    full.text(9.75,13.19,'Lower M2 FIXED',ha='center',va='center',fontsize=8,color='#235c99')
    for ax in (measure,detail):
        draw(ax,rows,pads,mounts,snapshot,True,ylim=(39.2,55.5) if ax is measure else (41.4,51.8),
             height=77.5,qd_center=centre)
    centre_marks(measure,gaps,centre,True)
    measure.set_title('QD at the midpoint of L-R\nCentral SMP-free gap: 6.60 mm on each side',fontsize=12)
    detail.set_xlim(4.7,14.8);overlay(detail,rows,paths,pads)
    detail.set_title('Translated QD pad field and RF guides\nAll 38 pads move together; pad 15 remains curved',fontsize=12)
    r15=next(r for r in rows if r['qd_pad']==15)
    detail.annotate('15: curve from pad end',xy=(r15['end'][0]-.1,r15['end'][1]-.17),
        xytext=(8.3,41.95),fontsize=8.5,color='#a93979',
        arrowprops=dict(arrowstyle='->',color='#a93979'),zorder=20)
    fig.suptitle('QD centred between the left and right SMP-free gaps',fontsize=19,y=.976)
    fig.text(.5,.947,'L = (2.75, 46.15) mm | R = (16.75, 46.15) mm | QD centre = (L + R) / 2 = (9.75, 46.15) mm',ha='center',fontsize=10.5)
    fig.text(.5,.085,'QD cavity and all bond pads translated +3.65 mm in Y; their sizes, angles and relative positions are retained.',ha='center',fontsize=10)
    fig.text(.5,.058,'SMP locations, mounting holes and trial PCB outline are unchanged. The 16 RF circuit assignments are retained.',ha='center',fontsize=10)
    fig.text(.5,.031,'CONCEPT ONLY: RF guides are not final copper. R/C placement, DC/GND/shields, carrier fit and native DRC remain pending.',ha='center',fontsize=9.5,color=RED)
    fig.savefig(OUT/'QD_Centred_in_SMP_Gap_Proposed_RF.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,9),dpi=180)
    draw(ax,rows,pads,mounts,snapshot,True,ylim=(39,55.7),height=77.5,qd_center=centre)
    centre_marks(ax,gaps,centre,True)
    ax.set_title('QD centre: (9.75, 42.50) -> (9.75, 46.15) mm\nMidpoint of the line connecting the two gap midpoints',fontsize=14)
    fig.text(.5,.035,'SMP envelope edges: Y = 42.85 and 49.45 mm. Their midpoint is Y = 46.15 mm.',ha='center',fontsize=10)
    fig.tight_layout(rect=(0,.06,1,.99));fig.savefig(OUT/'QD_Gap_Midpoint_Dimensioned.png');plt.close(fig)


def main():
    base_path=OUT/'raised_upper_M2_rf_audit.json'
    source=json.loads(base_path.read_text())
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protected=[native/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc',
        'QD4_2SET_38.PcbLib','pin_mapping.csv','full_copper_candidate.json')]
    protected += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    _,_,pads,_,_,snapshot=geometry()
    original_pads=deepcopy(pads);rows=deepcopy(source['rows']);mounts=deepcopy(source['mounts'])
    gaps,centre=midpoint_geometry(rows);delta=centre-np.array([9.75,42.5])
    for p in pads:
        p['after']['x']+=float(delta[0]);p['after']['y']+=float(delta[1])
        p['after_midpoints']=[list(np.array(q)+delta) for q in p['after_midpoints']]
    for r in rows:r['end']=list(np.array(r['end'])+delta)
    for a,b in zip(original_pads,pads):
        assert all(a['after'][k]==b['after'][k] for k in ('size_x','size_y','rotation','number','net','shape'))
        assert np.allclose([b['after']['x']-a['after']['x'],b['after']['y']-a['after']['y']],delta)
    assert [r['start'] for r in rows]==[r['start'] for r in source['rows']]
    assert mounts==source['mounts']
    paths,arc=routes(rows);checks,_=check(rows,paths,pads)
    assert not checks['centerline_crossings'],checks
    assert not checks['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps'],checks
    render(rows,paths,pads,mounts,snapshot,gaps,centre)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report=dict(status='OFFLINE_MIDPOINT_CENTRING_PROPOSAL_NOT_APPLIED',
        previous_proposal_sha256=sha(base_path),gap_geometry=gaps,
        old_qd_centre_mm=[9.75,42.5],new_qd_centre_mm=list(centre),translation_mm=list(delta),
        cavity_size_mm=[4.3,5.3],all_38_pads_rigidly_translated=True,
        pad_dimensions_angles_and_membership_preserved=True,
        SMP_mounts_outline_unchanged_from_previous_proposal=True,
        native_files_unchanged=True,source_hashes=hashes,guide_checks=checks,pad15_arc=arc,
        rows=rows,pads=pads,mounts=mounts,paths=[list(l.coords) for l in paths],
        limitations=['Picture only; no native PCB/CAD or manufacturing update.',
            'R/C placement, actual copper, DC/vias/GND/shields/masks and native DRC remain pending.',
            'Moving the cavity requires corresponding future copper-carrier/device-mount alignment changes.'])
    (OUT/'qd_gap_midpoint_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','pads','mounts','paths','source_hashes')},indent=2))


if __name__=='__main__':main()
