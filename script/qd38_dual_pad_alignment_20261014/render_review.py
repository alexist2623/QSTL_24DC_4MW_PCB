"""Publish the both-boundary pad alignment review, preserving native designs."""
from pathlib import Path
import hashlib
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, Rectangle, Circle
from shapely.geometry import shape, Point
from analyze import pg, BOUND, BASE, SRC, ROOT, OUT


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source = json.loads(SRC.read_text())
    protected = [Path(source['source']), ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.SchDoc',
                 ROOT/'QSTL_QD4_2SET_38PAD/QD4_2SET_38.PcbLib']
    before_hashes = {str(p):sha(p) for p in protected}
    assert before_hashes[str(Path(source['source']))] == BASE
    a = json.loads((OUT/'analysis.json').read_text())
    trial = next(t for t in a['trials'] if t['mode']=='rectangle_extrema' and t['depth_mm']==.84)
    assert trial['pad_pair_min'][0] >= .15 and trial['foreign_via_min'][0] >= .15
    assert trial['via_drills_contained'] and trial['cavity_gap'] >= .2-1e-8
    rows = trial['rows']
    unit = 2.54e-6
    boundary_checks = []
    for r in rows:
        p = r['after']
        # Native-grid prediction; this does not edit a native pad.
        p = dict(p, **{k:round(p[k]/unit)*unit for k in ('x','y','size_x','size_y')})
        g = pg(p)
        axis, inner, sign = BOUND[r['side']]
        vals = [pt[axis] for pt in g.exterior.coords]
        nearest = min(vals) if sign > 0 else max(vals)
        furthest = max(vals) if sign > 0 else min(vals)
        boundary_checks.append(dict(pad=r['number'], side=r['side'],
            inner_error_mm=abs(nearest-inner), outer_error_mm=abs(furthest-(inner+sign*.84))))
    assert max(max(x['inner_error_mm'],x['outer_error_mm']) for x in boundary_checks) < 4e-6
    fig, axes = plt.subplots(1,2,figsize=(13.0,8.6),dpi=180)
    for ax, state, title in zip(axes,('before','after'),('Last saved layout: inner ends aligned',
                                                      'Revised review: inner AND outer ends aligned')):
        ax.set_facecolor('#172c36')
        ax.add_patch(Rectangle((7.6,39.85),4.3,5.3,facecolor='#0b1820',edgecolor='#91a4ac',lw=.8))
        for r in rows:
            p = r[state]
            g = pg(p)
            color = '#e8b762' if p['net'].startswith('MW') else '#61c7dc'
            ax.add_patch(Patch(list(g.exterior.coords),facecolor=color,edgecolor='#e3eef1',lw=.35))
            ax.text(p['x'],p['y'],p['number'],fontsize=6.3,ha='center',va='center',color='#102833')
        ax.add_patch(Rectangle((7.4,39.65),4.7,5.7,fill=False,edgecolor='#b4eee5',lw=1.25,ls='--'))
        ax.add_patch(Rectangle((6.56,38.81),6.38,7.38,fill=False,edgecolor='#f59cc0',lw=1.25,ls='--'))
        ax.text(9.75,42.8,'QD / CHIP',ha='center',va='center',color='white',fontsize=12)
        ax.text(9.75,42.1,'Existing cavity\n4.30 x 5.30 mm',ha='center',va='center',color='#b7c7cc',fontsize=10)
        ax.text(9.75,41.15,'Inner boundary\n4.70 x 5.70 mm',ha='center',va='center',color='#b4eee5',fontsize=10)
        ax.text(9.75,38.45,'Outer boundary 6.38 x 7.38 mm',ha='center',color='#b94b7b',fontsize=9)
        ax.set(xlim=(6.0,13.5),ylim=(38.15,46.8),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)',title=title)
    fig.suptitle('16-RF / 38-DC carrier: all 38 bond pads',fontsize=15,y=.98)
    fig.text(.5,.072,'Pad width 0.25 mm and bond-parallel angles retained | Length adjusted from 0.80 to 0.802–0.865 mm',
             ha='center',fontsize=10)
    fig.text(.5,.047,'Aligned ends mean the inward/outward extremal corners. Rectangular pads retain tilted short end faces.',
             ha='center',fontsize=9,color='#8b3e31')
    fig.text(.5,.022,'Relocation review only; native PCB unchanged. Future R/C basis: 0603 resistors + Yageo CC1206JKNPO9BN104 1206 capacitors.',
             ha='center',fontsize=9,color='#425c68')
    fig.subplots_adjust(left=.06,right=.98,top=.91,bottom=.14,wspace=.20)
    target = OUT/'Both_Pad_Ends_Aligned_Review.png'
    fig.savefig(target)
    plt.close(fig)
    after_hashes = {str(p):sha(p) for p in protected}
    assert before_hashes == after_hashes
    report = dict(status='RELOCATION_REVIEW_ONLY_NOT_APPLIED', source_sha256=BASE,
                  scope='All 38 pad inward and outward supporting extrema aligned; native source and routing not changed.',
                  full_tilted_end_faces_collinear=False, inner_bounds_mm=[7.4,39.65,12.1,45.35],
                  outer_bounds_mm=[6.56,38.81,12.94,46.19], width_mm=.25,
                  length_range_mm=trial['length_range'], minimum_pad_gap_mm=trial['pad_pair_min'][0],
                  minimum_foreign_signal_via_gap_mm=trial['foreign_via_min'][0],
                  minimum_cavity_gap_mm=trial['cavity_gap'], all_existing_QD_drills_inside_pads=True,
                  native_grid_boundary_checks=boundary_checks,
                  image=str(target), image_sha256=sha(target), source_hashes=before_hashes,
                  native_sources_unchanged=True,
                  pending=['RF/DC terminal and foreign-copper clearance in the revised full layout',
                           'GND/shield/mask update for changed pads',
                           'R0603/C1206 relocation feasibility',
                           'Native PCB/library implementation, save/reopen connectivity and DRC'])
    (OUT/'review_manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('native_grid_boundary_checks','source_hashes')},indent=2))


if __name__=='__main__':
    main()
