"""Publish an English mask review and update the repository's current-state notes."""
from pathlib import Path
import json, sys, importlib.util, html
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

H = Path(__file__).resolve().parent
R = H.parents[1]
P = R / 'QSTL_24DC_4MW_PCB'
D = P / 'docs'
W = H.parent / '_support'
sys.path[:0] = [str(W / x) for x in ('qd_center_revision', 'final_routing/schematic', 'zif_revision_v2/board', 'rf_revision', 'route_python')]
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
spec = importlib.util.spec_from_file_location('native_mask_reader', W / 'zif_revision_v2/render_native_layout.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
reader.SOURCE = P / 'QSTL_24DC_4MW_PCB.PcbDoc'
n = reader.read_native()
regions = read_regions(snapshot(reader.SOURCE)['Regions6/Data'])
report = json.loads((D / 'mask_ground_validation.json').read_text())
assert report['passed'] and report['pcb_sha256'] == n['source_sha256']

im = Image.new('RGB', (1120, 1140), '#f4f6f8')
draw = ImageDraw.Draw(im)
font_path = 'C:/Windows/Fonts/arial.ttf'
font = ImageFont.truetype(font_path, 18)
small = ImageFont.truetype(font_path, 15)
heading = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 29)
draw.text((35, 24), 'Solder mask and paste review', font=heading, fill='#172333')
draw.text((35, 64), 'Saved original PCB | 19.5 x 67.9 mm | All views use Top coordinates', font=font, fill='#455468')
scale = 11.6
board = box(0, 0, 19.5, 67.9)
labels = ['Top: solder mask', 'Bottom: solder mask', 'Top: paste', 'Bottom: paste']

def xy(x, y, x0):
    return (x0 + x * scale, 139 + (67.9 - y) * scale)

def polygon(g, x0, color, hole_color=None):
    if g.is_empty:
        return
    for p in (g.geoms if hasattr(g, 'geoms') else [g]):
        if not isinstance(p, Polygon):
            continue
        draw.polygon([xy(x, y, x0) for x, y in p.exterior.coords], fill=color)
        if hole_color:
            for ring in p.interiors:
                draw.polygon([xy(x, y, x0) for x, y in ring.coords], fill=hole_color)

for col, label in enumerate(labels):
    x0 = 35 + 270 * col
    draw.text((x0, 106), label, font=font, fill='#172333')
    is_mask = col < 2
    polygon(board, x0, '#4b8857' if is_mask else '#293547')
    if is_mask:
        opening = unary_union([r['geometry'] for r in regions if r['layer'] == 37 + col])
        polygon(opening.intersection(board), x0, '#e2e5e9', '#4b8857')
    for p in n['pads']:
        if not (p['layer'] == 74 or p['layer'] == (1 if col in (0, 2) else 32)):
            continue
        if not is_mask and (p['component'] is None or p['component'].startswith('SMP')):
            continue
        if p['shape'] == 1 and abs(p['size_x'] - p['size_y']) < 1e-5:
            g = Point(p['x'], p['y']).buffer(p['size_x'] / 2, quad_segs=24)
        else:
            g = Polygon(reader.corners(p['x'], p['y'], p['size_x'], p['size_y'], p['rotation']))
        if is_mask and p['layer'] == 74:
            g = g.buffer(.05)
        polygon(g, x0, '#d5ad4d' if is_mask else '#f36caf')
    if is_mask:
        draw.rectangle([xy(7.6, 44.65, x0), xy(11.9, 40.35, x0)], outline='#ef694e', width=2)
    draw.rectangle([xy(0, 67.9, x0), xy(19.5, 0, x0)], outline='#182330', width=2)

notes = [
    'Green: retained solder mask. Light grey: general mask opening. Gold: normal pad openings.',
    'Pink: normal SMD paste. No SMP or mounting-pad paste; no separate via paste apertures.',
    'Red boundary: QD inner pad-end square, 4.3 x 4.3 mm. Top GND retained; all other layers excluded.',
    'RF copper retains a minimum 0.25 mm mask margin outside normal pad openings.',
    'Native geometry audit: 37 connected nets, 0 connection lines, 0 violations across 13 DRC rules.',
    'Mask/stencil geometry diagram; component bodies, drill holes and internal routing are omitted.'
]
for i, line in enumerate(notes):
    draw.text((35, 948 + i * 27), line, font=small, fill='#26364a')
im.save(D / 'mask_paste_review.png')

