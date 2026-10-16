# Symmetric 16-RF routing and shield proposal

Updated 2026-10-16. This is an offline geometric proposal, not an Altium implementation or a manufacturing release.

The fixed SMP/QD/mount/ZIF geometry, electrical membership, 0603 resistors, exact Yageo CC1206JKNPO9BN104 capacitor envelopes, and accepted 30/60/90-degree R/C placements are preserved. All source hashes match the preceding accepted symmetric proposal. Component mirror checks and the central pair alignment at X=1.485/18.015 mm pass.

## Revised routing

RF width remains 0.11 mm. Each QD, capacitor and resistor pad has a straight normal boundary crossing; curved segments begin outside the land. The actual R1 boundary intersections, rather than only a tangent at its centre, were checked. SMP signal entry is radial. Minimum sampled curve radius is 0.55 mm. There are no RF signal vias, RF crossings, resistor inter-pad crossings or capacitor-terminal shorts in this proposal.

Outside the highlighted QD launch prefixes, RF copper-edge separation is at least 1.180656 mm, exceeding the requested 6W + 2D = 1.160 mm. The closest pair is SMP12/SMP15. The complete QD fanout is limited to a 3 mm expansion of the aligned pad-end rectangle. Actual close-spacing points extend at most 2.944290 mm outside that rectangle; the longest curved launch prefix measures 5.885044 mm along its route. These are explicitly measured exceptions, not a global spacing waiver. The smallest RF edge gap inside the exception is 0.197560 mm.

The latest user clarification allows one shared via row between nearby RF traces in this region. Twenty-seven magenta shared vias are placed where the required hole clearance to both RF routes is available. Ordinary green rows resume where separate-row space is available. Immediately beside the bond pads, where neither arrangement fits, the approach remains unfenced. All 38 QD pad locations are preserved.

## Explicit via geometry checks

| Item | Saved result |
|---|---:|
| Proposed GND microvias | 1,439 |
| Shared QD microvias included in total | 27 |
| Land / laser hole | 0.25 / 0.10 mm |
| Annular ring | 0.075 mm |
| Layer span | L5-L6 only |
| Nominal trace-centre to via-centre offset | 0.438 mm |
| Nominal row pitch | 0.410 mm |
| Minimum RF copper to laser-hole edge | 0.331217 mm |
| Minimum via land to via land | 0.152744 mm |
| Minimum via land to component pad | 0.201498 mm |

The historical 3W offset means RF copper edge to **laser-hole edge**, not to the via land. The nominal exact value is 0.330 mm. The proposal uses a small geometric margin and checks every via against every RF route and every component pad. Each shared via also passes the clearance checks against both associated RF channels. All sixteen SMP rings use an equal-angle 30-degree grid, radius 0.91 mm, with the escape-axis position omitted symmetrically. Component perimeter fences stay outside pad/body convex hulls. No shield enters the QD bond field or the cavity. No proposed via has paste.

The JSON and CSV were saved, reopened and rechecked before rendering. These checks validate explicit two-dimensional geometry and circuit membership; they do not establish physical GND connectivity, solder-mask geometry, complete DC routing or native DRC.

## Prior JLCPCB order basis

The recorded Y34 order used HDI, six layers, 1-step, 1.6 mm, ENIG 1 microinch, 1 oz outer copper and impedance control ±10%. The RF target was 50 ohms on L6 using W=0.11 mm, coplanar GND gap=0.20 mm and requested stack JLCH06161HN1-1078 with 0.0784 mm outer dielectric. Retain the requested 0.5 oz inner copper basis.

The cart actually saved NP-175F TG170 and 1 oz inner copper with the stack subject to review. Manufacturer acceptance of the requested stack remains outstanding. The cart was not modified for this proposal, and its historical 474-via count does not describe this 1,439-via plan.

JLCPCB's [HDI capability FAQ](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq), checked 2026-10-16, specifies a default 0.10 mm laser hole, at least 0.075 mm blind-via annular ring and a maximum 1:1 dielectric-to-hole aspect ratio. The retained land/hole sizes meet those nominal limits; the requested outer dielectric gives 0.0784/0.10 = 0.784. This is not manufacturer approval of the complete layout or confirmation of 50-ohm impedance after the new curves and component transitions.

## Files

- `Shielded_RF_Overview.png`: complete RF/component proposal.
- `QD_Launch_Shield_Detail.png`: QD shared rows and unfenced pad approaches.
- `Pad_Normal_Entry_Detail.png`: component-boundary and SMP entry detail.
- `shielded_rf_plan.json`: component, route, via and audit data together.
- `shield_geometry_audit.json`: numerical checks, preserved source hashes and individual exceptions.
- `proposed_L5_L6_GND_vias.csv`: explicit proposed via coordinates and span.

Reproduction helpers are in `script/rf_redline_review_20261011/`: `shielded_symmetric_rf_plan_20261016.py` generates the curves; `finalize_shielded_rf_20261016.py` places, audits and renders the vias. Native PCB/schematic, reference boards, Gerbers and the JLCPCB cart remain unchanged.
