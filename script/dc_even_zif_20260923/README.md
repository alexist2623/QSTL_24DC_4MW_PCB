# Even-contact ZIF DC remap

The original project now uses physical J1 contacts 2, 4, ..., 48 for 18 QD DC inputs and six RF bias inputs. Contact 50, every odd contact and connector mounts 52/53 remain NC. No component positions, pad sizes, RF geometry, shielding or layer stack were changed.

The existing 24 ZIF fanout vias were moved into two rows. Each net uses exactly one internal layer: 12 on L2 and 12 on L4. DC routing below Y=20 mm and local Top/Bottom ZIF mask protection were rebuilt. The schematic, QD symbol library and `docs/PIN_MAPPING.csv` follow the physical even-contact map.

## Saved-file validation

- `audit_connectivity.py`: all 37 nets form continuous copper graphs; 0 saved connection lines, 48 signal through vias and 480 L5-L6 GND blind vias.
- `verify_final.py`: native geometry, clearance rules, QD cavity/GND exclusion, mask, paste and DRC checks.
- `verify_refinements.py`: rectangular masks, solid mounting-hole copper and retained RF shield rings.
- `finish.py`: exact RF/component/pad preservation, even contacts, one internal layer per DC net, XY/45-degree directions, at most 45-degree turns, schematic/PCB/library consistency and actual saved-geometry previews.
- Native save/reopen DRC: 0 violations across 15 enabled rules. Schematic export: 0 reported violations and matching 37 named nets plus 31 singleton NC nets. The API compile-return flag was False and is retained verbatim in `schematic_validation.json`.

The final source hash is in the validation JSON files. Previews are generated from the saved PCB primitives, not synthesized illustrations or screenshots. `DC_Even_ZIF.png` shows the overlay and both DC layers; `DC_Even_ZIF_detail.png` shows all connector contacts and contact 50 NC.

## Change-record workflow

`inspect_baseline.py`, `prepare.py` and `build_native.py` record the initial guarded change preparation. `ApplyEvenDC.pas` performs the native mutation. `prepare_audits.py` promotes the prepared schematic/library after closing them in Altium. `FixZIFPads.pas` explicitly sets the pad InNet flag and rebuilds net connectivity before saving and reopening. This flag is required for previously unconnected pads to retain their new nets on save. All native paths must use single Pascal backslashes to avoid duplicate Free Document aliases.

Mutation scripts and the saved `before.*` files belong to this one-time revision. Do not rerun them blindly against a later PCB. Read-only validators and `finish.py` may be rerun to refresh the matching reports/previews. Prior Gerber/HDI quote packages are historical and were not regenerated or uploaded for this request.