readme = R / 'README.md'
text = readme.read_text(encoding='utf-8')
text = text.replace('All retain Top/Bottom via tent flags and 144 explicit paste apertures. Via-in-pad holes share the component pad\'s Bottom mask opening. Three GND polygons occupy L1/L3/L5.', 'All retain Top/Bottom via tent flags. The former 144 via-specific paste apertures are removed; paste is disabled on all 40 SMP pads and six mounting pads. Normal paste on the 101 SMD pads remains. Via-in-pad holes share the component pad\'s Bottom mask opening. Three GND polygons occupy L1/L3/L5.')
text = text.replace('## Preserved geometry and validation', '''## Solder mask, paste and QD ground

General Top/Bottom areas have explicit solder-mask openings. Solder-control mask remains around QD, R/C, ZIF fanout, SMP and mounting lands, with their normal pad openings preserved. Bottom RF routes retain at least 0.25 mm of mask margin from the copper edge. Removing SMP/mechanical **paste** does not remove their solder mask.

The QD inner pad-end square, x=7.6-11.9 mm and y=40.35-44.65 mm, is GND-free on L2/L3/L4/L5/Bottom using five persistent polygon cutouts. Top GND is preserved. This is a copper exclusion, not a board cutout. RF/DC routes, components, pads, via geometry, schematic and library files are unchanged by this mask/ground update.

[Mask and paste review](QSTL_24DC_4MW_PCB/docs/mask_paste_review.png) | [Mask/ground audit](QSTL_24DC_4MW_PCB/docs/mask_ground_validation.json) | [Native paste flags](QSTL_24DC_4MW_PCB/docs/native_paste_audit.txt)

## Preserved geometry and validation''') if '## Solder mask, paste and QD ground' not in text else text
text = text.replace('[Current DRC](QSTL_24DC_4MW_PCB/docs/RF6_DRC.html)', '[Current DRC](QSTL_24DC_4MW_PCB/docs/Mask_Ground_DRC.html)')
text = text.replace('Earlier symmetry, resizing, surface-stack DRC and comparison artifacts are historical. Current reports listed above contain the current board\'s SHA-256; check that hash before reusing results after edits.', 'The current saved-board reports are validation.json, mask_ground_validation.json, connection_validation.json, schematic_validation.json and Mask_Ground_DRC.html. Earlier RF/DC/model reports and routing-only previews retain their revision hashes; the latest audit verifies their routing and component geometry was preserved. Check revision hashes before reusing reports after edits.')
readme.write_text(text, encoding='utf-8')
(H / 'README.md').write_text('''# Mask, paste and QD ground update

This phase edits the original project only. All helper code and audit outputs stay under the repository. Read `../../AGENTS.md` and the project design requirements before any replay.

- `prepare_change.py` and `ApplyMaskGround.pas` prepare/apply the two general solder openings, removal of the 144 explicit via paste regions, and five QD copper-pour cutouts. The source-hash and existing-object guards prevent replay on an already modified board.
- `DisablePaste.pas` is the required follow-up: it explicitly disables both paste faces of all SMP/mounting pads and clears interim expansion values. `GetState_IsTopPasteEnabled` and `GetState_IsBottomPasteEnabled` persist for pads.
- The generic via `PasteMaskEnabled` property does not persist as a disabled flag in this Altium version. Vias have no native pad-style paste aperture; the former explicit paste regions are removed. Normal SMD pad paste coincident with via-in-pad remains intentionally present.
- `ProbePaste.pas`, `ProbeRegion.pas` and `ProbeMaskPresence.pas` are API research probes, not production steps. The last probe cannot call `HasMaskExpansion` through the scripting layer and is not validation evidence.
- `ReopenAudit.pas` saves no new geometry; it closes/reopens the saved board, counts connection lines and runs all 13 enabled DRC rules. `AuditPaste.pas` reads native pad paste/solder properties after reopening.
- `verify_mask_ground.py` compares the saved board with `before.PcbDoc`, checking masks, pad paste, RF clearance, GND exclusion, preserved design files and connectivity. A four-native-unit coordinate tolerance handles contour quantization at the QD boundary.
- `verify_design.py` reruns the complete prior routing/schematic audit with the new paste requirement and current DRC report. It does not weaken routing or schematic checks.
- `publish_reports.py` renders the native mask/stencil review and updates the current-state documentation.

Final saved-board SHA-256: `'''+report['pcb_sha256']+'''`.
''', encoding='utf-8')
print(json.dumps(dict(review=str(D / 'mask_paste_review.png'), hash=report['pcb_sha256'])))
