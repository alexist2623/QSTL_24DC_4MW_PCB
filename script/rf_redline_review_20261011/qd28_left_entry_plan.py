"""Remove the SMP28 double turn by entering its signal pad from the left."""
import json
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from outline_mount_concept import ROOT,OUT,draw,sha,RED
from fixed_mount_rf_plan import geometry,overlay,COLORS
from latest_connection_plan import rounded,check


def main():
    src=OUT/'single_turn_smp_entry_audit.json';a=json.loads(src.read_text())
    hashes={p:sha(ROOT/p) for p in a['source_hashes']}
    rows=a['rows'];pads=a['pads'];mounts=a['mounts'];centre=a['qd_centre_mm']
    old=[LineString(p) for p in a['paths']];paths=old.copy()
    i=next(i for i,r in enumerate(rows) if r['qd_pad']==28);r=rows[i]
    s=np.array(r['start']);e=np.array(r['end']);u=np.array(r['outward']);e1=e+.65*u
    bus=13.75
    # Retain the existing QD departure and descending bus. At the SMP end,
    # make one rounded corner at (bus, signal Y), then enter horizontally.
    paths[i]=rounded([s,[bus,s[1]],[bus,e1[1]-.45],e1,e])
    p0,p1=list(paths[i].coords)[:2]
    assert abs(p1[1]-p0[1])<1e-10 and p1[0]<p0[0]
    assert all(paths[j].equals_exact(old[j],0) for j in range(16) if j!=i)
    checks,_=check(rows,paths,pads)
    assert not checks['centerline_crossings'],checks
    assert not checks['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps'],checks
    # With storage ordered from SMP to QD, sample the terminal portion and
    # confirm its path turns once from horizontal to vertical before Y=39.
    xy=np.asarray(paths[i].coords);local=xy[xy[:,1]<=39.0]
    headings=np.unwrap(np.arctan2(np.diff(local[:,1]),np.diff(local[:,0])))
    turns=np.diff(headings);active=np.flatnonzero(abs(turns)>1e-7)
    groups=0 if not len(active) else 1+int(np.sum(np.diff(active)>1))
    assert groups==1
    _,_,_,_,_,snapshot=geometry()
    fig=plt.figure(figsize=(12,13),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(.8,1.2),height_ratios=(1,.9),
        left=.065,right=.965,top=.91,bottom=.13,wspace=.24,hspace=.28)
    full=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);close=fig.add_subplot(gs[1,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,79),height=77.5,qd_center=centre)
    overlay(full,rows,paths,pads,False);full.set_title('Corrected proposed RF connections',fontsize=12)
    draw(detail,rows,pads,mounts,snapshot,True,ylim=(31.5,49.5),height=77.5,qd_center=centre)
    detail.set_xlim(10.5,19.8)
    for j,(rr,p) in enumerate(zip(rows,paths)):
        x,y=p.xy
        detail.plot(x,y,c=COLORS[j] if rr['qd_pad'] in (28,30) else '#adbdbe',
            lw=1.7 if rr['qd_pad'] in (28,30) else .65,zorder=12)
    x,y=old[i].xy;detail.plot(x,y,c='#9da9ad',lw=.85,ls='--',alpha=.8,zorder=11)
    detail.set_title('QD28 route: descending bus -> left entry\nQD30 and all other paths retained',fontsize=11)
    draw(close,rows,pads,mounts,snapshot,True,ylim=(31.2,39),height=77.5,qd_center=centre)
    close.set_xlim(12.5,19.8)
    x,y=old[i].xy;close.plot(x,y,c='#9caeb2',lw=1.1,ls='--',zorder=11)
    x,y=paths[i].xy;close.plot(x,y,c=COLORS[i],lw=2,zorder=15)
    close.annotate('',xy=(16.4,34.35),xytext=(14.9,34.35),
        arrowprops=dict(arrowstyle='->',color=COLORS[i],lw=1.8),zorder=20)
    close.annotate('One smooth turn\nat the SMP approach',xy=(13.86,34.55),xytext=(14.7,32.0),
        fontsize=9,color=COLORS[i],arrowprops=dict(arrowstyle='->',color=COLORS[i]),zorder=20,
        bbox=dict(fc='white',ec='none',alpha=.9))
    close.set_title('SMP28 close-up\nSolid: left entry | Dashed: removed double turn',fontsize=11)
    fig.suptitle('QD28 enters SMP28 from the left',fontsize=20,y=.975)
    fig.text(.5,.944,'The forced vertical approach is removed; the descending route turns directly toward the signal pad.',ha='center',fontsize=10.5)
    fig.text(.5,.093,'No connector relocation or pin reassignment. The QD-side transition is retained; only the SMP-end dogleg changes.',ha='center',fontsize=10)
    fig.text(.5,.065,'All 16 guides remain non-crossing and avoid foreign pads in the limited 0.11 mm geometry check.',ha='center',fontsize=10)
    fig.text(.5,.035,'PLAN ONLY: native PCB/CAD unchanged. Full routing validation and the documented copper-carrier fit issue remain pending.',ha='center',fontsize=9.5,color=RED)
    fig.savefig(OUT/'QD28_Left_Entry_Single_SMP_Turn.png');plt.close(fig)
    assert hashes=={p:sha(ROOT/p) for p in hashes}
    result=dict(status='QD28_LEFT_ENTRY_PROPOSAL_NOT_APPLIED',source_plan_sha256=sha(src),
        qd_pad=28,smp='SMP28',SMP_entry_from='left',SMP_approach_turn_regions=groups,
        QD_departure_preserved=True,other_15_guides_unchanged=True,
        all_terminal_positions_and_circuit_membership_preserved=True,
        old_guide_length_mm=old[i].length,new_guide_length_mm=paths[i].length,
        checks=checks,rows=rows,pads=pads,mounts=mounts,qd_centre_mm=centre,
        paths=[list(p.coords) for p in paths],native_unchanged=True,source_hashes=hashes)
    (OUT/'qd28_left_entry_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pads','mounts','paths','source_hashes')},indent=2))


if __name__=='__main__':main()
