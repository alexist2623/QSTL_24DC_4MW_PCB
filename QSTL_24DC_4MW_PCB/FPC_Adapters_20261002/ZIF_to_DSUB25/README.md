# ZIF contact tail to Micro-D adapter

Open `ZIF_to_DSUB25.PrjPcb`; it references the native PCB, schematic and recovered local footprint libraries. Native PCB save/reopen and DRC pass. Native library loading and schematic compilation remain unverified because Altium window activation times out.

## Electrical mapping

- J1: NorComp 381-025-112L565, 25-pin right-angle male Micro-D.
- A: 51-contact integral FPC fingers based on the Molex 15015-0451 reconstruction.
- DSUB 1..13 connect to A2, A6, A10, ..., A50.
- DSUB 14..25 connect to A4, A8, A12, ..., A48.
- Odd A contacts are NC. Both boardlocks are isolated mechanical pads.

This matches Anton's saved adapter map, including A50. The carrier's separate unused-pin-50 requirement is unaffected. Source hashes are recorded in `design_plan.json`; `contact_mapping.csv` lists the 25 signal pairs. Independent PCB/schematic correspondence covers all 78 pins/pads, including the 26 NC contacts and two boardlocks.

## Geometry and stack

| Item | Saved value |
| --- | --- |
| Overall length / connector base | 40 / 31 mm, provisional |
| Mating width / pitch / contacts | 15.60 mm / 0.30 mm / 51 |
| Contact opening / back stiffener | 3 / 4 mm |
| Finished mating thickness target | 0.20 +/- 0.03 mm |
| Signal lands / drills | 0.9652 / 0.7112 mm, Anton footprint |
| Boardlock drills / pitch | 2.69 / 24.51 mm |
| Boardlock row to edge | 5.0 mm, within manufacturer's 5.70 mm maximum |
| Copper | 18 um Top and Bottom |
| PI core plus adhesive | Nominal 45 um |
| Coverlay plus adhesive | Nominal 25 um per face |
| Nominal body stack | 0.131 mm |
| Finished DSUB mounting thickness | Provisional 1.6 mm with bonded backing |

Boardlock geometry follows the [NorComp drawing](https://www.norcomp.net/rohspdfs/Micro-D/381-025-112L565.pdf). The inherited 0.7112 mm signal drill is retained; the drawing specifies 0.70 mm. Mechanical 2 backing boundaries are fabrication geometry, not 3D stiffener solids. Dielectric constant 3.5 is a placeholder; no controlled impedance is claimed.

Twelve 0.40/0.20 mm land/drill vias lie at Y=23 mm, away from exposed fingers. DSUB signal holes use one rectangular coverlay opening per row on each face, expanded 0.10 mm from the row envelope, eliminating narrow coverlay webs. Boardlock openings remain separate. The native maximum-hole rule remains enabled at 2.70 mm to accommodate the 2.69 mm boardlocks.

## Saved validation

- Native Altium save and fresh-process reopen succeeded. Native DRC: zero violations. Rebuilt connection count: zero.
- 87 independent checks passed, including physical cross-layer connectivity, signal isolation, source pin mapping, outline containment and mask/paste geometry.
- Minimum saved copper gap: 0.0707105367 mm at inherited staggered contacts.
- All contact and through-hole pad paste is disabled. No explicit paste geometry exists. Manual negative via-mask overrides close apertures on both faces; raw generic via cache flags are not CAM-aperture evidence.
- Native schematic compilation remains pending; independent saved schematic correspondence passes.

See `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json`. The PNG shows actual saved copper rather than an Altium screenshot.

This is not a fabrication release. The inherited fine finger gap and 0.127 mm signal-pad annulus need supplier acceptance; the latter is below JLCPCB's published flex PTH-annulus limit. The backing and final mating thickness also need fabrication review. [JLCPCB flex capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities)

Git delivery to the existing repository was requested on 2026-10-03. No supplier upload, fabrication release or order was performed.
