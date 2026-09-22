# Three-piece mounting plate with an 8.5 mm drop

The current delivery is `QSTL_Plate_DWG_Package_RevB.zip`. It contains six native Inventor DWGs: five individual sheets and one combined five-sheet master. See `Manufacturing_DWG/README.md` for the sheet list. Drawing scope is the central plate/boss, separate supports and their eight-screw assembly. All three fabricated parts are oxygen-free copper, with no surface treatment. The original flat variant in `../Rod_Holder_Adapter/` is unchanged.

## Current models

- `Centre_Plate.ipt` and `.step`: 39 x 80 x 4 mm deck, integral 13.5 x 72 x 6 mm boss, eight 3.4 mm clearance holes with 6.6 mm x 90-degree countersinks.
- `Left_Rod_Support.ipt` / `Right_Rod_Support.ipt` and STEP files: separate supports retaining the rod contact footprints and 8.5 mm drop.
- `Rod_Holder_Assembly_Drop8p5.iam` and `.step`: complete variant with the existing carrier, PCB, rods and sleeve.
- `Manufacturing_DWG/Split_Mount_Plate_Only.iam`: three fabricated parts and eight countersunk screws.
- `Manufacturing_DWG/Split_Mount_Assembly.ipn`: native exploded presentation used by the assembly drawing.

The boss has five native M3x0.5-6H threads per side, at 16 mm pitch and 6 mm nominal depth. Each support has four native M3x0.5-6H blind threads at 20 mm pitch and 6.5 mm nominal depth.

Two lip reliefs are 3.3398406169 mm wide, 72 mm long and 0.5 mm deep, with R0.5 closed-end corners. Width is the measured 3.0398406169 mm lip plus 0.3 mm total allowance. Boss contact faces, device placement and thread axes remain unchanged.

## Standard hardware

Eight plate-joining screws are unmodified Inventor 2027 Content Center DIN 7991 M3x10 countersunk members, with 0.5 mm pitch and native 6g external thread features. The 6 mm head has a 0.2 mm rim; the 6.6 mm countersink seats its front 0.1 mm below the deck. Nominal engagement is 6.1 mm, with 0.4 mm remaining bore depth.

The full assembly also uses ten supplied ISO 4762 M3x8 screws at the rod/device interfaces. No washers are installed. `Standard_Fasteners/` contains the actual members; `content_center_fasteners.json` records families, library IDs, parameters and original member hashes.

## Verification

- All six DWGs reopened successfully, with five A3 sheets and 46 attached model dimensions without overrides. See `Manufacturing_DWG/dwg_reopen_audit.json` and `delivery_audit.json`.
- Three fabricated parts are valid individual solids. The full assembly has 24 top-level occurrences. Native threads and supplied hardware identity are checked in `standard_hardware_audit.json`.
- `geometry_verification.json` reports actual intersections. Plate joining screws clear the countersinks, carrier and sleeve. Cosmetic thread-cylinder overlap is confined to intended tapped regions.
- Two unresolved intersections remain between device screw under-head fillets and unchanged reference slots, approximately 0.00205 mm3 each. No washers or unrequested reference-part edits conceal these. The full installation is not marked interference-free.
- Existing sleeve intersections with rod corners, support flange corners and rod screw heads remain separately recorded.
- The PCB pocket reference point, 0.300 mm from the milling floor toward the opening, aligns with the sleeve axis within CAD numerical precision. Rod contact areas and original CAD source hashes remain unchanged.
- `device_relief_grooves.json` records independently verified groove geometry. `inward_placements.json` records saved occurrence transforms.

Current helpers are in `script/cnc_drawings_20260922/`; overall assembly geometry is checked by `script/probe_rod_inspection/verify_dropped_adapter.py`. Earlier prototype builders and ignored local previews are historical, not the current delivery.
