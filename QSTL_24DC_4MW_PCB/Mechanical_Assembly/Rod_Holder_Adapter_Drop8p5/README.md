# Three-piece mounting plate with an 8.5 mm drop

The current delivery is `QSTL_Plate_DWG_Package_RevE.zip`, regenerated from the saved CAD on 2026-09-24. It contains six native Inventor DWGs: five individual sheets and one combined five-sheet master. See `Manufacturing_DWG/README.md` for the sheet list. Drawing scope is the central plate/boss, separate supports and their eight-screw assembly. All three fabricated parts are oxygen-free copper, with no surface treatment. The original flat variant in `../Rod_Holder_Adapter/` is unchanged.

## Current models

- `Centre_Plate.ipt` and `.step`: 39 x 80 x 4 mm deck, integral 13.5 x 72 x 6 mm boss, eight 3.4 mm clearance holes with 6.6 mm x 90-degree countersinks.
- `Left_Rod_Support.ipt` / `Right_Rod_Support.ipt` and STEP files: separate supports with 1.6 mm outer flanges and C1.6 x 45-degree outer-edge bevels, retaining the rod contact footprints and 8.5 mm drop.
- `Rod_Holder_Assembly_Drop8p5.iam` and `.step`: complete variant with the existing carrier, PCB, rods and sleeve.
- `Manufacturing_DWG/Split_Mount_Plate_Only.iam`: three fabricated parts and eight countersunk screws.
- `Manufacturing_DWG/Split_Mount_Assembly.ipn`: native exploded presentation used by the assembly drawing.

The boss has five native M3x0.5-6H threads per side, at 16 mm pitch and 6 mm nominal depth. Each support has four native M3x0.5-6H blind threads at 20 mm pitch and 6.5 mm nominal depth.

Two lip reliefs are 3.3398406169 mm wide, 72 mm long and 0.5 mm deep, with R0.5 closed-end corners. Width is the measured 3.0398406169 mm lip plus 0.3 mm total allowance. Boss contact faces, device placement and thread axes remain unchanged.

## Standard hardware

Eight plate-joining screws are unmodified Inventor 2027 Content Center DIN 7991 M3x10 countersunk members, with 0.5 mm pitch and native 6g external thread features. The 6 mm head has a 0.2 mm rim; the 6.6 mm countersink seats its front 0.1 mm below the deck. Nominal engagement is 6.1 mm, with 0.4 mm remaining bore depth.

The full assembly uses eight supplied ISO 7380-1 M3x8 button-head screws at the rod interfaces and two supplied ISO 4762 M3x8 screws at the device interfaces. No washers are installed. `Standard_Fasteners/` contains the actual members; `content_center_fasteners.json` records families, library IDs, parameters and original member hashes.

## Verification

- All six DWGs reopened successfully, with five A3 sheets and 46 attached model dimensions without overrides. See `Manufacturing_DWG/dwg_reopen_audit.json` and `delivery_audit.json`.
- Three fabricated parts are valid individual solids. The full assembly has 24 top-level occurrences. Native threads and supplied hardware identity are checked in `standard_hardware_audit.json`.
- `geometry_verification.json` reports actual intersections. Plate joining screws clear the countersinks, carrier and sleeve. Cosmetic thread-cylinder overlap is confined to intended tapped regions.
- Two unresolved intersections remain between device screw under-head fillets and unchanged reference slots, approximately 0.00205 mm3 each. No washers or unrequested reference-part edits conceal these. The full installation is not marked interference-free.
- Existing sleeve intersections with rod corners, support flange corners and rod screw heads remain separately recorded.
- The PCB pocket reference point, 0.300 mm from the milling floor toward the opening, aligns with the sleeve axis within CAD numerical precision. Rod contact areas and original CAD source hashes remain unchanged.
- `device_relief_grooves.json` records independently verified groove geometry. `inward_placements.json` records saved occurrence transforms.

