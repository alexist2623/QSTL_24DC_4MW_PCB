"""Bind the completed RF correction report to the saved native evidence."""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'RF_Entry_Correction_20261016';N='QSTL_QD4_2SET_38PAD'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
reports={name:json.loads((H/name).read_text()) for name in ('saved_native_audit.json','support_audit.json','preservation_audit.json','route_identity_audit.json','preparation_audit.json','fitted_copper_audit.json','c13_native_audit.json')}
assert all(r['passed'] for r in reports.values())
digest=sha(P/(N+'.PcbDoc'));assert reports['saved_native_audit.json']['checks']['native_sha256']==digest
assert reports['support_audit.json']['source_sha256']==digest and reports['preservation_audit.json']['source_sha256']==digest
assert reports['c13_native_audit.json']['source_sha256']==digest
txt=(H/'native_validation.txt').read_text();assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in txt
drc=(H/'Native_DRC.html').read_text();counts=[int(v) for v in re.findall(r'<td class="column2">(\d+)</td>',drc)];assert counts and not any(counts)
metrics=json.loads((H/'saved_local_metrics.json').read_text());m=reports['preparation_audit.json']['metrics']
assert len(m['SMP_entry_continuity'])==32 and max(r['maximum_centre_step_mm'] for r in m['SMP_entry_continuity'])<.421
status=dict(passed=True,PCB_sha256=digest,schematic_sha256=sha(P/(N+'.SchDoc')),pin_map_sha256=sha(P/'pin_mapping.csv'),connected_named_nets=71,stored_connections=0,native_DRC_violations=0,retained_rules=44,shield_vias=m['via_count'],DC_terminal_vias=76,marked_pair_measurements=metrics,SMP_entries_verified=16,ambiguous_SMP_entries_applied=[],C13_rounding=reports['c13_native_audit.json'],rejected_trial='Further movement of QD-side MW28 reduced foreign QD-pad copper clearance to 0.1564 mm. That trial was not applied; saved MW28 QD curve is retained.',evidence={name:dict(path=str((H/name).relative_to(ROOT)),sha256=sha(H/name)) for name in reports})
(OUT/'final_status.json').write_text(json.dumps(status,indent=2))
report=f'''# RF spacing and SMP-entry correction

Implemented in the existing `{N}.PrjPcb` project on 2026-10-16. Saved PCB SHA256: `{digest}`.

## Changed routing

The latest C13 follow-up replaces its compact turn with **one exact native circular arc, R 1.600 mm, 90 degrees**. The route leaves C13 pad 1 normally for 0.750 mm, follows the tangent quarter-circle, and enters SMP13 along a 3.400 mm straight radial segment. Saved arc centre is (13.350, 24.450) mm, with angles 180 to 270 degrees. Only S13 and its local ground/shield/mask geometry changed in this follow-up. All other RF/DC routes are preserved within native coordinate-grid rounding, with maximum measured difference {reports['c13_native_audit.json']['other_saved_routes_max_difference_mm']:.9f} mm; the other fifteen SMP-entry fences are identical. Seventeen local shield vias were replaced with nineteen to follow the broader bend.

The marked lower-left MW13/MW15 pair now has **1.095581 mm** minimum copper-edge spacing in the marked review window, previously **0.197733 mm**. The marked right MW30/MW28 pair now has **0.780813 mm**, previously **0.606079 mm**. QD bond-pad positions are unchanged. These local QD fanout areas still use the previously authorized shared-row exception; they are not presented as meeting the 1.160 mm separate-two-row condition everywhere. Where a via cannot fit at the immediate bond-pad approach, the launch remains unfenced.

All sixteen capacitor-to-SMP paths have a straight radial approach before the signal centre: **3.400 mm for SMP13, 2.400 mm for the other fifteen**. Both shield rows are phased from the symmetric ring endpoints, rather than independently sampled and then left with rejected points. Each side has 6–8 row vias within 3.6 mm of its SMP centre, with maximum neighbouring centre distance **0.420 mm**, including the row-to-ring connection. All sixteen entries passed geometric clearance, saved-geometry identity and native DRC checks; **no unresolved/ambiguous SMP entry was applied**.

The separately explored additional movement of **MW28 near QD** was rejected because it reduced a foreign QD-pad copper gap to 0.1564 mm. Its original QD-side curve remains; widening the right pair was achieved by moving MW30. This is distinct from the verified SMP28 connector entry.

RF width stays 0.110 mm. There are **{m['via_count']:,} solid GND shield microvias**, land/hole 0.250/0.100 mm, exclusively L5–L6. Candidate minimum RF copper to laser-hole-edge distance is **{m['min_RF_copper_to_shield_hole_mm']:.6f} mm**. Candidate checks found minimum shield-land separation {m['min_via_land_gap_mm']:.6f} mm, component-pad-to-shield-land separation {m['min_pad_to_shield_land_mm']:.6f} mm and DC-via-to-shield-land separation {m['min_DC_via_to_shield_land_mm']:.6f} mm. Saved candidate identity and native DRC are checked separately below.

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
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report)
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';text=req.read_text();heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- RF spacing/SMP entry correction completed and saved (2026-10-16): marked MW13/MW15 copper gap 0.197733 -> 1.095581 mm; MW30/MW28 0.606079 -> 0.780813 mm. The authorized shared-row QD exception remains explicit. All sixteen SMP entries were individually verified: 2.400 mm radial launch, both rows joined to the ring with maximum 0.420 mm centre step in the 3.6 mm approach region. No ambiguous SMP entry was applied. The additional QD-side MW28 move failed foreign-pad clearance and was rejected; its original QD curve is retained. Current PCB SHA256 `{digest}`; 1,500 L5-L6 shields, 76 unchanged DC terminal vias, 71 connected nets, zero stored connections/DRC/compiler violations, 44 unchanged rules, fresh normal-only SMD paste. Component/pad/DC/schematic/mapping preservation passes. See [current RF correction report](../../QSTL_QD4_2SET_38PAD/RF_Entry_Correction_20261016/IMPLEMENTATION_REPORT.md). This supersedes earlier current-state hashes and shield counts below.\n'
bullet=f'- C13 rounding completed and saved (2026-10-16): exact native R1.600 mm / 90-degree arc, 0.750 mm normal capacitor launch and 3.400 mm radial SMP13 approach; both shield rows continue into the ring. Only S13 and nearby shields/L5-L6 GND/Bottom mask changed from the preceding RF-spacing revision; all other RF/DC routes and fifteen SMP-entry fences are unchanged. Current PCB SHA256 `{digest}`; {m["via_count"]:,} L5-L6 shields, 76 unchanged DC terminal vias, 71 connected named nets, zero saved connections/DRC/compiler violations and 44 unchanged rules. Fresh paste, masks, model transforms, schematic membership and preservation audits pass. See [C13 image](../../QSTL_QD4_2SET_38PAD/RF_Entry_Correction_20261016/C13_Rounded_Bend.png) and [current report](../../QSTL_QD4_2SET_38PAD/RF_Entry_Correction_20261016/IMPLEMENTATION_REPORT.md). This supersedes the preceding current-state hash/count and its 2.400 mm SMP13 approach.\n'
text=re.sub(r'^- C13 rounding completed and saved .*\n','',text,flags=re.M)
assert heading in text;req.write_text(text.replace(heading,heading+bullet,1))
readme=P/'README.md';text=readme.read_text();start=text.index('The authoritative current PCB SHA256');end=text.index('\n\n',start)
text=text[:start]+f'The authoritative current PCB SHA256 is `{digest}`. The subsequent RF spacing/SMP-entry correction is also saved: see the [current implementation report](RF_Entry_Correction_20261016/IMPLEMENTATION_REPORT.md), [RF before/after image](RF_Entry_Correction_20261016/RF_Before_After.png), [all SMP entries](RF_Entry_Correction_20261016/Saved_All_SMP_Entries.png) and [validation manifest](RF_Entry_Correction_20261016/final_status.json). The central DC geometry is retained. Manufacturing stack acceptance, impedance certification and inherited SMP component-PTH annular-ring review remain separate. No production Gerber release accompanies this revision.'+text[end:]
readme.write_text(text)
print(json.dumps(dict(passed=True,PCB_sha256=digest,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
