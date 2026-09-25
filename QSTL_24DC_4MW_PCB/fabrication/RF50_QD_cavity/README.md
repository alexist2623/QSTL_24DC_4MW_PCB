# JLCPCB fabrication companion package

Revision status (2026-09-23): the PCB DC contact map has changed to J1 contacts 2..48 even, with contact 50 unused. Pocket/RF geometry is unchanged, but these earlier package hashes and drill exports are historical. Regenerate complete CAM from the current original PCB before production.

Status: saved PCB and footprint verified after reopening; 37 connected nets and zero violations across 15 enabled Altium DRC rules. This is a fabrication companion package, not a complete production CAM release. See manifest.json for the source PCB revision.

## QD cavity

- Keep the central QD cavity 4.3 x 4.3 mm, centred at PCB coordinates (9.75, 42.50) mm.
- Nominal envelope: X=7.60 to 11.90 mm; Y=40.35 to 44.65 mm. Internal corner radius: 0.50 mm.
- Mill from Bottom/L6, the QD wire-bonding side, to a depth of 1.20 mm. Non-plated. Do not make a through cutout.
- Move all QD pad rows radially outward by 0.20 mm. Pad-end opening becomes 4.70 x 4.70 mm; nominal cavity-to-pad clearance is 0.20 mm. Pad sizes remain 1.00 x 0.50 mm.
- Keep L1/Top GND under the pocket floor. Exclude GND from the 4.70 mm pad-end square on L2/L3/L4/L5/L6.
- Nominal copper-plus-dielectric thickness is 1.5884 mm; material remaining after 1.20 mm milling is 0.3884 mm, and the distance from the pocket floor to the inner face of L1 copper is 0.3534 mm. Manufacturing tolerances must be included in the fabricator's review.
- `bottom blind slots layer.gbr` contains the pocket area only, in the same unmirrored XY coordinates as the PCB. Do not merge it with the board outline Gerber. `QD_cavity_drawing.png` gives location and depth.

## RF and HDI

- Controlled impedance target: 50 ohms single-ended coplanar waveguide on L6 with L5 reference. Set 0.110 mm nominal trace width and 0.200 mm coplanar copper gap, following the supplied JLCPCB calculator geometry. Component pads, connectors and bond wires are transitions and are not represented by this uniform-line calculation.
- Requested calculator stack: JLCH06161HN1-1078, nominal 1.6 mm, 6 layers, outer 1 oz and inner 0.5 oz. See `stackup.csv`. The fabricator must confirm material Dk, finished copper, mask and any width compensation; the legacy Altium dielectric constants are not an impedance simulation result.
- GND shield vias: laser blind L6-L5 only, 0.100 mm nominal hole, 0.250 mm land, copper-filled and planarized. No L4/L2/DC drilling. No paste; solid GND connections without thermal relief.
- RF fence: nominal 0.15 mm land-edge gap (0.40 mm centre-to-centre chord). Straight sections have 0.435 mm centre offset: 0.055 mm half-trace + 0.330 mm copper-to-hole-edge gap + 0.050 mm hole radius. Equal-angle 13-position grids surround each active SMP centre; two symmetric RF-exit positions are omitted, leaving 11 vias with approximately 0.421 mm centre chords, with the same nominal 0.330 mm gap from the signal-pad copper edge to the laser-hole edge.
- Remove C1-C6 pad through-vias: both capacitor terminals are routed on L6. Preserve normal capacitor pads and stencil apertures. Remove the six QD RF-pad vias (1/6/9/12/18/24); their routes remain entirely on L6. Preserve via-in-pad on the 18 QD DC pads and one DC-side via on pad 2 of each R1-R6. Remove all six unused RF-side resistor pad 1 vias; their RF path remains on L6.
- QD wire-bonding field is unmasked on Bottom. RF outside that field and solder-control areas retain mask. No via, SMP or mounting-pad paste apertures. R/C perimeter fences avoid each two-pad bridge/body envelope. All six mounting lands and their surrounding rings are unmasked on both faces and directly joined to GND without thermal relief.

## JLCPCB upload and ordering fields

For production, export the six copper Gerbers, both solder-mask layers, silkscreen as desired, board outline, separate through-drill and L6-L5 laser-drill data, and include the companion blind-slot layer. Include paste Gerbers only when ordering a stencil/assembly. Do not combine laser and through drills. This companion package includes L6_L5_laser_microvias.drl, generated from the 480 saved L5-L6 vias with decimal millimetre coordinates; it is not a through-drill file. Reconcile all final CAM origins and revision hashes before release.

Select Blind Slots = Yes, Bottom entry, non-plated, depth 1.2 mm; attach the location/section drawing. Select the matching HDI stack and impedance control. Use an order remark such as:

> Bottom non-plated blind pocket is specified in bottom blind slots layer.gbr: 4.3 x 4.3 mm, R0.5, 1.2 mm depth from Bottom/QD face. Retain Top copper and the pocket floor. QD pad edge clearance is 0.2 mm nominal. RF is L6 50-ohm coplanar with L5 reference; GND laser vias connect L6-L5 only. Please review the combined HDI, cavity, remaining floor and bond-pad finish before production.

The combined cavity/HDI process and finish suitability for the user's wire-bond material have not been accepted by JLCPCB. This companion package was superseded for quotation on 2026-09-22 by the complete native CAM ZIP in [JLCPCB_HDI_20260922](../JLCPCB_HDI_20260922/README.md), which was uploaded to the JLCPCB quote page. No order has been placed.

## Official sources checked 2026-09-20

- [Blind-slot file preparation and ordering](https://jlcpcb.com/help/article/how-to-place-an-order-with-blind-slots)
- [Manufacturing capabilities: blind slots and routing](https://jlcpcb.com/capabilities/Capab)
- [HDI capabilities: laser hole, annular ring and impedance tolerance](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq)
- [Impedance calculator](https://jlcpcb.com/pcb-impedance-calculator/)
- [Calculator assumptions](https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator)
