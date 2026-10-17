# C/R solder-control margin restoration

Saved native PCB SHA256: `214d65cc0d5debf9ef67c7c31496fe23b06b70147fe2f5511073fe110cb24619`.

All 16 capacitors and 16 resistors retain individual rotated pad-hull masks on the component face, with their nominal margin enlarged from **0.20 to 0.90 mm**. The contours follow the accepted component rotations instead of reverting to axis-aligned pair rectangles. Normal component-pad openings remain unchanged. General Bottom mask area increases from 908.220815 to 1002.915099 mm2 before normal pad apertures. Where the contours overlap, they merge; the exposed QD bond field and mounting lands remain explicit exceptions.

The opposite-face local via covers are unchanged. No component, copper pad, via, track, arc, ground plane, L5 cutout, outline, embedded model or pin assignment changed. All 38 QD pads retain their 0.260 mm width. The earlier six local mask-bridge repairs are retained; one boundary-rounding adjustment adds less than 0.000001 mm2 of protective mask.

## Validation

- Saved/reopened native Altium DRC: **0 violations**, with all 44 rules unchanged.
- All 71 named nets connected; stored connection count 0; compiled schematic membership agrees and enumerated compiler violations are 0.
- 212 preservation/geometry checks pass, including unchanged Top regions, all copper objects, all 1,590 vias, pad geometry, component/model streams and schematic/map hashes.
- All 32 L5 C/R copper cutouts and QD layer exclusions remain.
- Fresh Top/Bottom solder-mask CAM matches the saved regions and normal pad openings within 0.0003 mm; all 22 Top QD vias remain fully covered.
- Fresh paste CAM has exactly 53 Top and 64 Bottom normal SMD apertures. No via, QD, SMP or mounting paste was added.
- [Before/after image](Mask_Before_After.png), [both faces](Corrected_Masks_Both_Faces.png), [native DRC](../../script/rc_mask_margin_20261017/Native_DRC.html). Images use saved geometry and actual native CAM, not a GUI screenshot.

## Via copper-land size question

The user's phrase "hold pad" is interpreted as the via copper land protruding beyond the QD bond pad. This revision does not resize any via. The current 22 QD DC vias have 0.350 mm lands and 0.200 mm holes. They are mechanically drilled through vias; the L5-L6 RF shields are a separate laser-via class.

The [official JLCPCB capability table](https://jlcpcb.com/capabilities/pcb-capabilities), checked on 2026-10-17, requires a via land diameter at least 0.100 mm larger than its hole diameter; 0.150 mm difference is preferred. These correspond to radial annular rings of 0.050 and 0.075 mm. The table separately lists minimum via hole/land geometry of 0.150/0.250 mm. Component PTH annular-ring limits are different and must not be substituted for these via requirements.

| Hole / land (mm) | Radial ring (mm) | Geometry assessment |
|---|---:|---|
| 0.200 / 0.350, current | 0.075 | Meets preferred via diameter difference |
| 0.200 / 0.300 | 0.050 | Meets published minimum; still wider than the 0.260 mm bond pad |
| 0.200 / 0.260 | 0.030 | Fails published minimum |
| 0.150 / 0.250 | 0.050 | Meets published minimum geometry, but changes drilling and requires centre/connection review |

The existing QD via centres are not all centred in their pads. A 0.250 mm land therefore cannot be assumed to fit inside every 0.260 mm pad without checking the lateral and end offsets and rerouting the affected DC terminal connections. Only dimensional feasibility is stated here, not approval of a changed stack, production file or order. No via resizing, new production Gerber release or order/cart change is made by this revision.
