"""Document the corrected inward mounting and remove obsolete coordinate claims."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Rod_Holder_Adapter'
records=json.loads((OUT/'inward_placements.json').read_text(encoding='utf-8-sig'))
check=json.loads((OUT/'inward_geometry_verification.json').read_text())
orientation='Plate behind rods; boss and device face inward between rods. ZIF uppermost; device centered at X=25.5 mm.'
p=OUT/'adapter_plan.json';plan=json.loads(p.read_text())
plan.update(confirmed_orientation=orientation,reference_coordinates='Actual final assembly coordinates; inward_placements.json contains the authoritative reopened occurrence matrices.',adapter_position_mm=[0,135,-4],holder_translation_mm=[9.03587298808781,222.9513830290954,14.18839662],holder_rotation_x_deg=180,boss_x_min_mm=19.794248369169,boss_x_max_mm=33.294248369169,side_clamp_centres_mm=[[16.754407752268484,176.82802366515844,3],[16.754407752268484,160.82802366515844,3]],plate_midplane_x_mm=25.5,device_centre_x_mm=check['device_centre_x_mm'])
for key in ('holder_rotation_y_deg','side_clamp_rotation_y_deg','device_reverse_translation_mm','plate_reverse_translation_mm'):plan.pop(key,None)
plan['side_clamp_rotation_matrix']=[[0,0,1],[0,-1,0],[1,0,0]]
for parameter in plan['parameters']:
    if parameter['name']=='FingerStartX':parameter.update(expression='19.794248369169 mm',comment='Centre the reversed device on the plate midplane X=25.5 mm.')
p.write_text(json.dumps(plan,indent=2))
p=OUT/'device_thread_specification.json';t=json.loads(p.read_text());t.update(centre_z_mm=3,sides=[dict(entry_x_mm=33.294248369169,axis='-X'),dict(entry_x_mm=19.794248369169,axis='+X')],coordinate_scope='Actual assembly coordinates. The device uses the entry face at X=19.794248369169 mm; rod screws enter toward +Z from the back of the plate.')
p.write_text(json.dumps(t,indent=2))
# Rebuilds use the same final geometry and camera directions.
p=HERE/'build_hanging_adapter.ps1';s=p.read_text(encoding='utf-8-sig')
s=s.replace("@(-129,265,-524)","@(-130,265,530)").replace("@(-109,255,-189)","@(-115,245,190)").replace("@(-135,220,-65)","@(-160,210,28)").replace("@(25.5,177,-7)","@(25.5,175,3)")
lines=s.splitlines()
for i,line in enumerate(lines):
    if "'adapter_plan.json'" in line:
        lines[i]="    [pscustomobject]@{confirmed_orientation='"+orientation+"';adapter_position_mm=@(0,135,-4);holder_rotation_x_deg=180;holder_translation_mm=@(9.03587298808781,222.9513830290954,14.18839662);solid_plate_mm=@(51,80,4);boss_x_min_mm=19.794248369169;boss_x_max_mm=33.294248369169;boss_width_mm=13.5;contact_length_per_rod_mm=80;contact_width_mm=6;gross_contact_area_mm2=960;side_clamp_centres_mm=@(@(16.754407752268484,176.82802366515844,3),@(16.754407752268484,160.82802366515844,3));rod_fastener_rows_y_mm=@(140,160,180,200);plate_midplane_x_mm=25.5;device_centre_x_mm=25.5;parameters=$parameterReport} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'adapter_plan.json') -Encoding UTF8"
    if "'device_thread_specification.json'" in line:
        lines[i]=line.replace('31.205751630831003','33.294248369169').replace('17.705751630831003','19.794248369169').replace('centre_z_mm=13','centre_z_mm=3')
p.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')

(OUT/'README.md').write_text('''# Short plate with inward-facing device mount

The final arrangement follows the user's correction: the 4 mm base plate attaches to the back faces of the rods, while its raised boss projects inward between them. The device retains the confirmed 180-degree end-for-end orientation, with ZIF uppermost. The previous arrangement with the boss facing outward is superseded.

The device and mating boss were moved together by 2.088496738338 mm in X. The complete carrier's left and right bounds are 15.283771299524 and 35.716228700476 mm. Their midpoint is X=25.5 mm, exactly on the plate's longitudinal bisecting plane within CAD numerical precision. This is lateral centering; it does not place the device at the midpoint of the plate thickness.

## Geometry

| Item | Value |
|---|---:|
| Base plate | 51 x 80 x 4 mm |
| Device overall length | 79.43999922 mm |
| Raised boss | 13.5 x 72 x 6 mm |
| Plate base Z interval | -4 to 0 mm |
| Both rods Z interval | 0 to 6 mm |
| Inward boss Z interval | 0 to 6 mm |
| Plate and device lateral centre | X=25.5 mm |
| Plate Y interval | 135 to 215 mm |
| Device upper-end overhang | 3.1914 mm |
| Boss threads | Five per side, ten total; M3 x 0.5 - 6H, right-hand |
| Thread centre pitch | 16 mm |
| Modeled bore/thread depth | 6 mm per side |
| Web between opposed bores | 1.5 mm |
| Rod fasteners | Four per rod, eight total; enter from Z=-4 toward +Z |
| Device fasteners | Two illustrative M3 x 8 |

The standalone plate has ten native Inventor cosmetic thread features. STEP contains cylindrical bores without thread helices. Final boss entry faces are X=19.794248369169 and 33.294248369169 mm, at Z=3 mm. Hole Y coordinates are 144.82802366515844 + 16*n mm for n=0..4. Device screws enter the first face in +X at Y=160.82802366515844 and 176.82802366515844 mm.

The plate's 4 mm thickness matches the measured Coldfinger-SimplePlate reference. No stiffness or thermal analysis is implied. Manufacturing drill allowance remains unresolved because the reference drawing inconsistently calls for 4 mm drill depth and 6 mm thread depth.

## Files and verification

- Rod_Holder_Assembly.iam and .step: the single final assembly, 14 top-level occurrences and 32 local references. Activate Tube_Review for the sleeve or Interior_Review for the mounting details.
- Rod_Holder_Adapter.ipt and .step: editable single-solid plate/boss.
- Assembly_closeup.png, Assembly_side_clamp.png, Assembly_overview.png and Reversed_plate_side.png: final saved CAD views.
- Assembly_cross_section.png: true CAD section through Y=175 mm. Brown is the rod pair, blue is the plate/boss, orange is the original holder, and gray is the requested sleeve.
- inward_placements.json: occurrence matrices read after reopening the saved native assembly.
- inward_geometry_verification.json: independent STEP geometry checks using those matrices.
- native_thread_verification.json: saved thread metadata and locations in part coordinates.

The saved assembly STEP is valid. Rod/plate, plate/device and all illustrated mounting-screw interfaces have the intended contact and no positive-volume overlap. The device's lateral centre offset from the plate centre plane is less than 0.000001 mm. The requested 51 mm ID sleeve still intersects rod corners, plate corners and rod screw envelopes; these existing envelope conflicts are reported separately. Original carrier internal overlaps and simplified fastener assumptions are unchanged.

Scripts are under repository-root script/probe_rod_inspection/. mounting_orientation.ps1 applies absolute final placements, so running it again does not double-rotate the parts. Geometry checks use verify_inward_mounting.py. Superseded review variants are retained only in script/probe_rod_inspection/tmp/. No Git push is included.
''',encoding='utf-8')
print('Documented actual inward mounting coordinates and device centering.')
