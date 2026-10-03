# ZIF to two ZIF ends

Open `ZIF_to_2xZIF.PrjPcb`; it references the native PCB and schematic.

## Wiring and geometry

Every numbered contact branches to both outputs: **C.n = A.n = B.n for n = 1..51**. C is the long common end with Bottom contacts; A and B are the upper and lower right outputs with Top contacts. Contact numbers increase left to right in the review's common Top XY projection. A physical Bottom view is mirrored.

| Item | Saved value |
| --- | --- |
| A-to-B tip separation | **70 mm**, A at Y=420, B at Y=350 mm |
| Overall length | 420 mm, provisional reading of 390 + 30 |
| Strip width / clear lateral gap | 15.60 / 10.00 mm; gap interpretation provisional |
| Contact count / pitch | 51 / 0.30 mm at every end |
| Straight section above junction | 20.00 mm |
| Exposed contacts / back stiffeners | 3.00 / 4.00 mm |
| Finished mating thickness target | 0.20 +/- 0.03 mm |
| Branch via land / drill | 0.30 / 0.10 mm; 51 plated Top-to-Bottom vias |
| Copper | 18 um Top and Bottom |
| PI core plus adhesive | Nominal 45 um |
| Coverlay plus adhesive | Nominal 25 um per face |
| Nominal body stack | 0.131 mm |

The staggered fingers retain the Molex 15015-0451 reconstruction. A continuous Top bus joins A to B; a rounded Bottom bus from C reaches the diagonal crossover vias. Body tracks are 0.20 mm and junction tracks are 0.10 mm. The junction is a static no-bend area. The outline's in-plane curve is not an out-of-plane folding-radius specification.

Top/Bottom Solder layers represent coverlay openings: Top at A and B, Bottom at C. Mechanical 2 shows back-stiffener boundaries opposite the exposed fingers; these are fabrication boundaries, not native 3D stiffener solids. Final backing thickness must achieve the required finished mating thickness.

## Saved validation

- Altium native save and fresh-process reopen succeeded. Native DRC has zero violations; rebuilt connection count is zero.
- 532 independent saved-file checks passed, including 70 mm tip spacing, 51 physically continuous three-contact nets, inter-net isolation, drill spacing, outline and coverlay geometry.
- Minimum saved copper gap: 0.0707105367 mm at the inherited fingers. Via annulus: 0.10 mm. Minimum drill-to-other-net copper distance: approximately 0.200 mm.
- All 153 saved PCB assignments match the independently recovered schematic wire/label graph.
- Native pad paste is disabled. No explicit paste geometry exists. Every via has a negative manual mask expansion that closes its opening on both faces. Generic inherited via cache flags in the raw audit are not actual CAM-aperture indicators.
- Original carrier PCB/schematic and straight-cable hashes remain unchanged.
- The first native schematic compile found three missing footprint models. Component-specific local footprint files have now been recovered from saved geometry and explicitly linked in the schematic/project. Native library loading and recompile remain pending because Altium window activation times out. This limitation does not waive those checks.

See `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json`. The PNG is a dimensional rendering of actual saved copper, not an Altium screenshot.

Fabricator review is still required: the 0.10/0.30 mm hole/land pair is at JLCPCB's published two-layer-flex extreme capability, and the original finger gap is below its regular line/space capability. Stack, backing and coverlay registration remain subject to supplier acceptance. [JLCPCB flex capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities)

Git delivery was requested on 2026-10-03. No fabrication release, supplier upload or order was performed. Helpers are under `script/branched_fpc_20261002/`.
