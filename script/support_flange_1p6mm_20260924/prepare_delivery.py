"""Prepare revision D delivery with the final 1.6 mm clearance-hole supports."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent;R=H.parents[1]
M=R/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
source=(H.parent/'cnc_drawings_20260922/package_dwg.py').read_text(encoding='utf-8').replace('RevB','RevD').replace('Rev B','Rev D')
addition='''
## Final support flange revision - 2026-09-24

Both outer rod-contact flanges are 1.60 mm thick with full-thickness C1.6 x 45-degree outer bevels. The central deck remains 4 mm thick. The rod mating plane, full rod contact footprints, 8.5 mm mounting drop, boss and device placement are unchanged.

The four rod fastener holes in each support remain plain diameter 3.4 mm through holes; no support-flange thread features are present. The user cancelled flange threading after confirming that the reference rods already specify M3 through threads. The existing eight Content Center ISO 4762 M3x8 screws retain their insertion direction through the support into the rod, with heads reseated at global Z=-1.6 mm. The rods and supplied hardware are unchanged. With the provisional 6 mm rod depth, the screw tips project 0.4 mm beyond the rods. No washers are used.

The C1.6 bevel leaves 67.11% of the actual flat under-head bearing area supported (10.546 of 15.716 mm2 per rod screw). Geometry checks do not constitute preload or structural qualification. Existing reference-part/sleeve intersections and tiny device under-head fillet intersections remain recorded in the full assembly report.

The PCB pocket-floor centre plus 0.300 mm toward the cavity opening is at X=25.500, Z=3.000 mm, matching the cylinder axis. Calculated nominal radial residual is below 0.001 mm; the unrounded CAD value is recorded in geometry_verification.json. Cylinder_top_1p6mm.png is a literal native axial view; Cylinder_centre_1p6mm.png is a STEP-derived section exposing the pocket reference point hidden behind the crossbars in that view.

Validation: independent saved support IPT copies, one healthy solid per part, native C1.6 chamfer, four unchanged deck-joining M3x0.5-6H threads per support, and no added flange threads. STEP checks confirm the requested cut volume, 20,000 matching point classifications per part, rod contact and screw seating. All six Rev D DWGs reopen with 46 attached dimensions. Previous revision drawing/ZIP files outside this package are superseded and must not be paired with current models.
'''
needle="(OUT / 'README.md').write_text(readme,encoding='utf-8')"
source=source.replace(needle,'readme += '+repr(addition)+'\n'+needle)
source=source.replace("assert 'SECTION C-C' in reader.pages[4].extract_text()", "assert 'SECTION C-C' in reader.pages[4].extract_text()\nfor page in reader.pages[2:4]:\n    assert 'C1.6 X 45 DEG - OUTER EDGE' in page.extract_text()\n    assert 'THROUGH 1.60 FLANGE' in page.extract_text()")
source=source.replace("archive = MODEL / 'QSTL_Plate_DWG_Package_RevD.zip'", "files += [MODEL / 'support_flange_1p6mm_validation.json', MODEL / 'support_native_reopen.json', OUT / 'Split_Mount_Plate_Only.step']\narchive = MODEL / 'QSTL_Plate_DWG_Package_RevD.zip'")
(H/'package_dwg.py').write_text(source,encoding='utf-8')
p=M/'README.md';s=p.read_text(encoding='utf-8').split('\n## Support flange revision')[0].rstrip()+'\n'
s=s.replace('RevC.zip','RevD.zip').replace('2 mm outer flanges and C2 x 45-degree','1.6 mm outer flanges and C1.6 x 45-degree').replace('support_flange_2mm_20260924','support_flange_1p6mm_20260924')
p.write_text(s+addition,encoding='utf-8')
p=M/'variant_plan.json';v=json.loads(p.read_text(encoding='utf-8-sig'))
v.update(rod_flanges_z_mm=[-1.6,0],rod_flange_thickness_mm=1.6,rod_flange_outer_chamfer_mm=1.6,rod_flange_outer_chamfer_angle_deg=45,rod_fastener_holes='8 plain diameter 3.4 mm through; no support flange threads',rod_fasteners='8 unmodified Inventor Content Center ISO 4762 M3x8, original insertion direction',rod_screw_tip_projection_mm=.4,deck_join_screws='8 unmodified Inventor Content Center DIN 7991 M3x10',current_drawing_revision='D')
p.write_text(json.dumps(v,indent=2),encoding='utf-8')
(H/'README.md').write_text('''# Support flange 1.6 mm - final revision D

Final user requirements: 1.6 mm rod-contact flanges, full-thickness 45-degree outer bevels (C1.6), plain diameter 3.4 mm mounting holes, original M3 threaded rods and original fastener insertion direction. Flange threading was explicitly cancelled. The central deck remains 4 mm. Preserve the central pocket-reference alignment.

`apply_supports.ps1` updates native supports, eight screw seating transforms, STEP exports and assemblies. Its `before/` snapshot contains the prior 2 mm revision. Do not overwrite that baseline. `set_final_thickness.py` and `prepare_checks.py` are one-time helper preparation records, not regeneration commands.

Run `read_pocket_placement.ps1` to read nested saved transforms, then `verify_assembly.py`, `verify_flange.py` and `verify_native_saved.ps1`. They check valid solids, exact parameter values, native thread absence at flange holes, retained deck threads, protected part hashes, flange geometry, screw seating, actual contact/interference and pocket-reference alignment. The full model has 24 occurrences. The pocket reference is 0.300 mm from the milling floor toward its opening, not the carrier bounding-box centre.

`render_native.ps1` exports the literal cylinder axial view and the support end view. `verify_assembly.py` also makes the labelled STEP section through the pocket, whose centre can be obscured by crossbars in the literal native view.

`build_dwg.ps1` and `verify_dwg.ps1` update/reopen the six native Rev D DWGs (five A3 sheets, 46 associated dimensions). Render and inspect the PDF companion. Run `prepare_delivery.py`, then `package_dwg.py` to produce the current Rev D plate-only drawing package. Keep previous revision ZIPs historical.

The unchanged M3x8 rod screws now project 0.4 mm beyond the provisional 6 mm rods. Their flat head-bearing contact is 67.11%. Existing reference sleeve and tiny device screw fillet/slot intersections remain reported; do not assert that the complete installation is interference-free. No washers, shortened hand-built screws or unrequested reference-part edits were introduced.
''',encoding='utf-8')
print('Prepared revision D packaging and final English requirements/model records.')
