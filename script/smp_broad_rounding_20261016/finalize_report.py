"""Publish source-bound evidence only after all saved-native checks pass."""
from pathlib import Path
import hashlib,json,re
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name;OUT=P/'SMP_Rounded_Entries_20261016';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=('saved_native_audit.json','support_audit.json','preservation_audit.json','route_identity_audit.json','preparation_audit.json','fitted_copper_audit.json','native_scope_audit.json','l5_rc_openings_audit.json','mask_detail_audit.json','mask_cam_audit.json')
reports={n:json.loads((H/n).read_text()) for n in names};assert all(r['passed'] for r in reports.values())
digest=sha(P/(N+'.PcbDoc'));assert reports['saved_native_audit.json']['checks']['native_sha256']==digest
for n in ('support_audit.json','preservation_audit.json','native_scope_audit.json'):assert reports[n]['source_sha256']==digest
assert reports['l5_rc_openings_audit.json']['pcb_sha256']==digest
for n in ('mask_detail_audit.json','mask_cam_audit.json'):assert reports[n]['source_sha256']==digest
assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in (H/'native_validation.txt').read_text()
counts=[int(v) for v in re.findall(r'<td class="column2">(\d+)</td>',(H/'Native_DRC.html').read_text())];assert counts and not any(counts)
routes=json.loads((H/'entry_routes.json').read_text());m=reports['preparation_audit.json']['metrics'];scope=reports['native_scope_audit.json']
assert len(routes['changed_entries'])==13 and set(routes['uncertain_entries'])=={'SMP02','SMP24'}
assert max(v['maximum_centre_step_mm'] for v in m['SMP_entry_continuity'])<.421
status=dict(passed=True,PCB_sha256=digest,schematic_sha256=sha(P/(N+'.SchDoc')),pin_map_sha256=sha(P/'pin_mapping.csv'),changed_entries=routes['changed_entries'],retained_ambiguous_entries=routes['uncertain_entries'],preserved_C13=True,connected_named_nets=71,stored_connections=0,native_DRC_violations=0,retained_rules=44,shield_vias=m['via_count'],DC_terminal_vias=76,entry_geometry=routes['entry_report'],evidence={n:dict(path=str((H/n).relative_to(ROOT)),sha256=sha(H/n)) for n in names})
status.update(L5_individual_component_voids=32,QD_Top_masked_vias=22,native_mask_CAM_verified=True)
(OUT/'final_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
report=f'''# Broad circular SMP approaches

Implemented in the existing `{N}.PrjPcb` project on 2026-10-16. Saved PCB SHA256: `{digest}`.

## Applied and retained entries

Thirteen additional capacitor-to-SMP paths were revised. SMP34, SMP32, SMP35, SMP31, SMP05, SMP21, SMP12, SMP16 and SMP15 now use a single native circular arc of **R 1.600 mm**. SMP09, SMP30, SMP11 and SMP28 use two tangent native arcs of **R 1.400 mm**, with a straight connection between the arcs. These four need an S bend because the capacitor launch direction and the retained radial SMP approach do not permit the same one-arc geometry. All line/arc joins are tangent; launches are normal to the capacitor pad and SMP signal boundary. The accepted C13 R1.600 mm quarter-circle is retained exactly.

**SMP02 and SMP24 are unchanged**, including their RF routes and local shielding. Trial broader turns approached mounting lands A4 and A3 closely enough to interrupt their outer shield rows. The trials were rejected before native application. The original two entries remain in the saved design under the user's instruction to retain and report uncertain entries. This is a limitation of the checked candidates, not proof that no different future geometry could fit.

The modified entries remain mirror-symmetric about X=9.75 mm. Their terminal positions, R/C/SMP/QD footprints and electrical mappings did not move. Straight radial SMP approaches range from 1.600 to 3.400 mm depending on the broad curve; the two-sided fence continuity, rather than an arbitrary fixed straight length, was verified explicitly.

## Shielding, preserved routing and surfaces

RF width is 0.110 mm. The final board contains **{m['via_count']:,} GND shield microvias**, land/hole 0.250/0.100 mm, exclusively between L5 and L6. Both rows connect to every SMP ring with maximum centre-to-centre step **0.420 mm** in the measured 3.6 mm approach zone. No RF signal vias were added.

Candidate minima are RF copper to shield-hole edge {m['min_RF_copper_to_shield_hole_mm']:.6f} mm, shield land to shield land {m['min_via_land_gap_mm']:.6f} mm, component pad to shield land {m['min_pad_to_shield_land_mm']:.6f} mm, and DC terminal-via land to shield land {m['min_DC_via_to_shield_land_mm']:.6f} mm. Full L5/L6 land coverage is checked. Saved route/shield identity and native DRC independently verify the applied geometry.

QD-side RF and all centralized L2/L3 DC routes are preserved. All 76 terminal DC vias, 241 pads, 50 components, 49 embedded model geometries/transforms, schematic membership, pin map, board/mounting/cavity geometry, L1-L4 ground and Top mask are retained. L5/L6 ground and Bottom mask were regenerated locally around the revised RF paths. Protected C13/SMP02/SMP24 RF and fence geometry matches the previous saved revision. The maximum saved difference among preserved routes is {scope['saved_preserved_routes_max_difference_mm']:.9f} mm.

The earlier close QD-pair correction remains: MW13/MW15 gap 1.095581 mm and MW30/MW28 gap 0.780813 mm in their review windows, with the authorized short shared-fence QD exception. This revision does not change that exception.

## Saved native validation

- The omitted L5 C/R openings were restored after the user's reminder. All 32 individual two-pad convex hulls, including their inter-pad bridges, are now free of L5 GND copper. Persistent native L5-only cutout objects retain these exclusions during a future repour. No intentional margin was added beyond outward native-grid rounding. Approximately 149.803126 mm2 of L5 copper was removed, with all shield lands still covered. The separate L5 correction preserved every RF/DC route and all other layer regions exactly.
- Actual native Top/Bottom solder-mask CAM matches the saved general openings plus normal component-pad apertures, within 0.0003 mm CAM tolerance. The 91 feature checks cover all RF protection strips, SMP and 0.90 mm R/C control masks, the ZIF mask rectangles, and all 22 Top QD via covers. The central Top metal rectangle and Bottom QD bonding field remain exposed.
- 71 named nets connected in the independently reconstructed saved copper graph.
- Stored connection count 0 after native rebuild and save/reopen.
- Enabled native DRC violations 0; all 44 rules retained.
- Exact compiled schematic pin membership, zero enumerated compiler violations.
- Fresh native paste CAM: 53 Top and 64 Bottom normal SMD apertures, no extra via/SMP/mounting/QD paste.
- QD exclusions, solder-mask protection/openings and all embedded model transforms checked.

The native net rebuild resolves stale connection-cache entries; no connection objects or genuine DRC failures are suppressed. The native compiler Boolean return remains historically unreliable, so its enumerated membership and violation list are checked. These are geometry/connectivity checks, not EM simulation or new impedance/manufacturing approval. L5 reference removal beneath the component footprints is intentional; its local impedance effect has not been field-solver validated. No new production Gerber, cart update or Git push is included. The local mask/paste exports are verification-only files.

## Images

- [Whole RF board](Saved_RF_Whole_Board.png)
- [Actual mask output and all 32 L5 openings](Solder_Mask_and_L5_Openings.png)
- [Whole RF and DC layers](Saved_RF_DC_Layers.png)
- [All sixteen capacitor-to-SMP paths](Saved_All_SMP_Entries.png)
- [Unchanged SMP02/SMP24 and rejected broad-turn overlays](Unchanged_SMP02_SMP24.png)
- [Evidence manifest](final_status.json)
- [Native DRC](../../script/smp_broad_rounding_20261016/Native_DRC.html)

Scripts, the preceding native backup, candidate geometry and audits are in `script/smp_broad_rounding_20261016/`.
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';text=req.read_text();heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- Other SMP rounding completed (2026-10-16): thirteen entries revised; nine use one R1.600 mm circle and SMP09/30/11/28 use two tangent R1.400 mm circles. Accepted C13 is retained. SMP02/24 and their shields remain unchanged because trial broad turns could not retain continuous outer rows beside A4/A3 mounting lands. All QD-side RF/DC, component/pad/mapping geometry and protected entries are preserved. Current PCB SHA256 `{digest}`; {m["via_count"]:,} L5-L6 shields, 76 DC terminal vias, 71 connected nets, zero saved connections/native DRC/compiler violations, 44 unchanged rules, fresh paste/mask/model checks passed. See [current report](../../QSTL_QD4_2SET_38PAD/SMP_Rounded_Entries_20261016/IMPLEMENTATION_REPORT.md) and [whole RF image](../../QSTL_QD4_2SET_38PAD/SMP_Rounded_Entries_20261016/Saved_RF_Whole_Board.png). This supersedes older current-state hashes and shield counts below.\n'
text=re.sub(r'^- Other SMP rounding completed .*\n','',text,flags=re.M);assert heading in text;req.write_text(text.replace(heading,heading+bullet,1),encoding='utf-8')
text=req.read_text();l5bullet=f'- L5 C/R and mask verification completed (2026-10-16): saved PCB `{digest}` contains 32 persistent L5-only individual two-pad hull cutouts, zero remaining GND copper inside every hull, and full L5/L6 shield-land coverage. The L5 correction preserves all routes and other layer regions. Native solder-mask CAM matches the saved openings and normal pad apertures; 91 feature checks pass, including all 22 Top QD via covers, exposed Top centre/Bottom bond field, RF strips, SMP/R/C/ZIF masks. This supersedes the previously missing sixteen-pair openings.\n';text=re.sub(r'^- L5 C/R and mask verification completed .*\n','',text,flags=re.M);req.write_text(text.replace(heading,heading+l5bullet,1),encoding='utf-8')
readme=P/'README.md';text=readme.read_text();start=text.index('The authoritative current PCB SHA256');end=text.index('\n\n',start)
text=text[:start]+f'The authoritative current PCB SHA256 is `{digest}`. The latest broad SMP rounding is saved: thirteen additional entries changed, C13 retained, SMP02/24 retained due to uncertain outer shield clearance near A4/A3. See the [current report](SMP_Rounded_Entries_20261016/IMPLEMENTATION_REPORT.md), [whole RF board](SMP_Rounded_Entries_20261016/Saved_RF_Whole_Board.png), [entry images](SMP_Rounded_Entries_20261016/Saved_All_SMP_Entries.png) and [audit manifest](SMP_Rounded_Entries_20261016/final_status.json). QD-side RF, centralized DC and schematic mapping are retained. Manufacturing stack acceptance, impedance certification and inherited SMP PTH annular-ring review remain separate; no new production Gerber is issued.'+text[end:];readme.write_text(text,encoding='utf-8')
print(json.dumps(dict(passed=True,PCB_sha256=digest,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
