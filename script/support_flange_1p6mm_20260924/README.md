# Support flange 1.6 mm - final revision D

Final user requirements: 1.6 mm rod-contact flanges, full-thickness 45-degree outer bevels (C1.6), plain diameter 3.4 mm mounting holes, original M3 threaded rods and original fastener insertion direction. Flange threading was explicitly cancelled. The central deck remains 4 mm. Preserve the central pocket-reference alignment.

`apply_supports.ps1` updates native supports, eight screw seating transforms, STEP exports and assemblies. Its `before/` snapshot contains the prior 2 mm revision. Do not overwrite that baseline. `set_final_thickness.py` and `prepare_checks.py` are one-time helper preparation records, not regeneration commands.

Run `read_pocket_placement.ps1` to read nested saved transforms, then `verify_assembly.py`, `verify_flange.py` and `verify_native_saved.ps1`. They check valid solids, exact parameter values, native thread absence at flange holes, retained deck threads, protected part hashes, flange geometry, screw seating, actual contact/interference and pocket-reference alignment. The full model has 24 occurrences. The pocket reference is 0.300 mm from the milling floor toward its opening, not the carrier bounding-box centre.

`render_native.ps1` exports the literal cylinder axial view and the support end view. `verify_assembly.py` also makes the labelled STEP section through the pocket, whose centre can be obscured by crossbars in the literal native view.

`build_dwg.ps1` and `verify_dwg.ps1` update/reopen the six native Rev D DWGs (five A3 sheets, 46 associated dimensions). Render and inspect the PDF companion. Run `prepare_delivery.py`, then `package_dwg.py` to produce the current Rev D plate-only drawing package. Keep previous revision ZIPs historical.

The unchanged M3x8 rod screws now project 0.4 mm beyond the provisional 6 mm rods. Their flat head-bearing contact is 67.11%. Existing reference sleeve and tiny device screw fillet/slot intersections remain reported; do not assert that the complete installation is interference-free. No washers, shortened hand-built screws or unrequested reference-part edits were introduced.
