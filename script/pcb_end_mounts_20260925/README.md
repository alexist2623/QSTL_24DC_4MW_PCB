# M1 ZIF-end PCB mounts

Current geometry: MH7/MH8 at X1.05/18.45, Y1.20 mm, with 1.20 mm plated drills, 1.60 mm lands and 17.40 mm pitch. Original outline and six mounts persist. All eight mounts use direct GND, no thermal relief and no paste.

`ApplyM1.pas` records the original-PCB mutation, native repour, save/reopen DRC, paste audit and schematic check. `before_m1.PcbDoc` preserves the immediate M1.6 predecessor. These mutation scripts are one-time records; do not rerun blindly. Historical M2/M1.6 mutation and review scripts are superseded.

Current saved-file validation: `verify_m1_saved.py`, together with `../dc_even_zif_20260923/audit_connectivity.py` and `../dc_ground_pour_20260924/preview_ground.py --saved`. It verifies original pads/routes/vias/components, masks, GND/QD conditions, schematic mapping, DRC and independent continuity.

`generate_m1_round_member.ps1` obtains the genuine KS B 1021 M1 x 4 member. `prepare_m1_review.py` exports saved PCB and embedded connector geometry, plus a dimensional cable envelope. `build_m1_review.ps1` creates/reopens the native Inventor assembly, checks interference/minimum distances, and exports STEP and views. Run Inventor COM scripts using Windows PowerShell 5.1. `render_m1_clearance.py` provides the explicit dimensioned top view; `finalize_m1_review.py` links reports and updates documentation. The output is `Mechanical_Assembly/ZIF_M1_Review/`.

After native Altium `HDI_Fabrication.OutJob` export, `package_m1_cam.py` checks fresh output, 96 through holes, 480 L5-L6 blind holes, DC GND Gerber geometry and preserved silkscreen, then builds the current 18-file ZIP. `prepare_m1_deliverables.py` records how the M1-specific scripts were adapted from the preceding review; do not rerun it over finalized files.
