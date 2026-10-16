"""Render audited saved copper, with DC and RF shown separately at true scale."""
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as PlotPolygon, Rectangle
from shapely.affinity import rotate, translate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'


def pad_shape(p):
    if p['shape'] == 1:
        return Point(p['x'], p['y']).buffer(p['size_x']/2, quad_segs=64)
    return translate(rotate(box(-p['size_x']/2, -p['size_y']/2,
                                p['size_x']/2, p['size_y']/2),
                            p['rotation'], origin=(0, 0)), p['x'], p['y'])


def polygon(ax, geometry, color, alpha=1, edge='none'):
    if geometry.is_empty:
        return
    for g in geometry.geoms if hasattr(geometry, 'geoms') else [geometry]:
        ax.add_patch(PlotPolygon(list(g.exterior.coords), facecolor=color,
                                edgecolor=edge, linewidth=.5, alpha=alpha))


def draw(ax, native, plan, layer, crop, title, color):
    ax.set_facecolor('#111923')
    board = Polygon(native['board_outline'])
    polygon(ax, board, '#172630', edge='#687a85')
    pp = native['pads']
    hulls = defaultdict(list)
    for p in pp:
        ref = p['component'] or ''
        if ref.startswith('SMP') or ref.startswith('R'):
            hulls[ref].append(pad_shape(p))
    if layer in (2, 4):
        for ref, shapes in hulls.items():
            g = unary_union(shapes).convex_hull
            polygon(ax, g, '#705264' if ref.startswith('R') else '#485364', .4)
    for p in pp:
        if p['layer'] not in (layer, 74) and p['component'] != 'Q1':
            continue
        polygon(ax, pad_shape(p), '#c5ab65' if p['net'] != 'GND' else '#697982', .65)
        if p['hole']:
            ax.add_patch(Circle((p['x'], p['y']), p['hole']/2,
                                facecolor='#10151c', edgecolor='none'))
    # Patch widths are in millimetres, not arbitrary screen line widths.
    from shapely.geometry import LineString
    for t in native['tracks']:
        if t['layer'] != layer or t['net'] == 'GND':
            continue
        geom = LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).buffer(t['width']/2, quad_segs=24)
        polygon(ax, geom, color)
    for a in native['arcs']:
        if a['layer'] != layer:
            continue
        sweep = (a['end_angle']-a['start_angle']) % 360
        count = max(8, math.ceil(sweep/1.5))
        angles = [math.radians(a['start_angle']+sweep*i/count) for i in range(count+1)]
        points = [(a['cx']+a['radius']*math.cos(x), a['cy']+a['radius']*math.sin(x)) for x in angles]
        polygon(ax, LineString(points).buffer(a['width']/2, quad_segs=24), color)
    for v in plan['vias']:
        ax.add_patch(Circle((v['x'], v['y']), v['diameter']/2,
                            facecolor='#d99571', edgecolor='none', alpha=.9))
        ax.add_patch(Circle((v['x'], v['y']), v['hole']/2,
                            facecolor='#10151c', edgecolor='none'))
    if layer == 32:
        for v in plan['shield_vias']:
            ax.add_patch(Circle((v['x'], v['y']), v['diameter']/2,
                                facecolor='#58766a', edgecolor='none', alpha=.75))
        for c in plan['components']:
            if c['ref'].startswith(('R', 'C')):
                ax.text(c['x'], c['y']+.35, c['ref'], color='#eeeeee',
                        fontsize=5, ha='center')
    cx, cy = plan['sample_center']; w, h = plan['cavity_mm']
    ax.add_patch(Rectangle((cx-w/2, cy-h/2), w, h, facecolor='#080b10',
                           edgecolor='#d4dbe0', linewidth=.65, linestyle='--'))
    ax.axvline(cx, color='#dddddd', lw=.45, ls=':', alpha=.55)
    ax.set(xlim=(-.4, 19.9), ylim=crop, aspect='equal', xlabel='X (mm)',
           ylabel='Y (mm)', title=title)
    ax.tick_params(labelsize=8)


def main():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    audit = json.loads((HERE/'saved_revision_audit.json').read_text())
    assert audit['passed'] and audit['native_sha256'] == digest(DEST/(DEST.name+'.PcbDoc'))
    candidate = Path(audit['candidate_file'])
    assert audit['candidate_sha256'] == digest(candidate)
    native = json.loads((HERE/'saved_revision_snapshot.json').read_text())
    plan = json.loads(candidate.read_text())
    out = DEST/'review'
    out.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(9, 14), dpi=180)
    for ax, layer, color in zip(axes, (2, 4), ('#f7b36c', '#66d3ea')):
        n = sum(layers == [layer] for layers in audit['DC_internal_layers'].values())
        draw(ax, native, plan, layer, (-.5, 68.4), f'L{layer} DC — {n} channels', color)
    fig.suptitle('Saved 38-channel DC routing\n0.125 mm width · 0.10 mm DC pair rule', fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .96))
    fig.savefig(out/'DC_saved_two_layers.png'); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 14), dpi=180)
    draw(ax, native, plan, 32, (22, 64), 'Saved Bottom RF — tangent arcs, no RF signal vias', '#edb95c')
    fig.tight_layout(); fig.savefig(out/'RF_saved_bottom.png'); plt.close(fig)
    manifest = dict(native_sha256=audit['native_sha256'], candidate_sha256=audit['candidate_sha256'],
                    source='Saved native copper snapshot with separately audited candidate via geometry',
                    files=[dict(path=str(p), sha256=digest(p)) for p in
                           (out/'DC_saved_two_layers.png', out/'RF_saved_bottom.png')])
    (out/'image_sources.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
