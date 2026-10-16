# DC routing on the fixed sixteen-RF proposal

## Scope and result

All 38 independent DC connections are saved as continuous, clearance-checked coordinate routes. L2 and L3 carry 19 nets each, and L4 is assigned to GND. Every net stays on one internal layer. This is an offline routing proposal, not an updated native PCB or a native DRC result. Native PCB, schematic, source mapping, RF proposal and mechanical placement are unchanged.

The fixed RF bias tees are preserved: 16 resistor pad-2 DC terminals, plus 22 direct QD terminals. Exactly 76 terminal vias are used, with no standalone transition vias and no RF signal vias. The 1,439 L5-L6-only shield microvias remain unchanged. Five direct-QD terminal vias move only inside their unchanged bond lands to maintain at least 0.20 mm clearance to shield lands; movements are recorded in `dc_routed_plan.json`.

## Geometry and connectivity checks

- DC width: 0.125 mm. Minimum same-layer copper gap: 0.106931 mm (required 0.10 mm).
- Trace to foreign via land: 0.112265 mm; trace to foreign through-drill edge: 0.203572 mm (required 0.20 mm).
- Terminal via to Bottom RF copper: 0.269395 mm; terminal via to GND shield land: 0.203395 mm.
- All source and ZIF terminal centres connect exactly after saving and reopening the route data. Each DC net has one distinct ZIF contact. All 24 even pins 2..48 and 14 odd pins 1..27 are used; pin 50 remains unused.
- 35 contact assignments change relative to the native mapping. `proposed_pin_mapping.csv` and `schematic_change_contract.json` record the identical proposed mapping for future PCB/schematic implementation. These changes have not been applied to the native schematic.
- Internal DC copper excludes every complete SMP five-pad convex hull, resistor inter-pad/body envelope, mounting envelope and the central blind pocket. Passing under a capacitor body is allowed on an internal layer. Coincident XY projections on different layers are not electrical shorts.
- DC segments are horizontal, vertical or 45 degrees; no bend exceeds 45 degrees after chamfering. Source/component/connector coordinates are preserved except the five small terminal-via adjustments.
- Top ZIF fanout geometry is translated unchanged with the relocated connector and independently checked for pad/via/track clearance and continuity.

## Layer and manufacturing basis

The intended stack is L1 GND / L2 DC-A / L3 DC-B / L4 GND / L5 GND / L6 RF-QD. The user's L3/L4 exchange applies to this sixteen-RF proposal. The complete former L4 DC bank has moved to L3 without changing its XY routing or contacts. Historical native-source layer numbers are retained only in the `old_dc_layer` and source-mapping fields; they are not the proposed assignment. New L4 GND pours and antipads remain part of native implementation.

The prior order was six-layer HDI, 1-step, 1.6 mm, ENIG, outer 1 oz. Requested JLCH06161HN1-1078 / 0.0784 mm outer dielectric / 0.5 oz inner copper differed from the saved cart's NP-175F / 1 oz inner, subject to review. The RF target stays W=0.11 mm, coplanar gap 0.20 mm; this DC study does not establish impedance or resolve the manufacturer's stack review.

The [JLCPCB capability table](https://jlcpcb.com/capabilities/pcb-capabilities/) checked on 2026-10-16 specifies 0.09/0.09 mm multilayer 1 oz width/spacing and 0.20 mm inner copper-to-via-hole clearance. The router enforces 0.125/0.10 mm and checks hole-edge clearance separately from land clearance. Retained terminal via land/hole sizes are QD 0.35/0.20, R 0.50/0.25 and ZIF 0.40/0.20 mm. Ordinary via annular-ring rules must not be confused with component PTH annular rings.

## Remaining implementation work

Native placement/outline changes, route import, synchronized schematic mapping, GND pours and antipads, mask updates, native save/reopen connectivity/DRC and final fabrication checks remain pending. In particular, this inherited SMP footprint has approximately 0.125 mm component-PTH annular rings and needs its own manufacturing review; this is not a blanket JLCPCB approval. Gerbers and the shopping cart are not changed.

## Files

- `DC_Layers_Overview.png`: L2, L3 and combined views.
- `DC_QD_Detail.png`: QD and resistor DC terminal exits.
- `DC_ZIF_Detail.png`: relocated connector fanout with contact numbers.
- `dc_routed_plan.json`: all paths, vias and Top fanout.
- `dc_geometry_audit.json`: independently recomputed saved-geometry results.
- `proposed_pin_mapping.csv` and `schematic_change_contract.json`: synchronized proposed assignments.

Helper scripts are stored in the repository's `script/rf_redline_review_20261011/` directory. Source SHA256 checks are included in the audit. No native design/reference files were modified.
