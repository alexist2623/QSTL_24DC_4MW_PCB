"""Dimension the ZIF-to-cavity planar distance from verified saved PCB geometry."""
from pathlib import Path
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch
from gerbonara import GerberFile

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'QSTL_24DC_4MW_PCB'
SOURCE = ROOT / 'script' / 'mechanical_assembly_20260921'
OUT = PROJECT / 'Mechanical_Assembly' / 'Dimensions'
OUT.mkdir(exist_ok=True)
geometry = json.loads((SOURCE / 'pcb_geometry.json').read_text())
solids = json.loads((SOURCE / 'solid_geometry.json').read_text())
pcb_hash = hashlib.sha256((PROJECT / 'QSTL_24DC_4MW_PCB.PcbDoc').read_bytes()).hexdigest()
assert pcb_hash == geometry['pcb_sha256'], 'Cached geometry does not match saved PCB'
mm = lambda value: float(value.removesuffix('mil')) * 0.0254
component = next(c for c in geometry['components'] if c['SOURCEDESIGNATOR'] == 'J1')
body = next(b['props'] for b in geometry['bodies'] if b['component'] == 'J1')
assert float(component['ROTATION']) == 0
assert float(body['MODEL.3D.ROTX']) == 90
assert float(body['MODEL.3D.ROTY']) == float(body['MODEL.3D.ROTZ']) == 0
model = next(m for m in geometry['models'] if m['ID'] == body['MODELID'])
b = solids[Path(model['extracted_file']).name]['bounds']
bx, by = mm(body['MODEL.2D.X']), mm(body['MODEL.2D.Y'])
envelope = [bx + b[0], by - b[5], bx + b[3], by - b[2]]
body_centre = [(envelope[0] + envelope[2]) / 2, (envelope[1] + envelope[3]) / 2]
placement = [mm(component['X']), mm(component['Y'])]
cam = PROJECT / 'fabrication' / 'JLCPCB_HDI_20260922' / 'Gerber'
slot = GerberFile.open(cam / 'bottom blind slots layer.gbr')
(x0, y0), (x1, y1) = slot.bounding_box()
cavity = [(x0 + x1) / 2, (y0 + y1) / 2]
assert math.dist(cavity, [9.75, 42.5]) < 1e-5
distance_body = math.dist(body_centre, cavity)
distance_placement = math.dist(placement, cavity)
assert abs(distance_body - 37.975) < 1e-5
assert abs(distance_placement - 37.65) < 1e-5
report = {
    'pcb_sha256': pcb_hash,
    'measurement': 'PCB XY projection; not routed length or 3D spatial distance',
    'milling_centre_xy_mm': cavity,
    'zif_J1_placement_origin_xy_mm': placement,
    'zif_J1_model_envelope_xy_mm': envelope,
    'zif_J1_model_envelope_centre_xy_mm': body_centre,
    'placement_origin_to_milling_centre_mm': distance_placement,
    'model_envelope_centre_to_milling_centre_mm': distance_body,
}
(OUT / 'ZIF_to_milling_distance.json').write_text(json.dumps(report, indent=2) + '\n')

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'svg.fonttype': 'none'})
fig = plt.figure(figsize=(11.2, 9.4), facecolor='white')
blue, orange, ink = '#176bb5', '#d36b13', '#20313f'
fig.text(.055, .945, 'ZIF TO MILLING CENTRE', color=ink, fontsize=22, weight='bold')
fig.text(.055, .91, 'Saved PCB geometry  |  XY planar dimensions in mm  |  23 Sep 2026', color='#61717d', fontsize=10)
ax = fig.add_axes([.035, .075, .47, .80])
ax.set_aspect('equal')
ax.set_xlim(-8, 27)
ax.set_ylim(-2.5, 70)
ax.axis('off')
ax.add_patch(Rectangle((0, 0), 19.5, 67.9, fc='#e5eee9', ec='#466558', lw=1.5))
ax.plot([9.75, 9.75], [0, 67.9], ls='-.', lw=.7, color='#9caea3')

# Draw existing mounting and connector drills as contextual geometry.
for pad in geometry['pads']:
    px, py, sx, sy, *rest = pad['coords_mm']
    diameter = pad['coords_mm'][8]
    name = str(pad['component'])
    if diameter > 0:
        ax.add_patch(Circle((px, py), max(sx, sy) / 2, fc='#c6cdbb', ec='#7d8869', lw=.5))
        ax.add_patch(Circle((px, py), diameter / 2, fc='white', ec='#65746c', lw=.5))
    if name == 'Q1':
        rect = Rectangle((px-sx/2, py-sy/2), sx, sy, angle=pad['rotation'], rotation_point='center', fc='#c8ab68', ec='#9e844e', lw=.3)
        ax.add_patch(rect)
