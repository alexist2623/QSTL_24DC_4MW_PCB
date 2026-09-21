# Dense L5-L6 shield vias

User clarification: 0.15 mm is the spacing between shield-via copper-land edges, not the distance from RF copper. Retain the 0.25 mm land and 0.10 mm hole; nominal centre spacing is 0.40 mm. RF-to-via edge spacing remains 0.33 mm.

Saved original PCB SHA-256: `cd2c8eb18dbdc26cdb8f8d0b2e5536f642535e9f390aa7869319507fd45a0737`.

- 287 L5-L6 GND shields: 217 RF fence and 70 SMP ring vias.
- Saved minimum land-edge gap: 0.149998088 mm, within native coordinate precision of 0.15 mm.
- 283 of 287 vias have a nearest neighbour within 0.005 mm of the nominal gap. Component pads, holes, RF exits and fence endpoints create the larger local gaps.
- All 60 signal through-vias, component/pad placements, signal tracks/arcs, schematic, library, stack, cavity, mask and paste geometry are preserved.
- All 37 nets physically connected; zero stored connections; zero violations across 15 enabled Altium DRC checks after reopening.
- Shield vias remain solid GND, L5-L6 only, with no DC-layer penetration or via-specific paste.

`prepare.py` creates a plan and a guarded one-time native mutation from `before.PcbDoc`. Do not rerun mutation scripts against the completed board. `audit_connectivity.py` and `verify_final.py` inspect the saved copper; `verify_fabrication.py` checks the cavity and updated 287-hole laser-drill companion. Native logs are retained here. Published reports are under the original project's docs directory.

`publish_outputs.py` updates the saved-native previews and fabrication companion package. This package is not a complete production CAM release; no upload or order was made.
