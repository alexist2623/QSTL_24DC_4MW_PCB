"""Read-only SMP placement sketch using saved QD and mounting-pad geometry."""
from pathlib import Path
import hashlib
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
PCB = DEST / 'QSTL_QD4_2SET_38PAD.PcbDoc'
native = json.loads((H / 'through_dc_saved_native_snapshot.json').read_text())
assert hashlib.sha256(PCB.read_bytes()).hexdigest() == native['source_sha256']
rows = [(24.5, [3.75, 9.75, 15.75]), (30.5, [3.75, 15.75]),
        (36.5, [3.75, 15.75]), (42.5, [3.75, 15.75]),
        (48.5, [3.75, 15.75]), (54.5, [3.75, 15.75]),
        (60.5, [3.75, 9.75, 15.75])]
fig, axes = plt.subplots(1, 2, figsize=(11.5, 10), gridspec_kw={'width_ratios': [1, 1.5]})
for ax in axes:
    ax.set_aspect('equal')
    ax.add_patch(Polygon(native['board_outline'], closed=True, facecolor='#e6efe8', edgecolor='#263e35'))
    for p in native['pads']:
        if p['component'] is None:
            ax.add_patch(Circle((p['x'], p['y']), max(p['size_x'], p['size_y'])/2, facecolor='#ccba76', edgecolor='#716631', lw=.5))
            ax.add_patch(Circle((p['x'], p['y']), p['hole']/2, facecolor='white', edgecolor='#6b726e', lw=.5))
    ax.add_patch(Rectangle((7.1, 40.35), 5.3, 4.3, facecolor='#ffffff', edgecolor='#ab3939', lw=1.1))
    for p in native['pads']:
        if p['component'] != 'Q1':
            continue
        a = math.radians(p['rotation'])
        vertices = [(p['x']+u*p['size_x']/2*math.cos(a)-v*p['size_y']/2*math.sin(a),
                     p['y']+u*p['size_x']/2*math.sin(a)+v*p['size_y']/2*math.cos(a))
                    for u,v in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        ax.add_patch(Polygon(vertices, facecolor='#c98a26', edgecolor='#68481b', lw=.35))
    for y, xs in rows:
        side = y == 42.5
        color = '#e99040' if side else '#3186a9'
        for x in xs:
            ax.add_patch(Circle((x,y), 2.75, facecolor=color, alpha=.19, edgecolor=color, lw=1.3))
            ax.add_patch(Circle((x,y), .5, facecolor='#d2b35d', edgecolor='#665321', lw=.5))
            ax.add_patch(Circle((x,y), .375, facecolor='white', edgecolor='none'))
            for dx in [-1.27, 1.27]:
                for dy in [-1.27, 1.27]:
                    ax.add_patch(Circle((x+dx,y+dy), .5, facecolor='#d2b35d', edgecolor='#665321', lw=.5))
                    ax.add_patch(Circle((x+dx,y+dy), .375, facecolor='white', edgecolor='none'))
    ax.axhline(42.5, color='#ab3939', linestyle=':', lw=.8)
    ax.set_xlabel('X (mm)')
    ax.set_ylabel('Y (mm)')
    ax.tick_params(labelsize=9)
axes[0].set(xlim=(-.8,24), ylim=(-.8,68.7), title='Seven rows | 16 SMP')
for y, xs in rows:
    axes[0].text(21,y,'2\n(QD)' if y==42.5 else str(len(xs)),ha='center',va='center',fontsize=9,
                 color='#bc6426' if y==42.5 else '#2e6680')
axes[0].text(9.75, 12, 'Existing ZIF area\nunchanged', ha='center', va='center', color='#53625d', fontsize=9)
axes[1].set(xlim=(-.2,19.7), ylim=(37.4,47.6), title='Middle row: SMP — QD — SMP')
axes[1].text(9.75,42.5,'QD pocket\n5.3 × 4.3 mm',ha='center',va='center',fontsize=10,color='#ab3939')
axes[1].text(3.75,46,'SMP',ha='center',va='center',fontsize=11,color='#bc6426')
axes[1].text(15.75,46,'SMP',ha='center',va='center',fontsize=11,color='#bc6426')
fig.suptitle('Corrected SMP placement: 3 / 2 / 2 / 2 (QD) / 2 / 2 / 3', fontsize=15)
fig.text(.5,.07,'Transparent circles: nominal Ø5.5 mm Top bodies. Gold/white: through-hole lands/drills.\nQD pads and pocket are shown in the same XY projection on the Bottom face.',ha='center',fontsize=10)
fig.text(.5,.023,'PLACEMENT STUDY ONLY — native PCB unchanged; R/C, routing and shields must be redesigned and checked.',ha='center',fontsize=9,color='#9c3939')
fig.tight_layout(rect=(0,.10,1,.96))
out = DEST / 'review' / 'SMP_16_seven_rows_3222223_proposal_20261011.png'
fig.savefig(out,dpi=170)
plt.close(fig)
assert hashlib.sha256(PCB.read_bytes()).hexdigest() == native['source_sha256']
print(out)
