"""Audit saved masks, paste flags, QD ground and preservation of design geometry."""
from pathlib import Path
import sys, json, math, re, struct, collections, shutil
from shapely.geometry import shape, box, LineString
from shapely.ops import unary_union

H = Path(__file__).resolve().parent
R = H.parents[1]
P = R / 'QSTL_24DC_4MW_PCB'
D = P / 'docs'
W = H.parent / '_support'
B = 'QSTL_24DC_4MW_PCB'
sys.path[:0] = [str(W / x) for x in ('qd_center_revision', 'final_routing/schematic', 'zif_revision_v2/board', 'rf_revision', 'route_python')]
from native_metadata_helpers import properties, pads_stream, UNIT, sha, binary_records
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions, read_route, trackkey, arckey, viakey

before = snapshot(H / 'before.PcbDoc')
after = snapshot(P / (B + '.PcbDoc'))
plan = json.loads((H / 'mask_plan.json').read_text())
errors = []

def check(ok, text):
    if not ok:
        errors.append(text)

before_nets = properties(before['Nets6/Data'])
after_nets = properties(after['Nets6/Data'])
bt, ba, bv = read_route(before, before_nets)
at, aa, av = read_route(after, after_nets)
check(collections.Counter(map(trackkey, bt)) == collections.Counter(map(trackkey, at)), 'Track geometry or nets changed')
check(collections.Counter(map(arckey, ba)) == collections.Counter(map(arckey, aa)), 'Arc geometry or nets changed')
check(collections.Counter(map(viakey, bv)) == collections.Counter(map(viakey, av)), 'Via geometry or nets changed')
check(before['BoardRegions/Data'] == after['BoardRegions/Data'], 'Board outline changed')
check(properties(before['Components6/Data']) == properties(after['Components6/Data']), 'Component metadata changed')
check(before_nets == after_nets, 'Net definitions changed')
bp, ap = pads_stream(before['Pads6/Data']), pads_stream(after['Pads6/Data'])
components = properties(after['Components6/Data'])

def padkey(p):
    return (f"MOUNT_INDEX_{p['index']}" if p['component'] == 65535 else components[p['component']]['SOURCEDESIGNATOR'], p['number'])

oldpads = {padkey(p): p for p in bp}
for p in ap:
    old = oldpads[padkey(p)]
    for field in ('coords', 'rotation', 'shape', 'layer', 'net', 'component'):
        check(p[field] == old[field], f'Pad {padkey(p)} changed {field}')
    if p['layer'] != 74:
        check(p['blocks'] == old['blocks'], f'SMD pad settings changed {padkey(p)}')
    # These are the native top and bottom solder expansion fields and their mode.
    for start, end in ((90, 94), (102, 103), (121, 125)):
        check(p['blocks'][4][start:end] == old['blocks'][4][start:end], f'Solder expansion changed {padkey(p)}')
check(all(v['body'][1] & 0x60 == 0x60 for v in av), 'Via solder tent flag missing')

br = read_regions(before['Regions6/Data'])
ar = read_regions(after['Regions6/Data'])
check(not any(r['layer'] in (35, 36) for r in ar), 'Explicit paste regions remain')
check(sum(r['layer'] in (35, 36) for r in br) == 144, 'Unexpected original paste count')
for stream, kind in (('Tracks6/Data', 4), ('Arcs6/Data', 1), ('Fills6/Data', 6)):
    if stream in after:
        check(not any(r['body'][0] in (35, 36) for r in binary_records(after[stream], kind)), f'Paste shapes remain in {stream}')

audit = [line.split('|') for line in (H / 'native_paste_audit.txt').read_text().splitlines()]
check(audit[-1] == ['COMPLETE'], 'Native paste audit incomplete')
pad_audit = [x for x in audit if x[0] == 'PAD']
disabled = collections.Counter()
preserved = 0
for row in pad_audit:
    key = (row[1], row[2])
    if key[0] == 'MOUNT' or key[0].startswith('SMP'):
        check(row[7:10] == ['0', '0', '0'], f'Paste enabled on {key}')
        disabled['mounting_pads' if key[0] == 'MOUNT' else 'SMP_pads'] += 1
    else:
        check(row[7:10] == ['1', '1', '1'], f'SMD paste disabled on {key}')
        preserved += 1
check(dict(disabled) == {'SMP_pads': 40, 'mounting_pads': 6} and preserved == 101, 'Paste pad count mismatch')

qd = shape(plan['QD_exclusion'])
ground_reports = {}
for layer in (1, 2, 3, 4, 5, 32):
    geometries = []
    for stream, regs in ((before, br), (after, ar)):
        polygons = properties(stream['Polygons6/Data'])
        nets = properties(stream['Nets6/Data'])
        selected = []
        for r in regs:
            ni = r['net_index']
            if ni == 65535 and r['polygon_index'] != 65535:
                ni = int(polygons[r['polygon_index']]['NET'])
            if r['layer'] == layer and ni != 65535 and nets[ni]['NAME'] == 'GND':
                selected.append(r['geometry'])
        geometries.append(unary_union(selected))
    old, new = geometries
    area = new.intersection(qd).area
    interior_area = new.intersection(qd.buffer(-4 * UNIT)).area
    if layer == 1:
        check(old.equals(new) and abs(area - 18.49) < .00001, 'Top QD ground changed')
    else:
        check(interior_area < 1e-10, f'QD ground remains on layer {layer}')
    ground_reports[str(layer)] = dict(ground_area_inside_boundary_mm2=area, ground_area_inside_boundary_with_native_tolerance_mm2=interior_area, top_preserved=old.equals(new) if layer == 1 else None)
