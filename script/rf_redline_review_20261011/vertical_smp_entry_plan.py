"""Review vertical SMP entry for QD pads 11/12/28/30 without native edits."""
import json
from copy import deepcopy
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from outline_mount_concept import ROOT, OUT, draw, sha, RED
from fixed_mount_rf_plan import overlay, COLORS, geometry
from latest_connection_plan import rounded, check

TARGETS={11,12,28,30}


def main():
    src=OUT/'qd_gap_midpoint_audit.json';a=json.loads(src.read_text())
    hashes={p:sha(ROOT/p) for p in a['source_hashes']}
    rows=deepcopy(a['rows']);pads=a['pads'];mounts=a['mounts']
    old=[LineString(p) for p in a['paths']];paths=old.copy();changes=[]
    bus={11:4.95,12:4.95,30:14.65,28:13.75}
    for i,r in enumerate(rows):
        if r['qd_pad'] not in TARGETS:continue
        s=np.array(r['start']);e=np.array(r['end']);u=np.array(r['outward']);e1=e+u*.65
        toward=1 if e[1]>s[1] else -1
        side=1 if 'upper' in r['kind'] else -1
        b=bus[r['qd_pad']];turn_y=s[1]+toward*2.6
        paths[i]=rounded([s,[s[0],turn_y],[b,turn_y],[b,e1[1]+side*.45],e1,e])
        p0,p1=list(paths[i].coords)[:2]
        assert abs(p1[0]-p0[0])<1e-10 and abs(p1[1]-p0[1])>1
        changes.append(dict(qd_pad=r['qd_pad'],smp=r['smp'],
            entry_from='above' if toward>0 else 'below',
            old_guide_length_mm=old[i].length,new_guide_length_mm=paths[i].length,
            length_change_mm=paths[i].length-old[i].length))
    checks,_=check(rows,paths,pads)
    assert not checks['centerline_crossings'],checks
    assert not checks['projected_0p11mm_trace_to_SMP_or_foreign_QD_pad_overlaps'],checks
    _,_,_,_,_,snapshot=geometry();centre=a['new_qd_centre_mm']
    fig=plt.figure(figsize=(12,14),dpi=190)
    gs=fig.add_gridspec(2,2,width_ratios=(.8,1.25),height_ratios=(1,.65),
        left=.065,right=.965,top=.91,bottom=.13,wspace=.25,hspace=.23)
    full=fig.add_subplot(gs[:,0]);detail=fig.add_subplot(gs[0,1]);table=fig.add_subplot(gs[1,1])
    draw(full,rows,pads,mounts,snapshot,True,ylim=(0,79),height=77.5,qd_center=centre)
    overlay(full,rows,paths,pads,False);full.set_title('Revised proposed RF connections',fontsize=12)
    draw(detail,rows,pads,mounts,snapshot,True,ylim=(31.3,55.3),height=77.5,qd_center=centre)
    for i,(r,path) in enumerate(zip(rows,paths)):
        if r['qd_pad'] in TARGETS:
            x,y=old[i].xy;detail.plot(x,y,ls='--',lw=.8,c='#9eafb3',alpha=.7)
            x,y=path.xy;detail.plot(x,y,lw=1.7,c=COLORS[i],zorder=15)
            x,y=r['start'];d=1 if r['end'][1]>y else -1
            detail.annotate('',xy=(x,y+d*.25),xytext=(x,y+d*1.9),
                arrowprops=dict(arrowstyle='->',color=COLORS[i],lw=1.7),zorder=20)
        else:
            x,y=path.xy;detail.plot(x,y,lw=.5,c='#9db2b7',alpha=.5,zorder=5)
    detail.set_title('Solid: revised vertical entries\nDashed: previous horizontal entries',fontsize=12)
    table.axis('off')
    cells=[[str(c['qd_pad']),c['smp'],c['entry_from'].upper(),f"{c['length_change_mm']:+.2f} mm"] for c in changes]
    t=table.table(cellText=cells,colLabels=['QD pad','SMP','Entry side','Guide length change'],
        cellLoc='center',bbox=[0,.38,1,.5],colWidths=[.15,.22,.23,.4])
    t.auto_set_font_size(False);t.set_fontsize(10)
    for (r,c),cell in t.get_celld().items():
        cell.set_edgecolor('#c5d3d5');cell.set_facecolor('#214750' if r==0 else '#edf5f4')
        cell.get_text().set_color('white' if r==0 else '#214750')
    table.text(.5,.23,'All 16 guide centre lines remain non-crossing.\nNo overlap with the saved SMP / foreign QD pads.',
        ha='center',fontsize=10,transform=table.transAxes)
    table.text(.5,.04,'R/C positions and RF shield escape gaps must follow the final route.\nThis picture does not establish component fit or 50-ohm performance.',
        ha='center',fontsize=9.5,color=RED,transform=table.transAxes)
    fig.suptitle('QD 11 / 12 / 28 / 30: vertical SMP entry proposal',fontsize=18,y=.975)
    fig.text(.5,.943,'Connector positions and QD centre (9.75, 46.15) mm retained | Pad 20 remains DC-only',ha='center',fontsize=10.5)
    fig.text(.5,.09,'QD11 enters SMP05 from below; QD12, QD30 and QD28 enter their SMPs from above.',ha='center',fontsize=10)
    fig.text(.5,.061,'RF guides preserve circuit membership and pad 15 immediate curvature. Other 12 guide paths are unchanged.',ha='center',fontsize=10)
    fig.text(.5,.031,'PLANNING ONLY: native PCB/CAD unchanged. R/C, DC/GND/shields, mask and native DRC remain pending.',ha='center',fontsize=9.5,color=RED)
    fig.savefig(OUT/'Vertical_SMP_Entry_QD11_12_28_30.png');plt.close(fig)
    assert hashes=={p:sha(ROOT/p) for p in hashes}
    result=dict(status='VERTICAL_ENTRY_REVIEW_ONLY',source_plan_sha256=sha(src),changes=changes,
        checks=checks,rows=rows,pads=pads,mounts=mounts,qd_centre_mm=centre,
        paths=[list(p.coords) for p in paths],native_unchanged=True,source_hashes=hashes)
    (OUT/'vertical_smp_entry_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(changes=changes,checks=checks,native_unchanged=True),indent=2))


if __name__=='__main__':main()
