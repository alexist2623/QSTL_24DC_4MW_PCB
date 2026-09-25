"""Prepare measured DC ground-pour geometry while native Altium is unavailable.

This script reads the original PCB, writes only plans/previews, and does not
represent the preview as a native repour or a manufacturing output.
"""
from pathlib import Path
import sys, json, struct, math
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, LineString, Polygon, box, mapping
from shapely.ops import unary_union
from shapely.affinity import rotate, translate

H = Path(__file__).resolve().parent
R = H.parents[1]
P = R / 'QSTL_24DC_4MW_PCB'
W = H.parent / '_support'
sys.path[:0] = [str(W / x) for x in (
    'qd_center_revision', 'final_routing/schematic', 'zif_revision_v2/board',
    'rf_revision', 'route_python')]
from native_metadata_helpers import properties, pads_stream, UNIT, sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route, read_regions, read_rules
from geometry_helpers import Arc, copper_geometry

source = P / 'QSTL_24DC_4MW_PCB.PcbDoc'
saved_mode = '--saved' in sys.argv
s = snapshot(source)
nets = properties(s['Nets6/Data'])
components = properties(s['Components6/Data'])
pads = pads_stream(s['Pads6/Data'])
tracks, arcs, vias = read_route(s, nets)
regions = read_regions(s['Regions6/Data'])
polygons = properties(s['Polygons6/Data'])
rules = read_rules(s['Rules6/Data'])
gnd = next(i for i, n in enumerate(nets) if n['NAME'] == 'GND')

def net_index(r):
    n = r['net_index']
    return int(polygons[r['polygon_index']]['NET']) if n == 65535 and r['polygon_index'] != 65535 else n

def pad_shape(p, layer):
    x, y = [c * UNIT for c in p['coords'][:2]]
    offset = 2 if layer == 1 else 6 if layer == 32 else 4
    sx, sy = [c * UNIT for c in p['coords'][offset:offset + 2]]
    if p['layer'] == 74:
        assert abs(sx - sy) < 4 * UNIT
        return Point(x, y).buffer(sx / 2, quad_segs=128)
    return translate(rotate(box(-sx/2, -sy/2, sx/2, sy/2), p['rotation'], origin=(0, 0)), x, y)

reference = unary_union([r['geometry'] for r in regions if r['layer'] == 3 and net_index(r) == gnd])
assert reference.is_valid
assert len(polygons) == (6 if saved_mode else 4)
assert any(p['LAYER'] == 'MID1' for p in polygons) == saved_mode
assert any(p['LAYER'] == 'MID3' for p in polygons) == saved_mode
keep = box(7.4, 40.15, 12.1, 44.85)
plan = dict(status='SAVED_NATIVE_POUR' if saved_mode else 'PREVIEW_ONLY_NATIVE_APPLICATION_PENDING', pcb_sha256=sha(source),
            clearance_mm=0.20 if saved_mode else 0.15, unchanged_source=True, layers={},
            clearance_rules=[r for r in rules if r.get('RULEKIND') == 'Clearance'])
geometries = {}
for layer in (2, 4):
    signals = []
    for t in tracks:
        if t['layer'] == layer and t['net'] != 'GND':
            signals.append(LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).buffer(t['width']/2, quad_segs=64))
    for a in arcs:
        if a['layer'] == layer and a['net'] != 'GND':
            signals.append(copper_geometry(Arc((a['cx'], a['cy']), a['radius'], a['start_angle'],
                (a['end_angle']-a['start_angle']) % 360, layer, a['width'], a['net']), 0.000001))
    for p in pads:
        if p['layer'] in (74, layer) and p['net'] != gnd:
            signals.append(pad_shape(p, layer))
    for v in vias:
        if v['net'] != 'GND':
            assert tuple(sorted(v['body'][29:31])) == (1, 32)
            signals.append(Point(v['x'], v['y']).buffer(v['diameter']/2, quad_segs=128))
    signal = unary_union(signals)
    # The adjacent saved plane supplies the unchanged outline, through-hole
    # clearances and SMP thermal connections. Cutouts already apply on all
    # internal layers. Recut signal clearances conservatively by one grid unit.
    candidate = (unary_union([r['geometry'] for r in regions if r['layer'] == layer and net_index(r) == gnd])
        if saved_mode else reference.difference(signal.buffer(0.15 + 2*UNIT, quad_segs=128)).difference(keep))
    anchors = unary_union([pad_shape(p, layer) for p in pads if p['layer'] == 74 and p['net'] == gnd])
    pieces = list(candidate.geoms) if candidate.geom_type == 'MultiPolygon' else [candidate]
    retained = [p for p in pieces if p.intersection(anchors).area > 1e-6]
    dropped = [p for p in pieces if p.intersection(anchors).area <= 1e-6]
    if saved_mode:
        assert not dropped, ('Floating ground regions', layer, [p.area for p in dropped])
    ground = candidate if saved_mode else unary_union(retained)
    assert ground.is_valid and not ground.is_empty
    assert ground.distance(signal) >= plan['clearance_mm'] - 4*UNIT
    # Native coordinates are quantized to 2.54 nm. Check the protected interior
    # with the same six-coordinate-unit tolerance used by the saved-file audit.
    assert ground.intersection(keep.buffer(-6*UNIT)).area < 1e-10
    geometries[layer] = ground
    plan['layers'][str(layer)] = dict(ground_area_mm2=ground.area,
        grounded_regions=len(retained), removed_islands=len(dropped),
        removed_island_area_mm2=sum(p.area for p in dropped),
        minimum_signal_clearance_mm=ground.distance(signal),
        QD_excluded_ground_area_mm2=ground.intersection(keep).area,
        QD_excluded_interior_ground_area_mm2=ground.intersection(keep.buffer(-6*UNIT)).area,
        geometry=mapping(ground))

