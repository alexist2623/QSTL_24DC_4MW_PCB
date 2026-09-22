# Short plate with inward-facing device mount

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

## Pocket reference point measurement

The requested point is 0.300 mm above the milling floor into the cavity, toward the QD-side opening. In this assembly orientation that direction is global -Z. The floor centre is (25.360872538088, 175.691382249095, 11.8) mm, and the point is (25.360872538088, 175.691382249095, 11.5) mm. The tube-axis point in the same cross section is (25.5, 175.691382249095, 3) mm. Their radial separation is 8.501138538493 mm, with delta X=-0.139127461912 mm and delta Z=8.5 mm. The complete carrier is laterally centred on the plate; the PCB milling centre has this separate 0.139127 mm registration offset.

Pocket_centre_distance.png and .svg show the actual CAD section and an enlarged pocket detail. pocket_centre_distance.json records the measurement, while pocket_measurement_transforms.json records the actual nested Inventor occurrence transforms used. annotate_pocket_distance.py generates the drawing without changing the model.
