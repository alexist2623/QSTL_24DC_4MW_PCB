"""Render the actual J2 footprint and highlight pads assigned to D-sub nets."""
from pathlib import Path
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from inspect_pinout import parse, rows, row, val, REF, OUT

source = REF / 'DSUBtoZIF_20250106.kicad_pcb'
audit = json.loads((OUT / 'pinout_audit.json').read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest() == audit['source_hashes'][source.name]
board = parse(source)
fp = next(f for f in rows(board, 'footprint') if any(p[1:3] == ['Reference', 'J2'] for p in rows(f, 'property')))
footprint_angle = float(row(fp, 'at')[3])
pins = {p['pin']: p for p in audit['ZIF_pad_mapping']}
used = {n for n, p in pins.items() if any(q['reference'] == 'J1' for q in p['connected_pads'])}
assert used == {str(n) for n in range(2, 51, 2)}

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13, 'svg.fonttype': 'none'})
fig = plt.figure(figsize=(14, 5.7), facecolor='white')
blue, gray, ink = '#087ac1', '#bac3cc', '#23384a'
fig.text(.045, .926, 'ANTON PCB  /  ZIF J2 PIN USAGE', fontsize=21, weight='bold', color=ink)
fig.text(.045, .867, 'Molex 502598-5193  |  Component-side top view  |  Rotated to horizontal; not mirrored', fontsize=11, color='#596c7c')
ax = fig.add_axes([.055, .20, .89, .58])
ax.set_aspect('equal');ax.set_xlim(-9.5, 9.5);ax.set_ylim(-3.25, 3.25);ax.axis('off')

# Native footprint coordinates use positive Y downward; plotting reverses Y.
for line in rows(fp, 'fp_line'):
    layer = val(line, 'layer')
    if layer not in ['F.Fab', 'F.SilkS']:
        continue
    a = [float(v) for v in row(line, 'start')[1:3]]
    b = [float(v) for v in row(line, 'end')[1:3]]
    ax.plot([a[0], b[0]], [-a[1], -b[1]], color='#536573' if layer == 'F.SilkS' else '#96a4af', lw=1.2 if layer == 'F.SilkS' else .85, zorder=1)
for p in rows(fp, 'pad'):
    number = p[1]
    at = [float(v) for v in row(p, 'at')[1:]]
    x, y = at[:2];w, h = map(float, row(p, 'size')[1:3])
    # Stored pad orientation is absolute; subtract the footprint orientation.
    angle = (at[2] if len(at)>2 else 0) - footprint_angle
    selected = number in used
    color = blue if selected else gray
    patch = Rectangle((x-w/2, -y-h/2), w, h, angle=angle, rotation_point='center', fc=color, ec=blue if selected else '#8696a4', lw=.8, zorder=3)
    ax.add_patch(patch)
    if number.isdigit():
        if selected:
            ax.text(x, 2.05, number, ha='center', va='bottom', fontsize=12.2, weight='bold', color=blue)
        else:
            ax.text(x, -2.1, number, ha='center', va='top', fontsize=11.5, color='#788897')
    else:
        ax.text(x, -2.15, number, ha='center', va='top', fontsize=10.5, color='#677c8a')

ax.text(0, 2.90, 'USED: 2, 4, 6, ... , 50  (25 pins)', ha='center', fontsize=14, color=blue, weight='bold')
ax.text(0, -.05, 'J2  /  502598-5193', ha='center', va='center', fontsize=17, color='#84939f')
ax.text(0, -.48, 'Actual pad geometry from Anton\'s KiCad PCB', ha='center', fontsize=10, color='#8395a3')
ax.add_patch(Circle((-7.5, -1.59), .47, fc='none', ec='#b76a1b', lw=1.3, zorder=5))
ax.text(-7.5, -3.05, 'PIN 1', ha='center', color='#a95e14', fontsize=11, weight='bold')
fig.text(.065, .135, 'BLUE = connected to D-sub', color=blue, fontsize=13, weight='bold')
fig.text(.47, .135, 'GRAY = unconnected  |  Odd pins 1-51 and MP1/MP2', color='#6d8090', fontsize=11)
fig.text(.045, .053, 'Source: DSUBtoZIF_20250306.zip / DSUBtoZIF_20250106.kicad_pcb  |  PCB source unchanged', color='#748591', fontsize=9)
fig.savefig(OUT / 'Anton_ZIF_J2_footprint.png', dpi=180, facecolor='white')
fig.savefig(OUT / 'Anton_ZIF_J2_footprint.svg', facecolor='white')
print(OUT / 'Anton_ZIF_J2_footprint.png')
