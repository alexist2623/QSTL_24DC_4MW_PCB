# RF spacing and SMP-entry correction

Implemented in the existing `QSTL_QD4_2SET_38PAD.PrjPcb` project on 2026-10-16. Saved PCB SHA256: `8b8002cfa465c2b7ff8a1c57299817a78393ef0a3739fe9d5962aed1a692bdd5`.

## Changed routing

The latest C13 follow-up replaces its compact turn with **one exact native circular arc, R 1.600 mm, 90 degrees**. The route leaves C13 pad 1 normally for 0.750 mm, follows the tangent quarter-circle, and enters SMP13 along a 3.400 mm straight radial segment. Saved arc centre is (13.350, 24.450) mm, with angles 180 to 270 degrees. Only S13 and its local ground/shield/mask geometry changed in this follow-up. All other RF/DC routes are preserved within native coordinate-grid rounding, with maximum measured difference 0.000000000 mm; the other fifteen SMP-entry fences are identical. Seventeen local shield vias were replaced with nineteen to follow the broader bend.

The marked lower-left MW13/MW15 pair now has **1.095581 mm** minimum copper-edge spacing in the marked review window, previously **0.197733 mm**. The marked right MW30/MW28 pair now has **0.780813 mm**, previously **0.606079 mm**. QD bond-pad positions are unchanged. These local QD fanout areas still use the previously authorized shared-row exception; they are not presented as meeting the 1.160 mm separate-two-row condition everywhere. Where a via cannot fit at the immediate bond-pad approach, the launch remains unfenced.

All sixteen capacitor-to-SMP paths have a straight radial approach before the signal centre: **3.400 mm for SMP13, 2.400 mm for the other fifteen**. Both shield rows are phased from the symmetric ring endpoints, rather than independently sampled and then left with rejected points. Each side has 6–8 row vias within 3.6 mm of its SMP centre, with maximum neighbouring centre distance **0.420 mm**, including the row-to-ring connection. All sixteen entries passed geometric clearance, saved-geometry identity and native DRC checks; **no unresolved/ambiguous SMP entry was applied**.

The separately explored additional movement of **MW28 near QD** was rejected because it reduced a foreign QD-pad copper gap to 0.1564 mm. Its original QD-side curve remains; widening the right pair was achieved by moving MW30. This is distinct from the verified SMP28 connector entry.

RF width stays 0.110 mm. There are **1,502 solid GND shield microvias**, land/hole 0.250/0.100 mm, exclusively L5–L6. Candidate minimum RF copper to laser-hole-edge distance is **0.331217 mm**. Candidate checks found minimum shield-land separation 0.152204 mm, component-pad-to-shield-land separation 0.201498 mm and DC-via-to-shield-land separation 0.203373 mm. Saved candidate identity and native DRC are checked separately below.

## Retained design

- All component positions, all 241 pads, board/mounting geometry and 49 embedded 3D model geometries/transforms are retained.
- All 38 DC connections remain centralized on L2/L3, nineteen nets each. Actual saved non-RF routing is geometrically identical to the baseline; all 76 terminal DC vias and schematic/pin mapping are unchanged.
- L1/L2/L3/L4 GND and Top mask are unchanged. L5/L6 ground and Bottom RF protection were regenerated around the revised geometry. QD ground exclusions, the Bottom blind pocket, the Top exposed centre and protected QD vias remain valid.
- Normal SMD paste remains 53 Top and 64 Bottom apertures. Fresh native CAM confirms no additional via, SMP, mounting or QD paste.

## Saved native verification

All **71 named nets** are connected in the independently reconstructed saved-copper graph. Native saved/reopened connection count is **0**, enabled-rule DRC violations **0**, and compiled schematic violations **0** with exact pin membership. All **44 rules** are retained unchanged. A stale 42-line connection cache was resolved through Altium's native net rebuild, then saved/reopened and rechecked; no connection objects or genuine failures were manually suppressed.

The native fitted route centreline differs from the checked candidate by at most 0.000102 mm, within the reader's 0.000100 mm arc tessellation bound plus coordinate-grid tolerance. These checks verify geometry/connectivity, not an EM simulation or a new manufacturing impedance approval. No new production Gerber or cart update accompanies this revision.

## Images and evidence

- [Saved C13 broad-radius bend](C13_Rounded_Bend.png)
- [C13 bend before/after](C13_Rounded_Bend_Before_After.png)
- [Saved before/after RF close-ups](RF_Before_After.png)
- [All sixteen saved SMP entries](Saved_All_SMP_Entries.png)
- [Saved RF and DC layers](Saved_RF_DC_Layers.png)
- [Final source-bound audit manifest](final_status.json)
- [Native DRC report](../../script/rf_entry_shield_fix_20261016/Native_DRC.html)

The canonical candidate, scripts, measurements and native evidence for this revision are in `script/rf_entry_shield_fix_20261016/`. Earlier `Native_Applied_20261016` images and audits document the preceding central-DC revision.
