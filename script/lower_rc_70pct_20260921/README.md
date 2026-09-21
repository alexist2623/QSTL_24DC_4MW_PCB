# Lower R/C placement at 70% of centreline distance

This revision edits the original PCB only. The schematic and QD footprint library remain unchanged; no pin remap is required.

- Translate R1/C1 by -1.36500108 mm X and R5/C5 by +1.46999960 mm X. The centre of each pair's pad envelope is at 70% of its previous distance from X=9.75 mm. Y, spacing and rotations remain unchanged.
- Remove six unused QD RF through vias at pads 1/6/9/12/18/24. Keep 18 QD DC vias, six resistor DC vias and 24 ZIF fanout vias. Capacitor and resistor RF pads remain via-free.
- Reconnect S1/MW1/S5/MW5 using XY/45-degree straight segments with tangent bends. MW1 uses 0.15 mm tangent radii for its small lateral adjustment; other changed bends use 0.30 mm radii. Simplify ZIF21/ZIF02 terminal approaches on their original L4 layer without extra vias.
- Regenerate 0.90 mm rectangular R/C masks and 480 solid L5-L6 shields: 243 RF-fence, 171 R/C-perimeter and 66 equal-angle SMP-ring vias. Preserve the hole-edge offset, no-interpad-via envelopes and cavity/ground/paste requirements.
- Move only the C1 reference label downward by 1.2 mm to resolve the resulting silk collision.

`prepare_move.py` and `prepare_shields.py` reuse the checked-in native geometry writers and guard the expected starting state. `ApplyMove.pas`, `ApplyShields.pas` and `FixLabel.pas` are one-time native mutations; do not rerun on a different revision. `before.PcbDoc` is a local ignored backup.

Validation reads the saved native PCB: exact requested moves and unaffected geometry, 37-net physical copper graph, one internal DC layer per net, XY/45-degree routing, tangent RF bends outside pads, RF paths through resistor pad centres, mask rectangles, 101 normal SMD paste apertures, QD ground exclusions, solid mounting connections, and 15 enabled Altium DRC rules after reopening. All reports must match the current PCB hash. Existing short track endings wholly inside QD pads 1/24 are recorded separately from exposed trace bends.

`publish_outputs.py` refreshes previews and fabrication companion files; this is not a complete production CAM release. `finalize_reports.py` updates current-report pointers after verification.
