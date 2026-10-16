"""Replace unnecessary doglegs with one tangent turn; expose blocked cases."""
import json
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from outline_mount_concept import ROOT,OUT,draw,sha,RED
from fixed_mount_rf_plan import geometry,overlay,COLORS
from latest_connection_plan import rounded,check,pg

TARGETS={11,12,28,30}


def one_turn(r):
    s=np.array(r['start']);e=np.array(r['end']);u=np.array(r['outward'])
    t=(s[0]-e[0])/u[0]
    assert t>0
    corner=e+t*u
    # One quadratic fillet between the pad-axis ray and the SMP's vertical line.
    line=rounded([e,corner,s],trim=.65)
    return LineString(list(line.coords)[::-1]),list(corner)


def main():
    src=OUT/'vertical_smp_entry_audit.json';a=json.loads(src.read_text())
    hashes={p:sha(ROOT/p) for p in a['source_hashes']}
    rows=a['rows'];pads=a['pads'];mounts=a['mounts'];centre=a['qd_centre_mm']
    old=[LineString(p) for p in a['paths']];attempt=old.copy();corners={}
    for i,r in enumerate(rows):
        if r['qd_pad'] in TARGETS:attempt[i],corners[r['qd_pad']]=one_turn(r)
    all_check,smppads=check(rows,attempt,pads)
    # Keep the established safe path for any direct candidate hitting another
    # connector, rather than silently moving the connector or shorting a net.
    blocked={p[0] for p in all_check['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps']}
    paths=[old[i] if r['position'] in blocked else attempt[i] for i,r in enumerate(rows)]
    finalcheck,_=check(rows,paths,pads)
    report=dict(direct_candidate_checks=all_check,blocked_positions=sorted(blocked),
        revised_plan_checks=finalcheck,corners=corners,
        changes=[dict(qd_pad=r['qd_pad'],smp=r['smp'],
            one_turn_applied=r['position'] not in blocked,
            old_guide_length_mm=old[i].length,new_guide_length_mm=paths[i].length)
            for i,r in enumerate(rows) if r['qd_pad'] in TARGETS])
    print(json.dumps(report,indent=2))
    assert not finalcheck['centerline_crossings']
    assert not finalcheck['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps']
    _,_,_,_,_,snapshot=geometry()
    fig=plt.figure(figsize=(13,14),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(.85,1.2),height_ratios=(1,.95),
        left=.06,right=.965,top=.91,bottom=.14,wspace=.24,hspace=.28)
    full=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);issue=fig.add_subplot(gs[1,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,79),height=77.5,qd_center=centre)
    overlay(full,rows,paths,pads,False);full.set_title('Revised plan\n11 / 12 / 30: one smooth turn',fontsize=12)
    draw(detail,rows,pads,mounts,snapshot,True,ylim=(38.4,54.8),height=77.5,qd_center=centre)
    for i,r in enumerate(rows):
        if r['qd_pad'] in (11,12,30):
            x,y=old[i].xy;detail.plot(x,y,c='#a5b6b7',ls='--',lw=.7,alpha=.65)
            x,y=paths[i].xy;detail.plot(x,y,c=COLORS[i],lw=1.8,zorder=15)
            x,y=r['start'];d=1 if r['end'][1]>y else -1
            detail.annotate('',xy=(x,y+d*.3),xytext=(x,y+d*1.7),
                arrowprops=dict(arrowstyle='->',color=COLORS[i],lw=1.5),zorder=20)
    detail.set_title('One pad-axis departure + one curve + vertical entry\nDashed: rejected extra doglegs',fontsize=11)
    draw(issue,rows,pads,mounts,snapshot,True,ylim=(32,48.8),height=77.5,qd_center=centre)
    issue.set_xlim(11.3,19.9)
    i28=next(i for i,r in enumerate(rows) if r['qd_pad']==28)
    for i,r in enumerate(rows):
        if r['qd_pad']==30:
            x,y=paths[i].xy;issue.plot(x,y,c=COLORS[i],lw=2,zorder=15)
    x,y=attempt[i28].xy;issue.plot(x,y,c='#cd3b42',lw=2,ls='--',zorder=16)
    x,y=old[i28].xy;issue.plot(x,y,c=COLORS[i28],lw=1.4,zorder=15)
    issue.scatter(16.75,40.1,s=160,fc='none',ec='#cd3b42',lw=1.6,zorder=25)
    issue.annotate('Direct QD28 route\nhits SMP24 signal\nand overlaps QD30',xy=(16.75,40.1),
        xytext=(11.6,41.6),fontsize=9,color='#b72c38',
        arrowprops=dict(arrowstyle='->',color='#b72c38'),zorder=26,
        bbox=dict(fc='white',ec='none',alpha=.95))
    issue.set_title('QD28: direct vertical path is obstructed\nRed dashed = rejected; brown = retained bypass',fontsize=11)
    fig.suptitle('Remove the added RF doglegs',fontsize=20,y=.977)
    fig.text(.5,.947,'One-turn paths for QD11, QD12 and QD30 | QD28 obstruction is shown explicitly',ha='center',fontsize=11)
    fig.text(.5,.105,'Connector positions and circuit identities are unchanged. QD28 is not falsely reported as a completed one-turn path.',ha='center',fontsize=10)
    fig.text(.5,.078,'The direct QD28 alternative shares X = 16.75 mm with intervening SMP24; its signal pad lies in the path.',ha='center',fontsize=10)
    fig.text(.5,.051,'All 16 guides in the retained plan are non-crossing and avoid foreign pads in the limited geometry check.',ha='center',fontsize=10)
    fig.text(.5,.025,'PLAN ONLY: native files unchanged. R/C fit and DRC remain pending; the known copper-carrier incompatibility remains unresolved.',ha='center',fontsize=9.4,color=RED)
    fig.savefig(OUT/'Single_Turn_SMP_Entry_Review.png');plt.close(fig)
    assert hashes=={p:sha(ROOT/p) for p in hashes}
    report.update(status='PARTIAL_ONE_TURN_PROPOSAL_WITH_EXPLICIT_QD28_OBSTRUCTION',
        rows=rows,pads=pads,mounts=mounts,qd_centre_mm=centre,
        paths=[list(p.coords) for p in paths],native_unchanged=True,source_hashes=hashes)
    (OUT/'single_turn_smp_entry_audit.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