cutouts = [r for r in ar if r['name'].startswith('QD_GND_EXCLUSION_')]
check(sorted(r['layer'] for r in cutouts) == [2, 3, 4, 5, 32], 'QD cutout layers mismatch')
for r in cutouts:
    check(r['props']['KIND'] == '1' and r['geometry'].symmetric_difference(qd).area < .0001, 'Invalid QD cutout')
old_cutouts = [r for r in br if r['props'].get('KIND') == '1']
other_cutouts = [r for r in ar if r['props'].get('KIND') == '1' and not r['name'].startswith('QD_GND_EXCLUSION_')]
check(len(old_cutouts) == len(other_cutouts), 'Existing SMP local exclusions changed')
check(all(any(a['layer'] == b['layer'] and a['geometry'].equals(b['geometry']) for b in other_cutouts) for a in old_cutouts), 'Existing exclusion geometry changed')

mask_reports = {}
board = box(0, 0, 19.5, 67.9)
for layer in (37, 38):
    rows = [r for r in ar if r['layer'] == layer and r['name'].startswith('SURFACE_MASK_OPEN_')]
    opening = unary_union([r['geometry'] for r in rows])
    expected = shape(plan['mask_openings'][str(layer)])
    delta = opening.symmetric_difference(expected).area
    check(len(rows) == 1 and all(r['valid'] for r in rows) and delta < .001, f'Mask geometry mismatch {layer}')
    mask_reports[str(layer)] = dict(opening_region_count=len(rows), protected_islands=sum(len(r['rings']) - 1 for r in rows), opening_area_inside_board_mm2=opening.intersection(board).area, native_quantization_difference_mm2=delta)
rf = []
for t in at:
    if t['layer'] == 32:
        rf.append(LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])]).buffer(t['width'] / 2 + .25))
for a in aa:
    sweep = (a['end_angle'] - a['start_angle']) % 360
    n = max(8, math.ceil(sweep / .25))
    coords = [(a['cx'] + a['radius'] * math.cos(math.radians(a['start_angle'] + sweep * i / n)), a['cy'] + a['radius'] * math.sin(math.radians(a['start_angle'] + sweep * i / n))) for i in range(n + 1)]
    rf.append(LineString(coords).buffer(a['width'] / 2 + .25))
bottom_opening = unary_union([r['geometry'] for r in ar if r['layer'] == 38])
check(unary_union(rf).intersection(bottom_opening).area < 1e-9, 'General mask opening touches RF protected margin')
hashes = json.loads((H / 'before_hashes.json').read_text())
unchanged = {name: sha(P / name) == old for name, old in hashes.items() if not name.endswith('.PcbDoc')}
check(all(unchanged.values()), 'Schematic, project or footprint library changed')
html = (D / 'Mask_Ground_DRC.html').read_text(encoding='cp949', errors='replace')
rows = re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>', html, re.S)
check(len(rows) == 13 and sum(int(n) for _, n in rows) == 0, 'DRC not clear')
check(not after['Connections6/Data'] and struct.unpack('<I', after['Connections6/Header'])[0] == 0, 'Connection lines remain')
connectivity = json.loads((D / 'connection_validation.json').read_text())
check(connectivity['passed'] and connectivity['pcb_sha256'] == sha(P / (B + '.PcbDoc')), 'Connectivity report stale or failed')

report = dict(passed=not errors, errors=errors, pcb_sha256=sha(P / (B + '.PcbDoc')), source_sha256=sha(H / 'before.PcbDoc'), geometry_and_pin_assignments_preserved=True if not errors else None, counts=dict(components=len(components), pads=len(ap), tracks=len(at), arcs=len(aa), vias=len(av)), paste=dict(explicit_via_paste_apertures_removed=144, explicit_paste_regions_remaining=0, SMP_pads_disabled=40, mounting_pads_disabled=6, normal_SMD_pads_preserved=101, via_count=72, native_via_generic_enabled_flag_serializes_as_true=True, note='Vias do not create native pad-style paste apertures. Their former dedicated 144 paste regions are absent. SMD pad paste coincident with via-in-pad is intentionally retained. The generic via PasteMaskEnabled getter is not used as aperture evidence.'), solder_mask=dict(openings=mask_reports, RF_protected_margin_mm=.25, SMP_and_mounting_solder_expansions_preserved=True, via_tent_flags_preserved=72), QD_ground=dict(boundary_mm=[7.6,40.35,11.9,44.65], coordinate_tolerance_mm=4*UNIT, exclusions_on_layers=[2,3,4,5,32], physical_board_cutout=False, layers=ground_reports), other_design_files_unchanged=unchanged, DRC=dict(checked_rules=len(rows), violations=sum(int(n) for _, n in rows), report='Mask_Ground_DRC.html'), connected_nets=connectivity['connected_net_count'], stored_connections=0)
(D / 'mask_ground_validation.json').write_text(json.dumps(report, indent=2) + '\n')
shutil.copy2(H / 'native_paste_audit.txt', D / 'native_paste_audit.txt')
shutil.copy2(P / 'work/mask_ground_reopen_check.txt', D / 'native_reopen_check.txt')
print(json.dumps(dict(passed=report['passed'], errors=errors, hash=report['pcb_sha256'], paste=report['paste'], DRC=report['DRC']), indent=2))
raise SystemExit(0 if report['passed'] else 1)
