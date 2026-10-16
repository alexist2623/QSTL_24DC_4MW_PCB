"""Raise the upper group in an offline RF sketch; do not change native designs."""
import json
from copy import deepcopy
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from fixed_mount_rf_plan import geometry, routes, mechanics, overlay
from outline_mount_concept import ROOT, OUT, draw, sha, arrow, GREEN, RED
from latest_connection_plan import check


def main():
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protected=[native/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc',
        'QD4_2SET_38.PcbLib','pin_mapping.csv','full_copper_candidate.json')]
    protected += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    _,rows,pads,_,mounts,snapshot=geometry()
    previous=deepcopy(rows);previous_mounts=deepcopy(mounts)
    for r in rows:
        if int(r['position'][1])<=4:r['start'][1]+=5.
    for p in mounts:
        if p['concept_group']=='upper_M2':p['y']+=5.
    paths,arc=routes(rows);checks,_=check(rows,paths,pads);mech=mechanics(rows,mounts)
    assert not checks['centerline_crossings']
    assert not checks['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps']
    assert all(v[0]>.2 for v in mech.values())
    fig=plt.figure(figsize=(13,16),dpi=180)
    gs=fig.add_gridspec(3,2,width_ratios=(.86,1.2),height_ratios=(1,.82,.7),
        left=.06,right=.96,top=.915,bottom=.14,wspace=.24,hspace=.32)
    full=fig.add_subplot(gs[:,0]);central=fig.add_subplot(gs[0,1]);lower=fig.add_subplot(gs[1,1]);scale=fig.add_subplot(gs[2,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,79),height=77.5)
    overlay(full,rows,paths,pads,False)
    full.set_title('Proposed RF connections\nPCB 19.50 x 77.50 mm (trial)',fontsize=13)
    full.text(9.75,75,'Upper M2\nY = 75.00',ha='center',va='center',fontsize=8,color='#9b6918')
    full.text(9.75,13.19,'Lower M2 FIXED\nY = 13.19',ha='center',va='center',fontsize=7.7,color='#235c99')
    full.text(9.75,17.34,'M2.5: Y = 17.34',ha='center',va='center',fontsize=7.5,color=RED)
    draw(central,rows,pads,mounts,snapshot,True,ylim=(36.6,55.6),height=77.5)
    overlay(central,rows,paths,pads)
    central.set_title('Upper SMP group raised by 5.00 mm\nAll four upper rows move together',fontsize=12)
    for x in (0.,14.):
        central.add_patch(Rectangle((x,44.45),5.5,5,fc='#f8d477',alpha=.28,ec='#c3932f',lw=.6,zorder=2))
    central.annotate('',xy=(9.75,49.45),xytext=(9.75,44.45),
        arrowprops=dict(arrowstyle='<->',color='#9b6a0e',lw=1.4),zorder=22)
    central.text(9.75,47.1,'+5.00 mm\nplacement height',ha='center',va='center',fontsize=8,
        bbox=dict(fc='white',ec='none',alpha=.9),zorder=23)
    for x in (2.75,16.75):arrow(central,[x,47.2],[x,52.2],GREEN)
    draw(lower,rows,pads,mounts,snapshot,True,ylim=(10.5,30.5),height=77.5)
    overlay(lower,rows,paths,pads,False)
    lower.set_title('Lower geometry retained from the corrected plan',fontsize=12)
    lower.text(9.75,13.19,'M2: original position',ha='center',va='center',fontsize=8,color='#235c99')
    lower.text(9.75,17.34,'Large mounts: -0.75 mm',ha='center',va='center',fontsize=8,color=RED)
    lower.text(9.75,25.3,'Lower SMP pitch: 5.75 mm',ha='center',fontsize=8,color='#285b61')
    # A scale reference, deliberately separated from the placement drawing.
    # R0603 pad sizes come from the saved board; C1206 from the accepted footprint.
    scale.set_aspect('equal');scale.set_xlim(0,10);scale.set_ylim(-.8,7)
    scale.add_patch(Rectangle((.5,-.4),4.95,7.05,fc='#e7f1ee',ec='#72988d',ls='--',lw=.8))
    for x in (1.95,3.65):scale.add_patch(Rectangle((x-.55,.5),1.1,1,fc='#bba363',ec='none'))
    scale.add_patch(Rectangle((2,.6),1.6,.8,fc='#445b64',ec='none',alpha=.85))
    for y in (2.25,5.25):scale.add_patch(Rectangle((2.75,y-.5),1.8,1.,fc='#bba363',ec='none'))
    scale.add_patch(Rectangle((2.75,2),1.8,3.5,fc='#718582',ec='none',alpha=.65))
    scale.text(2.8,1,'R0603',ha='center',va='center',fontsize=8,color='white')
    scale.text(3.65,3.75,'C1206',ha='center',va='center',fontsize=8,color='white',rotation=90)
    scale.text(5.9,5.5,'Package-size reference only',fontsize=9,fontweight='bold')
    scale.text(5.9,4.4,'Illustrative L pair:\n3.15 x 5.25 mm pad envelope',fontsize=9,va='top')
    scale.text(5.9,2.7,'With 0.90 mm group margin:\n4.95 x 7.05 mm',fontsize=9,va='top')
    scale.text(5.9,1.0,'Not a placed or routed pair.\nFour-pair fit is not yet verified.',fontsize=9,va='top',color=RED)
    scale.set_title('Why the central R/C area needs a separate fit check',fontsize=11)
    scale.axis('off')
    fig.suptitle('Upper M2 / SMP extension + revised proposed RF connections',fontsize=18,y=.977)
    fig.text(.5,.947,'Upper M2: 70.00 -> 75.00 mm | PCB top: 72.50 -> 77.50 mm | Upper SMP group: +5.00 mm',ha='center',fontsize=10.5)
    fig.text(.5,.105,'Pad 15 leaves directly into a tangent curve. All 16 RF circuit assignments and all 38 DC assignments are preserved.',ha='center',fontsize=10)
    fig.text(.5,.078,'Added height does not change the 19.50 mm board width. The central cavity and QD pad coordinates remain fixed.',ha='center',fontsize=10)
    fig.text(.5,.052,'Lines are SMP -> C1206 -> R0603 junction -> QD connection guides; individual R/C positions are not implemented.',ha='center',fontsize=10)
    fig.text(.5,.025,'PICTURE ONLY: copper carrier needs revision; screw-head/plug fit, DC/GND/shields, masks and native DRC remain pending.',ha='center',fontsize=9.6,color=RED)
    target=OUT/'Raised_Upper_M2_Proposed_RF_Connections.png'
    fig.savefig(target);plt.close(fig)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report=dict(status='OFFLINE_PROPOSAL_NOT_APPLIED',board_mm=[19.5,77.5],
        upper_M2_y_mm=75.,upper_group_shift_vs_prior_mm=5.,lower_M2_unchanged=True,
        requested_RC_numbers='11,12,28,30: pending distinction between QD pad numbers and component designators',
        RC_four_pair_placement_verified=False,pad15_arc=arc,route_guide_checks=checks,
        nominal_2D_checks=mech,source_hashes=hashes,native_unchanged=True,
        rows=rows,mounts=mounts,paths=[list(l.coords) for l in paths])
    (OUT/'raised_upper_M2_rf_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('paths','source_hashes','rows','mounts')},indent=2))
    print(str(target))


if __name__=='__main__':main()