(H/('saved_ground_geometry.json' if saved_mode else 'pour_preview_plan.json')).write_text(json.dumps(plan, indent=2), encoding='utf-8')
font = lambda sz: ImageFont.truetype('C:/Windows/Fonts/arial.ttf', sz)
bg, board, ground_color = '#101923', '#263642', '#b29242'
dc_colors = {2:'#5be9ef', 4:'#ff92cd'}
im = Image.new('RGB', (1310, 1950), bg)
d = ImageDraw.Draw(im)
d.text((35, 25), 'DC LAYERS | GND COPPER POUR' + ('' if saved_mode else ' PREVIEW'), font=font(34), fill='white')
d.text((35, 80), 'Rendered from saved Altium PCB copper geometry' if saved_mode else 'PREVIEW ONLY - Altium application and native DRC pending', font=font(23), fill='#b4c2cd' if saved_mode else '#ffc985')
d.text((35, 118), f'Signal clearance {plan["clearance_mm"]:.2f} mm | QD exclusion retained | Unconnected islands removed', font=font(20), fill='#b4c2cd')

def draw_layer(layer, origin, scale, bounds):
    x0, y0, x1, y1 = bounds
    ox, oy = origin
    xy = lambda x, y: (ox + (x-x0)*scale, oy + (y1-y)*scale)
    d.rectangle((ox, oy, ox+(x1-x0)*scale, oy+(y1-y0)*scale), fill=board, outline='#718693', width=2)
    def poly(g, color):
        if g.is_empty: return
        for piece in list(g.geoms) if hasattr(g, 'geoms') else [g]:
            if piece.geom_type != 'Polygon': continue
            d.polygon([xy(*p) for p in piece.exterior.coords], fill=color)
            for ring in piece.interiors:
                d.polygon([xy(*p) for p in ring.coords], fill=board)
    poly(geometries[layer].intersection(box(*bounds)), ground_color)
    for t in tracks:
        if t['layer'] != layer: continue
        g = LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2, quad_segs=32)
        poly(g.intersection(box(*bounds)), dc_colors[layer])
    for p in pads:
        if p['layer'] not in (layer, 74): continue
        poly(pad_shape(p, layer).intersection(box(*bounds)), ground_color if p['net']==gnd else '#d4dbe1')
        if p['coords'][8]:
            x,y=[c*UNIT for c in p['coords'][:2]];hole=p['coords'][8]*UNIT/2
            poly(Point(x,y).buffer(hole,quad_segs=64).intersection(box(*bounds)), bg)
    for v in vias:
        if v['net']=='GND': continue  # L5-L6 shields do not penetrate DC layers.
        for r,col in ((v['diameter']/2,dc_colors[layer]),(v['hole']/2,bg)):
            poly(Point(v['x'],v['y']).buffer(r,quad_segs=32).intersection(box(*bounds)), col)
    if y1>44.85 and y0<40.15:
        d.rectangle((*xy(7.4,44.85),*xy(12.1,40.15)), outline='#e7edf0', width=2)
        d.text(xy(9.75,42.5),'QD',font=font(20),fill='white',anchor='mm')

for i, layer in enumerate((2, 4)):
    ox = 47+i*650
    d.text((ox,175), f'L{layer} DC_{"A" if layer==2 else "B"} + GND', font=font(26), fill=dc_colors[layer])
    draw_layer(layer,(ox,220),24,(0,0,19.5,67.9))
    item=plan['layers'][str(layer)]
    d.text((ox,1880),f'GND {item["ground_area_mm2"]:.1f} mm2 | 12 DC nets',font=font(20),fill='#d5dde2')
d.text((40,1920),'PCB '+plan['pcb_sha256'][:24]+' | Top-view coordinates' + ('' if saved_mode else ' | Native file unchanged'),font=font(17),fill='#9bafbc')
image_path = (P/'docs/DC_GND_pour.png') if saved_mode else (H/'DC_GND_pour_preview.png')
im.save(image_path)
print(json.dumps({k:v for k,v in plan.items() if k not in ('layers','clearance_rules')} | {
    'layers':{k:{a:b for a,b in v.items() if a!='geometry'} for k,v in plan['layers'].items()},
    'clearance_rules':plan['clearance_rules'], 'image':str(image_path)},indent=2))