Current rod-hardware helpers are in `script/rod_button_head_20260924/`. The flange-generation and drawing helpers remain in `script/support_flange_1p6mm_20260924/`; their saved pre-button-head verification is historical for rod screws. The older builders retain the previous geometry and are not the current regeneration workflow. Earlier prototype builders and ignored local previews are historical, not the current delivery.

## Final support flange revision - 2026-09-24

Both outer rod-contact flanges are 1.60 mm thick with full-thickness C1.6 x 45-degree outer bevels. The central deck remains 4 mm thick. The rod mating plane, full rod contact footprints, 8.5 mm mounting drop, boss and device placement are unchanged.

The four rod fastener holes in each support remain plain diameter 3.4 mm through holes; no support-flange thread features are present. The user cancelled flange threading after confirming that the reference rods already specify M3 through threads. The eight rod screws are now unmodified Content Center ISO 7380-1 M3x8 button-head members. They retain their insertion direction through the support into the rod and bearing planes at global Z=-1.6 mm. The original rods remain unchanged. With the provisional 6 mm rod depth, the screw tips project 0.4 mm beyond the rods. No washers are used.

With the ISO 7380-1 button heads, the C1.6 bevel leaves 70.70% of the actual flat under-head bearing area supported (10.845 of 15.339 mm2 per rod screw). The previous 67.11% result applies to the superseded ISO 4762 rod heads. Geometry checks do not constitute preload or structural qualification. Existing reference-part/sleeve intersections and tiny device under-head fillet intersections remain recorded in the full assembly report.

The PCB pocket-floor centre plus 0.300 mm toward the cavity opening is at X=25.500, Z=3.000 mm, matching the cylinder axis. Calculated nominal radial residual is below 0.001 mm; the unrounded CAD value is recorded in geometry_verification.json. Cylinder_top_1p6mm.png is a literal native axial view; Cylinder_centre_1p6mm.png is a STEP-derived section exposing the pocket reference point hidden behind the crossbars in that view.

Validation: independent saved support IPT copies, one healthy solid per part, native C1.6 chamfer, four unchanged deck-joining M3x0.5-6H threads per support, and no added flange threads. STEP checks confirm the requested cut volume, 20,000 matching point classifications per part, rod contact and screw seating. All six Rev D DWGs reopen with 46 attached dimensions. Previous revision drawing/ZIP files outside this package are superseded and must not be paired with current models.


## Button-head rod hardware - 2026-09-24

Eight rod screws are actual Inventor 2027 Content Center ISO 7380-1 M3x8 members: head diameter 5.7 mm, head height 1.65 mm, 2 mm hex drive, M3x0.5-6g external thread. The two device screws and eight DIN 7991 plate screws remain unchanged. The copied library member retains its original SHA-256 and Content Center identity. No washers are present.

The native assembly was saved and reopened. Only the eight rod occurrence file references changed; every occurrence transform and all three fabricated IPT/STEP pairs are unchanged. STEP solid validity and assembly/component volume agreement were checked using adaptive integration for the curved heads. See rod_button_head_native_audit.json and rod_button_head_verification.json in the model directory.

Per rod screw, the sleeve overlap falls from approximately 3.398 to 0.576 mm3, but is not eliminated. The supplied R0.3 under-head fillet also intersects the unchamfered 3.4 mm flange-hole mouth by approximately 0.00492 mm3. This is an unresolved geometric seating issue, not cosmetic thread overlap. Hole geometry and supplied screws were not modified to conceal it. Original rod-corner/support/sleeve clashes and device fillet intersections remain.

Cylinder_top_round_heads.png shows the native axial view; Rod_button_head_assembly.png shows the mounting screws with the sleeve hidden for inspection. Fabricated geometry, the plate-only IAM/IPN and all six Rev D DWGs are byte-for-byte unchanged by this hardware-only update. Rod installation is outside the plate drawing scope; source_cad_hashes.json remains the historical drawing-generation record, including its then-current full-installation IAM hash. The rod change does not invalidate the associated plate views.

