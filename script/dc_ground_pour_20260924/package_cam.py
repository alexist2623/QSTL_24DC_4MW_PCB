"""Validate fresh native CAM after DC-layer ground pour and package fabrication files."""
from pathlib import Path
import collections, hashlib, json, math, re, shutil, sys, zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Arc
from gerbonara import GerberFile, ExcellonFile
from gerbonara.utils import MM
from shapely.geometry import Polygon
from shapely.ops import unary_union

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
P = ROOT / 'QSTL_24DC_4MW_PCB'
F = P / 'fabrication/JLCPCB_HDI_20260924'
CAM = F / 'Native_CAM'
PKG = F / 'Gerber'
PKG.mkdir(parents=True, exist_ok=True)
W = H.parent / '_support'
sys.path[:0] = [str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision')]
from native_metadata_helpers import properties, sha, pads_stream, UNIT
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route, read_regions

board = P/'QSTL_24DC_4MW_PCB.PcbDoc'
validation = json.loads((H/'validation.json').read_text())
assert validation['passed'] and not validation['errors']
assert sha(board) == validation['pcb_sha256']
schematic_sha = sha(P/'QSTL_24DC_4MW_PCB.SchDoc')
s = snapshot(board)
tracks, arcs, vias = read_route(s, properties(s['Nets6/Data']))
shields = [v for v in vias if v['net']=='GND']
through_vias = [v for v in vias if v['net']!='GND']
laser = ExcellonFile.open(CAM/'QSTL_24DC_4MW_PCB-Plated.TX1')
through = ExcellonFile.open(CAM/'QSTL_24DC_4MW_PCB-Plated.TXT')
assert len(laser.objects)==480 and len(through.objects)==94
assert all(abs(o.aperture.diameter-.1)<1e-8 for o in laser.objects)
laser_error = max(min(math.dist((o.x,o.y),(v['x'],v['y'])) for v in shields) for o in laser.objects)
assert laser_error < .000075
assert len({(o.x,o.y) for o in laser.objects}) == 480
assert all(min(math.dist((v['x'],v['y']),(o.x,o.y)) for o in through.objects)<.000075 for v in through_vias)
assert all(o.aperture.diameter>.1 for o in through.objects)
expected_holes = [(v['x'],v['y'],.25) for v in through_vias]
expected_holes += [(p['coords'][0]*UNIT,p['coords'][1]*UNIT,p['coords'][8]*UNIT)
                   for p in pads_stream(s['Pads6/Data']) if p['coords'][8]>0]
assert len(expected_holes)==len(through.objects)==94
through_error=max(min(math.dist((o.x,o.y),(x,y)) for x,y,d in expected_holes
                      if abs(d-o.aperture.diameter)<.00001) for o in through.objects)
assert through_error<.000075
assert len({(o.x,o.y) for o in through.objects})==94
for ext in ('GTL','G1','G2','G3','G4','GBL','GTO','GBO','GTS','GBS','GM','GM2','LDP','DRR','REP'):
    assert (CAM/f'QSTL_24DC_4MW_PCB.{ext}').stat().st_mtime > board.stat().st_mtime
for ext in ('TX1','TXT'):
    assert (CAM/f'QSTL_24DC_4MW_PCB-Plated.{ext}').stat().st_mtime > board.stat().st_mtime
ldp = (CAM/'QSTL_24DC_4MW_PCB.LDP').read_text()
assert 'DrillLayers=g4,gbl' in ldp and 'L5_GND_L6_RF_QD_Blind_Vias' in ldp

files = {}
ground_checks = {}
for ext in ('GTL','G1','G2','G3','G4','GBL','GTO','GBO','GTS','GBS','GM','GM2'):
    source = CAM/f'QSTL_24DC_4MW_PCB.{ext}'
    g = GerberFile.open(source)
    assert len(g.objects)>0
    name = 'bottom blind slots layer.gbr' if ext=='GM2' else f'QSTL_24DC_4MW_PCB.{"GKO" if ext=="GM" else ext}'
    shutil.copy2(source, PKG/name)
    files[name] = {'objects':len(g.objects),'bounds_mm':g.bounding_box(),'sha256':sha(source)}
    (F/f'{ext}.svg').write_text(str(g.to_svg()), encoding='utf-8')
    if ext in ('G1','G3'):
        layer=2 if ext=='G1' else 4
        native=unary_union([r['geometry'] for r in read_regions(s['Regions6/Data'])
                            if r['layer']==layer and r['polygon_index'] in (4,5)])
        actual=Polygon()
        for obj in g.objects:
            if type(obj).__name__!='Region':continue
            primitive=next(obj.to_primitives(unit=MM)).approximate_arcs(max_error=.0001)
            region=Polygon(primitive.outline).buffer(0)
            actual=actual.union(region) if obj.polarity_dark else actual.difference(region)
        missing=native.difference(actual.buffer(.0002)).area
        delta=native.symmetric_difference(actual).area
        ground_checks[ext]={'native_ground_mm2':native.area,'gerber_regions_mm2':actual.area,
                           'missing_ground_beyond_0p2um_mm2':missing,'symmetric_difference_mm2':delta}
        assert missing<.0001, ground_checks[ext]
        assert delta<.2, ground_checks[ext]
outline=GerberFile.open(CAM/'QSTL_24DC_4MW_PCB.GM')
assert len(outline.objects)==4
slot=GerberFile.open(CAM/'QSTL_24DC_4MW_PCB.GM2')
assert len(slot.objects)==8
assert all(abs(a-b)<.00001 for a,b in zip(sum(slot.bounding_box(),()),(7.595,40.345,11.905,44.655)))
for src,name in [('QSTL_24DC_4MW_PCB-Plated.TX1','L5-L6_Blind_Laser_0.1mm.drl'),('QSTL_24DC_4MW_PCB-Plated.TXT','L1-L6_PTH.drl')]:
    shutil.copy2(CAM/src,PKG/name)
for name in ('stackup.csv','QD_cavity_drawing.png'):
    shutil.copy2(P/'fabrication/RF50_QD_cavity'/name,PKG/name)
for name in ('QSTL_24DC_4MW_PCB.DRR','QSTL_24DC_4MW_PCB.LDP','QSTL_24DC_4MW_PCB.REP'):
    shutil.copy2(CAM/name,F/name)

fig = plt.figure(figsize=(12,9),facecolor='white')
ax=fig.add_axes([.03,.09,.42,.84]); ax.set_aspect('equal')
ax.add_patch(Rectangle((0,0),19.5,67.9,fill=False,color='black'))
rf=[t for t in tracks if t['layer']==32]
rf_arcs=[a for a in arcs if a['layer']==32]
for t in rf: ax.plot([t['x1'],t['x2']],[t['y1'],t['y2']],color='#175fa7',lw=1.4)
for a in rf_arcs: ax.add_patch(Arc((a['cx'],a['cy']),2*a['radius'],2*a['radius'],theta1=a['start_angle'],theta2=a['end_angle'],color='#175fa7',lw=1.4))
ax.scatter([v['x'] for v in shields],[v['y'] for v in shields],s=1.8,c='#168856',label='L6-L5 laser microvias')
ax.add_patch(Rectangle((7.6,40.35),4.3,4.3,fill=False,color='#c53f34',lw=1.4))
ax.set(xlim=(-1,20.5),ylim=(-1,69),xlabel='X (mm)',ylabel='Y (mm)',title='Bottom / L6 RF locations\nCommon top-view coordinates; not mirrored')
ax.grid(alpha=.15)
info='''CONTROLLED IMPEDANCE REQUIREMENT

Target: 50 ohm single-ended coplanar waveguide
Signal: L6 / Bottom / QD face
Reference: L5 GND
All blue tracks/arcs shown at left are RF.
Nominal trace width W: 0.110 mm
Coplanar copper gap G: 0.200 mm on both sides
Nominal L6-L5 dielectric: 0.0784 mm (1078)
Outer copper: 1 oz / 0.035 mm
Requested stack: JLCH06161HN1-1078
See stackup.csv for all six layers.

Please review the stack and 50-ohm geometry.
Confirm production files before manufacture.
Do not substitute a stack without confirmation.
RF trace locations must remain as supplied.

BLIND MICROVIAS
480 laser holes: diameter 0.100 mm
Copper land: diameter 0.250 mm
Span L6-L5 ONLY; filled and planarized.
No shield holes on L1-L4 or DC layers.
Separate drill: L5-L6_Blind_Laser_0.1mm.drl

BOTTOM NON-THROUGH MILLING
One non-plated pocket: 4.3 x 4.3 mm, R0.5
Depth: 1.20 mm from Bottom / L6
Center: X9.75, Y42.50 mm
Separate layer: bottom blind slots layer.gbr
Keep Top copper and the remaining floor intact.

Bare PCB only. No PCBA. No stencil.'''
fig.text(.43,.94,info,ha='left',va='top',fontsize=10,fontfamily='DejaVu Sans',linespacing=1.35)
fig.savefig(PKG/'Impedance_50ohm_and_HDI_requirements.jpg',dpi=180)
plt.close(fig)
(PKG/'FABRICATION_README.txt').write_text('''QSTL 24DC 6RF - JLCPCB HDI FABRICATION PACKAGE
Exported from the original saved Altium PCB on 2026-09-24.
Bare PCB only, no assembly or stencil.

LAYER MAP (all files use the same origin; no mirror)
GTL: L1 Top GND
G1: L2 DC A with GND copper pour
G2: L3 GND
G3: L4 DC B with GND copper pour
G4: L5 GND
GBL: L6 Bottom RF / QD
GTS / GBS: Top / Bottom solder mask
GTO / GBO: Top / Bottom silkscreen
GKO: 19.5 x 67.9 mm closed board outline only

L2/L4 GND-pour clearance to signal copper: nominal 0.20 mm.
DC traces, pin mapping and RF geometry are unchanged.

L1-L6_PTH.drl: 94 through plated holes (48 x 0.25 mm,
40 x 0.75 mm, 4 x 2.1 mm, 2 x 4.0 mm).
L5-L6_Blind_Laser_0.1mm.drl: 480 x 0.10 mm blind laser holes,
L6 to L5 ONLY, 0.25 mm copper lands. Filled and planarized.
Do NOT interpret these as through holes. No buried holes.
Excellon: metric, 4:4, leading zeros suppressed.

bottom blind slots layer.gbr: NON-PLATED blind pocket from Bottom,
4.3 x 4.3 mm, internal R0.50, depth 1.20 mm, centered X9.75 Y42.50.
Contour centerline defines finished pocket; 0.01 mm drawing stroke
is not a tool diameter. This is NOT a through-board cutout.
Keep Top copper and approximately 0.3884 mm remaining material.
See QD_cavity_drawing.png for machining side/location/depth.

50 ohm coplanar RF on L6 referenced to L5, W=0.110 mm, gap=0.200 mm.
Requested stack JLCH06161HN1-1078: 1 oz outer / 0.5 oz inner,
nominal 1.6 mm board; see stackup.csv and impedance requirement JPG.
The HDI order-page stack/inner-copper options require engineering
review if they differ from this requested dielectric/copper stack.
Confirm final stack, impedance compensation and production files.
Exposed QD pads are used for wire bonding; confirm surface-finish
suitability before production release. Quote interface finish is
a quotation assumption and does not approve bondability.
''',encoding='utf-8')
assert sha(board)==validation['pcb_sha256']
report={'passed':True,'pcb_sha256':sha(board),'schematic_sha256':schematic_sha,
        'outjob_sha256':sha(P/'HDI_Fabrication.OutJob'),'native_export':'Altium Designer 26.10.1',
        'all_CAM_newer_than_saved_PCB':True,'gerbers':files,'DC_ground_CAM_checks':ground_checks,
        'DC_ground_clearance_mm':validation['dc_ground_clearance_mm'],
        'blind_holes':480,'blind_span':['L5','L6'],'blind_drill_max_center_error_mm':laser_error,
        'through_holes':94,'through_drill_max_center_error_mm':through_error,
        'through_diameters':dict(collections.Counter(o.aperture.diameter for o in through.objects)),
        'saved_design_checks':{k:validation[k] for k in ('connectivity','mask_symmetric_difference_mm2','DRC','schematic_mapping_matches')},
        'pocket_mm':[4.3,4.3,1.2],'pocket_entry':'Bottom','pocket_non_through':True}
(F/'CAM_validation.json').write_text(json.dumps(report,indent=2)+'\n')
with zipfile.ZipFile(F/'QSTL_24DC_6RF_HDI_Gerber_20260924.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(PKG.iterdir()): z.write(p,p.name)
with zipfile.ZipFile(F/'QSTL_24DC_6RF_HDI_Gerber_20260924.zip') as z:
    assert z.testzip() is None and len(z.namelist())==18
print(json.dumps({k:v for k,v in report.items() if k not in ('gerbers','saved_design_checks')},indent=2))
print(F/'QSTL_24DC_6RF_HDI_Gerber_20260924.zip')
