# Support flange revision - 2026-09-24

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
