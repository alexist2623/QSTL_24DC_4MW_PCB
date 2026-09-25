"""Prepare the current revision package script and update model documentation."""
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parents[1]
M=R/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
source=(H.parent/'cnc_drawings_20260922/package_dwg.py').read_text(encoding='utf-8')
source=source.replace('RevB','RevC').replace('Rev B','Rev C')
addition='''
## Support flange revision - 2026-09-24

Both outer rod-contact flanges are 2.00 mm thick, with full-thickness C2 x 45-degree bevels along their outer 80 mm edges. Their mating plane and rod contact footprints are unchanged. The central deck remains 4 mm thick; the 8.5 mm drop, boss, device reliefs and pocket-axis alignment are retained.

The full installation's eight existing ISO 4762 M3x8 rod screws move 2 mm toward the rods to seat on the new flange face. Their standard geometry is unchanged; no washers were added. The C2 bevel leaves 60.60% of each flat under-head bearing area in contact with the support (9.524 of 15.716 mm2). This is a geometric result, not structural or preload qualification. Rod screws and the reference rods are outside the plate-only drawing scope.

The independently reopened support IPTs retain one solid, a native chamfer feature and four M3x0.5-6H threads each. STEP validation checks the requested cut volume, 20,000 matching point classifications per part, bevel planes, unchanged rod-side planes, rod screw bearing contact and unchanged central plate/standard hardware hashes. The full assembly checks confirm unchanged device alignment and rod contact areas; pre-existing reference-part intersections remain documented separately.

The current deliverable is Rev C. Rev B files retained outside this package are superseded and must not be used with the changed support models.
'''
needle="(OUT / 'README.md').write_text(readme,encoding='utf-8')"
source=source.replace(needle,"readme += "+repr(addition)+"\n"+needle)
needle="archive = MODEL / 'QSTL_Plate_DWG_Package_RevC.zip'"
source=source.replace(needle,"files += [MODEL / 'support_flange_2mm_validation.json', MODEL / 'support_native_reopen.json', OUT / 'Split_Mount_Plate_Only.step']\n"+needle)
source=source.replace("assert 'SECTION C-C' in reader.pages[4].extract_text()", "assert 'SECTION C-C' in reader.pages[4].extract_text()\nfor page in reader.pages[2:4]:\n    assert 'C2 X 45 DEG - OUTER EDGE' in page.extract_text()\n    assert 'THROUGH 2.00 FLANGE' in page.extract_text()")
(H/'package_dwg.py').write_text(source,encoding='utf-8')
p=M/'README.md';text=p.read_text(encoding='utf-8').replace('RevB.zip','RevC.zip')
text=text.replace('separate supports retaining the rod contact footprints and 8.5 mm drop.','separate supports with 2 mm outer flanges and C2 x 45-degree outer-edge bevels, retaining the rod contact footprints and 8.5 mm drop.')
text=text.replace('Current helpers are in `script/cnc_drawings_20260922/`; overall assembly geometry is checked by `script/probe_rod_inspection/verify_dropped_adapter.py`.','Current revision helpers are in `script/support_flange_2mm_20260924/`; `verify_assembly.py` checks the full assembly including the rod screw seating change. The older builders retain the previous geometry and are not the current regeneration workflow.')
text += addition
p.write_text(text,encoding='utf-8')
p=R/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md'
text=p.read_text(encoding='utf-8').replace('bevel their outer ends at 45 degrees as drawn.','bevel their outer ends with a full-thickness C2 x 45-degree chamfer as drawn.')
p.write_text(text,encoding='utf-8')
(H/'README.md').write_text('''# Support flange revision - 2026-09-24

The user section sketch selects the outer rod-contact flange: 4 to 2 mm and a 45-degree outer bevel. The implemented bevel is C2, spanning the full new flange thickness. The central deck remains 4 mm, and the rod mating plane, device placement and pocket-axis alignment are unchanged.

`apply_supports.ps1` is a one-time guarded mutation with a pre-change backup in `before/`. It saves native support IPTs, assembly placements and STEP exports; moves eight existing rod screws by 2 mm to their new seating plane; and produces native previews. Do not rerun it on already-modified models.

Validation and delivery order:

1. `verify_assembly.py`: full STEP geometry, seating/interference, unchanged reference parts, device alignment and rod contact.
2. `verify_flange.py`: independent requested cuts, valid solids, volume and 20,000 deterministic point classifications per part, bevel planes and actual screw-bearing contact. Coincident-face boolean differences produce invalid kernel results, so they are not used as evidence of equivalence.
3. `verify_native_saved.ps1`: independent saved IPT copies, native features and threads.
4. `build_dwg.ps1`, then `verify_dwg.ps1`: six native Rev C DWGs, five A3 sheets and 46 associated dimensions. Render the PDF companion and inspect all sheets after changes.
5. `prepare_delivery.py`, then `package_dwg.py`: update documentation and create the Rev C plate-only delivery.

The C2 bevel leaves 60.60% of each rod screw flat bearing area in contact. No washers or substitute hardware are introduced. Existing device screw fillet/reference-slot intersections remain in the assembly report. The revision is geometrically checked, not structurally qualified. Rev B delivery files are historical; Rev C is current.

All source comments and design records are English. Original PCB/reference CAD and the flat adapter variant are unchanged by this revision.
''',encoding='utf-8')
print('Prepared Rev C packaging and updated English design records.')
