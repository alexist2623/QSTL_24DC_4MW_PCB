# QD bond-pad width increase

Saved native PCB SHA256: `5a5d3a83e164647765685761dfe95143e4bacdde0b8763a326cdc1eebfc5e8ac`.

All 38 QD wire-bond pads now have a **0.260 mm short-axis copper width**, increased from 0.250 mm (+4%). Pad centres, long-axis dimensions, rotations, inner/outer end-midpoint alignment, cavity, all RF/DC routes and electrical membership are preserved. This is an in-plane width change, not a copper-foil thickness change.

The applicable [JLCPCB capability table](https://jlcpcb.com/capabilities/pcb-capabilities), checked on 2026-10-16, specifies 0.150 mm minimum different-net SMD-pad spacing. The saved minimum is **0.152142 mm**. Pads 4/5 and their mirrored 34/35 pair limit a common width. A trial 0.300 mm common width gives only 0.112271 mm spacing and was not applied. The 0.260 mm selection preserves the accepted centres and angles; further significant widening requires revisiting pad placement or shape.

Five GND shield microvias moved by 0.00217..0.005803 mm to retain the existing shield clearance. Approximately 0.085958 mm2 of L6 GND was removed locally around the widened pads. Other layer copper, compact masks, component/model geometry, schematic and pin map are preserved. Recreating the L6 contour introduces only native-coordinate-grid rounding outside the local pad-clearance change; the audit confines that difference to a 3 nm boundary band.

## Saved geometry checks

| Quantity | Minimum saved distance (mm) |
|---|---:|
| QD pad to another QD pad | 0.152142 |
| QD pad to foreign signal trace/via land | 0.154269 |
| QD pad to L6 GND | 0.200492 |
| QD pad to GND shield land | 0.201000 |
| QD pad to blind pocket | 0.208992 |
| Moved shield land to another shield land | 0.154081 |
| Moved shield land to signal-via land | 0.203902 |

All 1,514 GND shields retain their 0.250/0.100 mm land/hole geometry and L5-L6 span. The saved minimum RF-copper-to-shield-hole-edge distance is 0.330010 mm; full L5/L6 ground coverage passes. All 76 DC terminal vias and the single-internal-layer-per-DC routing remain unchanged.

## Remaining via-land protrusion

The 22 DC vias on QD pads retain **0.350 mm lands and 0.200 mm holes**. These lands are wider than the new 0.260 mm pads, so all 22 still protrude outside the rectangular pad outline. A centred land protrudes 0.045 mm on each side. Including existing offsets and the aligned pad ends, maximum edge-normal protrusion is 0.074098 mm. QD pad 29 has 0.073998 mm end protrusion. These are copper-outline protrusions, not claims about physical via height. Enlargement alone does not enclose the existing lands.

Affected pad numbers: 1, 3, 4, 6, 7, 8, 10, 14, 17, 18, 19, 20, 22, 23, 25, 26, 27, 29, 33, 36, 37, 38. Full before/after values are in [Via_Protrusion.csv](Via_Protrusion.csv).

## Native verification

- Save/reopen Altium DRC: **0 violations**, with all 44 rules preserved.
- All 71 named nets connected, stored connection count 0; exact compiled schematic membership and zero enumerated compiler violations. The compiler Boolean historically returns False and is not used as pass evidence.
- All RF/DC tracks/arcs and component/model streams preserved. All 38 pad centres, lengths, rotations and net assignments preserved.
- All 32 persistent L5-only C/R hull cutouts remain free of GND copper; the QD cavity and layer-specific GND exclusions are retained.
- Fresh Top/Bottom solder-mask CAM matches the saved openings and normal SMD apertures; all 22 Top QD via lands remain covered and the central metal/Bottom bond field remain exposed.
- Fresh paste CAM contains exactly 53 Top and 64 Bottom normal SMD apertures, with no extra via, QD, SMP or mechanical-pad paste. Raw native via paste-enable flags alone do not represent effective CAM output.
- [Saved close-up and via protrusion](Saved_Bond_Pad_Width.png) is a render of the actual saved native geometry, not a GUI screenshot. [Native DRC](../../script/bond_pad_width_20261016/Native_DRC.html).

The frozen baseline is under `script/bond_pad_width_20261016/baseline/`. The first native edit attempt invalidated the active pad iterator while modifying pad dimensions; the repaired helper collects all 38 references before editing. Altium was restarted with user authorization, and the completed saved revision was independently checked. This task changes the current PCB document; it does not release new manufacturing Gerbers, update an order/cart or push Git. Overall stack/impedance manufacturing approval remains outside this local geometry verification.
