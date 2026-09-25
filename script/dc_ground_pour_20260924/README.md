# DC-layer ground pour and CAM refresh

Completed on 2026-09-24 in the original Altium project. The user confirmed GND pour around existing L2/L4 DC traces. Actual saved-copper images were delivered before CAM generation.

## Saved design

`ApplyGroundPour.pas` initially added `L2_DC_GND` and `L4_DC_GND` through Altium's native PCB API. The user's subsequent widening request was implemented by `WidenGround.pas`: a dedicated 0.20 mm `DC_GND_GAP_0P2` rule applies to GND on L2/L4, and the general 0.15 mm clearance rule excludes that scope. Both polygons were rebuilt and the original PCB was saved, reopened and independently validated.

- L2 grounded copper: 900.799391 mm2; L4: 921.449974 mm2. One connected region per added layer; no floating islands.
- Nominal DC clearance: 0.20 mm; minimum saved signal-copper gap: 0.199997029 mm (within the native 2.54 nm coordinate grid). Trace-only minimum is approximately 0.199999 mm. Trace-to-trace minima remain 0.224998 mm on L2 and 0.274998 mm on L4.
- QD GND exclusion retained on every non-Top layer; Top GND retained.
- Existing tracks, arcs, pads, vias, components, net identities and masks preserved. L1/L3/L5/L6 ground geometry is unchanged. The dedicated DC clearance rule is the only new rule; existing clearance priorities were renumbered and the general rule scope was narrowed accordingly. Native save also materialized zero-valued Manhattan-length statistics and closed the unused polygon terminal vertices onto vertex zero.
- All six mechanical GND annuli connect directly to the new pours without thermal relief.
- All 37 copper nets connected; zero stored connection lines and zero native DRC violations across 16 checked rules after save/reopen, including the new 0.20 mm DC pour rule.
- Native schematic compilation: zero violations; physical assignments match. J1 uses even contacts 2..48; 50 and odd contacts remain NC.
- Existing 480 L5-L6 shield microvias and 48 signal through vias preserved; no added DC transitions.
- Native paste audit checked 147 pads; mask/paste geometry unchanged.

Source SHA-256: `e252bd2d1eb66c667f9d9521f6877922dba3e0579a901d9490fa90835c539c07`.

Pre-widening (0.15 mm pour) SHA-256: `84dcebb1a5cb88b31b997d4bbd6eb5fdd2adb6653206d6d17162d2bf9df86361`. Backup: `before_clearance_0p20.PcbDoc`.

Saved PCB SHA-256: `833555d572fb9945703213acef1ecd809d7eb3ce4a73d5e467c577d3ef70bc90`.

`verify_saved.py` records checks in `validation.json` and `../../QSTL_24DC_4MW_PCB/docs/DC_GND_pour_validation.json`. `preview_ground.py --saved` renders actual native copper to `../../QSTL_24DC_4MW_PCB/docs/DC_GND_pour.png`. Its default mode and `DC_GND_pour_preview.png` are historical proposals, not final results. Mutation scripts are one-time records and must not be rerun against a later board.

## Manufacturing outputs

`prepare_outjob.py` transfers the original project's saved Gerber/NC-drill settings into `HDI_Fabrication.OutJob`. The OutJob belongs to the original project and selects its PCB. Altium regenerated both outputs into `fabrication/JLCPCB_HDI_20260924/Native_CAM` after the 0.20 mm change. Export did not change the PCB.

`package_cam.py` checks timestamps, source hashes, 12 Gerbers, actual GND pours against native geometry, all 94 plated through holes, all 480 laser holes, coordinates/diameters, L5-L6 layer pair, outline and separate Bottom blind-pocket contour. Gerber GND boundaries match native copper within the 0.0002 mm comparison tolerance.

Delivery: `fabrication/JLCPCB_HDI_20260924/QSTL_24DC_6RF_HDI_Gerber_20260924.zip`. Includes requested stack, 50-ohm geometry and Bottom 4.3 x 4.3 x 1.2 mm pocket documentation. Paste/stencil outputs are excluded. `CAM_validation.json` and `Native_DRC.html` accompany the ZIP.

Earlier startup/login and standalone-dialog problems were resolved; the native OutJob completed CAM generation. No supplier upload, new quote, order or Git push was performed for this refresh.