for c in geometry['components']:
    if c['SOURCEDESIGNATOR'].startswith('SMP'):
        px, py = mm(c['X']), mm(c['Y'])
        ax.add_patch(Circle((px, py), 2.75, fc='none', ec='#8b9b92', lw=.7))

def zif_envelope(target):
    target.add_patch(Rectangle((envelope[0], envelope[1]), envelope[2]-envelope[0], envelope[3]-envelope[1], fc='#d7dce1', ec='#4e5d69', lw=1.2))
    for pad in geometry['pads']:
        if pad['component'] == 'J1':
            px, py, sx, sy = pad['coords_mm'][:4]
            target.add_patch(Rectangle((px-sx/2, py-sy/2), sx, sy, fc='#b49a61', ec='none'))

zif_envelope(ax)
ax.text(9.75, 1.5, 'ZIF  J1', ha='center', color=ink, fontsize=10, weight='bold')
ax.add_patch(FancyBboxPatch((7.6, 40.35), 4.3, 4.3, boxstyle='round,pad=0,rounding_size=0.5', fc='#fff0dc', ec=orange, lw=1.5, linestyle='--'))
ax.plot(*cavity, marker='+', ms=12, mew=1.8, color=orange)
ax.plot(*body_centre, marker='+', ms=11, mew=1.6, color=blue)
for yy in [body_centre[1], cavity[1]]:
    ax.plot([-5.5, 9.75], [yy, yy], color=blue, lw=.8)
ax.annotate('', xy=(-4.7, cavity[1]), xytext=(-4.7, body_centre[1]), arrowprops={'arrowstyle': '<->', 'color': blue, 'lw': 1.5, 'shrinkA': 0, 'shrinkB': 0})
ax.text(-5.6, (cavity[1]+body_centre[1])/2, f'{distance_body:.3f} mm', rotation=90, ha='center', va='center', fontsize=16, weight='bold', color=blue, bbox={'fc': 'white', 'ec': 'none', 'pad': 4})
ax.annotate('Milling\ncentre', xy=cavity, xytext=(21.0, 46.3), color=orange, fontsize=10, arrowprops={'arrowstyle': '-', 'color': orange, 'lw': .9})
ax.text(9.75, 65.1, '19.5 x 67.9 PCB', ha='center', color='#61756a', fontsize=9)

detail = fig.add_axes([.575, .525, .38, .31])
detail.set_aspect('equal')
detail.set_xlim(-.4, 19.9)
detail.set_ylim(.7, 8.05)
detail.axis('off')
detail.set_title('ZIF REFERENCE POINTS — ENLARGED', loc='left', color=ink, fontsize=12, weight='bold', pad=9)
zif_envelope(detail)
detail.plot([.8, 18.7], [body_centre[1]]*2, color=blue, lw=1, ls='--')
detail.plot([.8, 18.7], [placement[1]]*2, color=orange, lw=1, ls=':')
detail.plot(*body_centre, marker='+', ms=12, color=blue, mew=1.6)
detail.plot(*placement, marker='x', ms=7, color=orange, mew=1.5)
detail.annotate('Placement origin\nY = 4.850', xy=placement, xytext=(11, 7.05), color=orange, fontsize=9, arrowprops={'arrowstyle': '-', 'color': orange})
detail.annotate('Model envelope centre\nY = 4.525', xy=body_centre, xytext=(1.1, 2.05), va='top', color=blue, fontsize=9, arrowprops={'arrowstyle': '-', 'color': blue})
fig.text(.575, .50, 'CENTRE-TO-CENTRE', color=blue, fontsize=11, weight='bold')
fig.text(.575, .457, f'{distance_body:.3f} mm', color=blue, fontsize=28, weight='bold')
fig.text(.575, .413, 'ZIF 3D-model envelope centre to milling centre', fontsize=9.6, color=ink)
fig.text(.575, .349, 'PCB PLACEMENT REFERENCE', color=orange, fontsize=11, weight='bold')
fig.text(.575, .31, f'{distance_placement:.2f} mm', color=orange, fontsize=22, weight='bold')
fig.text(.575, .27, 'J1 footprint origin to milling centre', fontsize=10, color=ink)
fig.text(.575, .187, 'Milling centre:  X 9.750, Y 42.500\nBoth ZIF references lie on X 9.750.\nBottom pocket shown projected into the PCB plan.', color='#5f6b76', fontsize=10, linespacing=1.7)
fig.text(.055, .033, 'Reference geometry only. The PCB was not modified. Distance excludes component height and pocket depth.', fontsize=9, color='#6f7a82')
fig.savefig(OUT / 'ZIF_to_milling_distance.png', dpi=180, facecolor='white')
fig.savefig(OUT / 'ZIF_to_milling_distance.svg', facecolor='white')
print(json.dumps(report, indent=2))
print(OUT / 'ZIF_to_milling_distance.png')
