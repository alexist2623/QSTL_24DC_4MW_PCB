"""Record the single user-confirmed short-plate assembly and validate its export."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,volume
OUT=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Rod_Holder_Adapter'
HERE=Path(__file__).resolve().parent
orientation='Confirmed screenshot: ZIF uppermost; carrier turned end-for-end and mounting group on the opposite rod face.'
p=OUT/'adapter_plan.json';plan=json.loads(p.read_text(encoding='utf-8-sig'))
plan.update(confirmed_orientation=orientation,reference_coordinates='Placement parameters below define the original mounting coordinate system. Apply mounting_orientation.ps1 for the final assembly. Actual saved matrices are in final_orientation_verification.json.',device_reverse_translation_mm=[48.911503261662006,353.65604733031688,0],plate_reverse_translation_mm=[51,0,6])
p.write_text(json.dumps(plan,indent=2))
p=HERE/'build_hanging_adapter.ps1';s=p.read_text(encoding='utf-8-sig')
if "confirmed_orientation=" not in s:
    s=s.replace("@{mechanism='Continuous solid plate", "@{confirmed_orientation='"+orientation+"';reference_coordinates='Reference mounting coordinates; apply mounting_orientation.ps1 for final placement.';mechanism='Continuous solid plate")
p.write_text(s,encoding='utf-8-sig')
# Do not regenerate superseded mounting alternatives during routine native checks.
p=HERE/'finalize_hanging_adapter.ps1';s=p.read_text(encoding='utf-8-sig')
start=s.find('    $review=$app.Documents.Add(');end=s.find('    # Reload the complete generated document set')
if start>=0 and end>start:
    s=s[:start]+"    $assembly.Save()\n"+s[end:]
p.write_text(s,encoding='utf-8-sig')

geometry=json.loads((OUT/'final_orientation_geometry.json').read_text(encoding='utf-8-sig'))
native=json.loads((OUT/'final_orientation_verification.json').read_text(encoding='utf-8-sig'))
shape=read(OUT/'Rod_Holder_Assembly.step');info=inspect(shape)
assert info['valid']
assert abs(volume(shape)-geometry['expected_assembly_volume_mm3'])<1e-3
assert native['matches_user_confirmed_screenshot'] and native['occurrence_count']==14
assert max(i['overlap_mm3'] for i in geometry['interfaces'])<1e-5
report=dict(valid=True,assembly_volume_mm3=volume(shape),occurrences=14,screenshot_placement_verified_after_reopen=True,plate_length_mm=80,device_length_mm=79.43999922,plate_width_mm=51,plate_thickness_mm=4,device_overhang_at_upper_end_mm=geometry['device_overhang_y_mm'][1],new_mounting_interface_overlap_mm3=max(i['overlap_mm3'] for i in geometry['interfaces']),tube_interferences_preserved=geometry['sleeve_intersections'])
(OUT/'final_export_verification.json').write_text(json.dumps(report,indent=2))
# Mark earlier interface measurements with their reference-coordinate scope.
p=OUT/'geometry_verification.json';old=json.loads(p.read_text())
old['coordinate_scope']='Reference mounting coordinates before the confirmed orientation; final orientation checks are in final_orientation_geometry.json and final_export_verification.json.'
p.write_text(json.dumps(old,indent=2))
p=OUT/'device_thread_specification.json';threads=json.loads(p.read_text(encoding='utf-8-sig'))
threads['coordinate_scope']='Pre-reversal mounting coordinates. Final boss entries are at X=19.794248369169 and 33.294248369169 mm, Z=-7 mm; Y coordinates are unchanged.'
p.write_text(json.dumps(threads,indent=2))
(OUT/'README.md').write_text('''# Short mounting plate and confirmed assembly

The plate is now **51 x 80 x 4 mm**, shortened from 150 mm to match the unchanged device's 79.43999922 mm overall length. Its integral mounting boss is 13.5 x 72 x 6 mm. The 4 mm plate thickness also matches the measured read-only Coldfinger-SimplePlate reference; it is not a structural or thermal analysis result.

The user confirmed the screenshot with the ZIF at the upper end. The carrier is turned 180 degrees in the plate plane and uses the opposite threaded boss face. The complete plate/carrier/fastener group is then turned 180 degrees about the rod-axis line X=25.5, Z=3 mm. Rods and sleeve retain their original placement. This is the only final assembly; intermediate alternatives are archived under repository-root script/probe_rod_inspection/tmp/.

## Deliverables

- Rod_Holder_Assembly.iam: editable final Inventor assembly, 14 top-level occurrences and 32 local references.
- Rod_Holder_Assembly.step: self-contained final assembly including the sleeve.
- Rod_Holder_Adapter.ipt and .step: one connected short plate/boss solid.
- Assembly_closeup.png, Assembly_side_clamp.png and Assembly_overview.png: final CAD views. The sleeve is hidden in the Interior_Review view for readability; activate Tube_Review to show it.
- Assembly_cross_section.png: a true CAD section through assembly Y=181.75 mm, including the sleeve.
- Adapter_isometric.png, Adapter_opposite_side.png and Adapter_top.png: standalone plate views in local part coordinates.

## Dimensions and mounting

| Item | Value |
|---|---:|
| Plate | 51 x 80 x 4 mm |
| Boss | 13.5 x 72 x 6 mm |
| Plate Y limits | 135 to 215 mm |
| Boss threads | Five per side, ten total, M3 x 0.5 - 6H, right-hand |
| Thread centre pitch | 16 mm |
| Modeled bore/thread depth | 6 mm per side |
| Web between opposed bores | 1.5 mm |
| Rod fasteners | Four per rod, eight total |
| Rod fastener Y positions | 140, 160, 180, 200 mm |
| Device fasteners | Two illustrative M3 x 8 |
| Upper device overhang beyond plate | 3.1914 mm |
| Net rod-to-plate contact area | 830.8177 mm2 |

The ten native Inventor cosmetic ThreadFeatures were saved and reopened with the correct designation and depth. STEP bores do not contain helical thread geometry. Manufacturing drill allowance remains to be finalized: the reference drawing's 4 mm drill / 6 mm thread-depth callout is inconsistent. The current 6 mm cylindrical model depth is retained.

The final boss entries are at X=19.794248369169 and 33.294248369169 mm, Z=-7 mm, with Y=144.82802366515844 + 16*n mm for n=0..4. The device engages the row at X=33.294248369169 mm, Y=160.82802366515844 and 176.82802366515844 mm. Placement matrices in final_orientation_verification.json are authoritative. adapter_plan.json retains reference mounting coordinates plus the final transformation description.

## Verification and limits

The final native assembly was reopened and all 14 occurrence matrices were matched against the screenshot-confirmed arrangement. The saved STEP is a valid shape and its total component volume matches the independently transformed source solids. Checks found no positive-volume intersection among the plate, rods, device and illustrative mounting screws. The 80 mm plate remains one connected solid with no longitudinal windows.

The requested ID 51 / OD 54 mm sleeve still intersects the existing rods, plate corners, rod screw envelopes and portions of the device. Reversing the group does not eliminate those intersections. See ../Probe_Tube/geometry_verification.json and final_export_verification.json for measured values. Original carrier internal overlaps and simplified fastener assumptions remain unchanged; these files do not certify fabrication readiness.

Final reports: final_orientation_verification.json, final_orientation_geometry.json, final_export_verification.json, native_thread_verification.json. geometry_verification.json measures the reference mounting configuration and is labeled accordingly.

Scripts are under repository-root script/probe_rod_inspection/. build_hanging_adapter.ps1 includes mounting_orientation.ps1 so rebuilds retain the confirmed placement. No Git push is included.
''',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='tube_interferences_preserved'},indent=2))
