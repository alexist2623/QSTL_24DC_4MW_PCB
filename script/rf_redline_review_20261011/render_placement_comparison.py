"""Illustrate a measured SMP placement candidate without modifying a design."""
import hashlib
import importlib.util
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / 'script/qd38_pad_alignment_20261011'
native = json.loads((BASE / 'saved_revision_snapshot.json').read_text())
plan = json.loads((BASE / 'alignment_full_candidate.json').read_text())
placement = json.loads((HERE / 'placement_feasibility_measurements.json').read_text())
model = json.loads((HERE / 'smp_embedded_model_geometry_review.json').read_text())
proposal = placement['recommended_review_candidate']
pcb = Path(native['source'])
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pcb) == native['source_sha256']
spec = importlib.util.spec_from_file_location('renderer', ROOT / 'script/qd38_rotation_20261011/render_saved_revision_review.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
conflicts = {x['rc_pad'].split('.')[0] for x in proposal['current_RC_pad_collisions_or_below_0p15_clearance']}
fig, axes = plt.subplots(1, 2, figsize=(11, 13), dpi=180)

for ax, proposed in zip(axes, (False, True)):
    ax.add_patch(Rectangle((0, 0), 19.5, 67.9, facecolor='#f4f8f7', edgecolor='#395961', lw=1.3))
    centres = proposal['centres'] if proposed else [dict(name=s['ref'], x=s['x'], y=s['y']) for s in plan['smp']]
    if proposed:
        ax.add_patch(Rectangle((0, 38.75), 19.5, 7.5, facecolor='#d7f1e6', edgecolor='none'))
        ax.text(.5, 42.5, 'No SMP\nbeside QD', fontsize=10, color='#136f50', va='center')
    for p in native['pads']:
        if p['component'] and p['component'].startswith('SMP'):
            continue
        if p['y'] < 16:
            continue
        color = '#d98d65' if p['component'] and p['component'].startswith(('R','C')) else '#8a9a9b'
        if proposed and p['component'] in conflicts:
            color = '#d74e3b'
        if p['component'] == 'Q1': color = '#c19a38'
        r.polygon(ax, r.pad_shape(p), color, .85)
        if p['hole']:
            ax.add_patch(Circle((p['x'], p['y']), p['hole']/2, facecolor='white', edgecolor='none'))
    for s in centres:
        x, y = s['x'], s['y']
        # The exact model's 5.5 mm XY bounding box is a conservative projection.
        ax.add_patch(Rectangle((x-2.75, y-2.75), 5.5, 5.5, facecolor='#d3e2f0',
                               edgecolor='#6b8daa', linestyle='--', linewidth=.75, alpha=.50))
        for dx, dy in [(0,0),(-1.27,1.27),(-1.27,-1.27),(1.27,-1.27),(1.27,1.27)]:
            ax.add_patch(Circle((x+dx,y+dy), .5, facecolor='#52687b', edgecolor='none'))
            ax.add_patch(Circle((x+dx,y+dy), .375, facecolor='white', edgecolor='none'))
        ax.text(x, y+2, s['name'], ha='center', va='center', fontsize=7, color='#23465f')
    ax.add_patch(Rectangle((7.6,39.85),4.3,5.3,facecolor='#142e34',edgecolor='#142e34'))
    ax.text(9.75,42.5,'QD',ha='center',va='center',fontsize=11,color='white')
    ax.axhline(42.5,color='#627a80',ls=':',lw=.65)
    y1,y2 = (54.75,60.5) if proposed else (54.5,60.5)
    ax.annotate('', xy=(20.5,y1),xytext=(20.5,y2),arrowprops=dict(arrowstyle='<->',color='#304e61'))
    ax.text(20.85,(y1+y2)/2,'5.75 mm' if proposed else '6.00 mm',rotation=90,va='center',fontsize=9)
    ax.set(xlim=(-.65,22.1),ylim=(16,68.5),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    ax.set_title('Offline candidate: 3 / 3 / 2 | QD | 2 / 3 / 3' if proposed else 'Current saved placement',fontsize=11,pad=12)
    ax.grid(alpha=.15, lw=.5); ax.tick_params(labelsize=8)

fig.suptitle('SMP / RF feasibility only — native PCB unchanged',fontsize=16,y=.99)
fig.text(.5,.047,'Candidate: 16 SMPs; side columns X = 2.75 / 16.75 mm; 8 above + 8 below QD.\n'
         'Blue dashed boxes: actual STEP bounding projections on Top. Red pads: existing Bottom R/C conflicts.\n'
         'Body gap = 0.25 mm; body-to-board edge = 0 mm nominal. R/C relocation and RF rerouting are required.\n'
         'No trial RF tracks are shown. Full routing, shielding, cable-plug access and native DRC are not certified.',
         ha='center',va='center',fontsize=9,linespacing=1.5,color='#283b45')
fig.subplots_adjust(top=.948,bottom=.115,left=.065,right=.97,wspace=.22)
out = HERE/'SMP_outboard_no_QD_side_review.png'
fig.savefig(out,facecolor='white');plt.close(fig)
assert sha(pcb) == native['source_sha256']
manifest = dict(status='READ_ONLY_PLACEMENT_CANDIDATE',native_sha256=native['source_sha256'],
                native_changed=False,placement_report_sha256=sha(HERE/'placement_feasibility_measurements.json'),
                model_report_sha256=sha(HERE/'smp_embedded_model_geometry_review.json'),
                rf_routing_verified=False,image=str(out),image_sha256=sha(out))
(HERE/'placement_review_image_manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
