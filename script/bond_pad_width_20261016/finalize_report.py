"""Publish source-bound verification of the saved QD pad width increase."""
from pathlib import Path
import json,re,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Bond_Pad_Width_20261017'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
evidence={}
for name in ('width_audit.json','saved_native_audit.json','support_audit.json','mask_cam_audit.json'):
    obj=json.loads((H/name).read_text());assert obj['passed'],name
    assert (obj['source_sha256'] if 'source_sha256' in obj else obj['checks']['native_sha256'])==digest,name
    evidence[name]=dict(passed=True,sha256=sha(H/name))
width=json.loads((H/'width_audit.json').read_text());m=width['minima']
prep=json.loads((H/'preparation_audit.json').read_text());protrusion=json.loads((H/'via_protrusion.json').read_text());assert protrusion['source_sha256']==digest
render=json.loads((H/'render_manifest.json').read_text());assert render['source_sha256']==digest
for name,d in render['images'].items():assert sha(OUT/name)==d
count=int(re.search(r'Rule Violations:</td>.*?DRC_summary_header_col3[^>]*>(\d+)',(H/'Native_DRC.html').read_text(),re.S)[1]);assert count==0
assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in (H/'native_validation.txt').read_text()
assert (H/'Native_DRC.html').stat().st_mtime>=(H/'apply_log.txt').stat().st_mtime
report=f'''# QD bond-pad width increase

Saved native PCB SHA256: `{digest}`.

All 38 QD wire-bond pads now have a **0.260 mm short-axis copper width**, increased from 0.250 mm (+4%). Pad centres, long-axis dimensions, rotations, inner/outer end-midpoint alignment, cavity, all RF/DC routes and electrical membership are preserved. This is an in-plane width change, not a copper-foil thickness change.

The applicable [JLCPCB capability table](https://jlcpcb.com/capabilities/pcb-capabilities), checked on 2026-10-16, specifies 0.150 mm minimum different-net SMD-pad spacing. The saved minimum is **{m['pad_to_pad_mm']:.6f} mm**. Pads 4/5 and their mirrored 34/35 pair limit a common width. A trial 0.300 mm common width gives only 0.112271 mm spacing and was not applied. The 0.260 mm selection preserves the accepted centres and angles; further significant widening requires revisiting pad placement or shape.

Five GND shield microvias moved by 0.00217..{prep['max_shift_mm']:.6f} mm to retain the existing shield clearance. Approximately {prep['L6_removed_ground_mm2']:.6f} mm2 of L6 GND was removed locally around the widened pads. Other layer copper, compact masks, component/model geometry, schematic and pin map are preserved. Recreating the L6 contour introduces only native-coordinate-grid rounding outside the local pad-clearance change; the audit confines that difference to a 3 nm boundary band.

## Saved geometry checks

| Quantity | Minimum saved distance (mm) |
|---|---:|
| QD pad to another QD pad | {m['pad_to_pad_mm']:.6f} |
| QD pad to foreign signal trace/via land | {m['pad_to_foreign_signal_mm']:.6f} |
| QD pad to L6 GND | {m['pad_to_L6_ground_mm']:.6f} |
| QD pad to GND shield land | {m['pad_to_shield_land_mm']:.6f} |
| QD pad to blind pocket | {m['pad_to_pocket_mm']:.6f} |
| Moved shield land to another shield land | {m['moved_shield_to_shield_land_mm']:.6f} |
| Moved shield land to signal-via land | {m['moved_shield_to_signal_via_land_mm']:.6f} |

All 1,514 GND shields retain their 0.250/0.100 mm land/hole geometry and L5-L6 span. The saved minimum RF-copper-to-shield-hole-edge distance is 0.330010 mm; full L5/L6 ground coverage passes. All 76 DC terminal vias and the single-internal-layer-per-DC routing remain unchanged.

## Remaining via-land protrusion

The 22 DC vias on QD pads retain **0.350 mm lands and 0.200 mm holes**. These lands are wider than the new 0.260 mm pads, so all 22 still protrude outside the rectangular pad outline. A centred land protrudes 0.045 mm on each side. Including existing offsets and the aligned pad ends, maximum edge-normal protrusion is {max(r['after_protrusion_mm'] for r in protrusion['rows']):.6f} mm. QD pad 29 has 0.073998 mm end protrusion. These are copper-outline protrusions, not claims about physical via height. Enlargement alone does not enclose the existing lands.

Affected pad numbers: {', '.join(r['pad'] for r in protrusion['rows'])}. Full before/after values are in [Via_Protrusion.csv](Via_Protrusion.csv).

## Native verification

- Save/reopen Altium DRC: **0 violations**, with all 44 rules preserved.
- All 71 named nets connected, stored connection count 0; exact compiled schematic membership and zero enumerated compiler violations. The compiler Boolean historically returns False and is not used as pass evidence.
- All RF/DC tracks/arcs and component/model streams preserved. All 38 pad centres, lengths, rotations and net assignments preserved.
- All 32 persistent L5-only C/R hull cutouts remain free of GND copper; the QD cavity and layer-specific GND exclusions are retained.
- Fresh Top/Bottom solder-mask CAM matches the saved openings and normal SMD apertures; all 22 Top QD via lands remain covered and the central metal/Bottom bond field remain exposed.
- Fresh paste CAM contains exactly 53 Top and 64 Bottom normal SMD apertures, with no extra via, QD, SMP or mechanical-pad paste. Raw native via paste-enable flags alone do not represent effective CAM output.
- [Saved close-up and via protrusion](Saved_Bond_Pad_Width.png) is a render of the actual saved native geometry, not a GUI screenshot. [Native DRC](../../script/bond_pad_width_20261016/Native_DRC.html).

The frozen baseline is under `script/bond_pad_width_20261016/baseline/`. The first native edit attempt invalidated the active pad iterator while modifying pad dimensions; the repaired helper collects all 38 references before editing. Altium was restarted with user authorization, and the completed saved revision was independently checked. This task changes the current PCB document; it does not release new manufacturing Gerbers, update an order/cart or push Git. Overall stack/impedance manufacturing approval remains outside this local geometry verification.
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
status=dict(passed=True,PCB_sha256=digest,pad_width_before_mm=.25,pad_width_after_mm=.26,DRC_violations=count,minima=m,remaining_protruding_DC_vias=22,audits=evidence,images=render['images'],report_sha256=sha(OUT/'IMPLEMENTATION_REPORT.md'))
(OUT/'final_status.json').write_text(json.dumps(status,indent=2))
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';s=req.read_text();heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- Bond-pad widening implemented and verified (2026-10-17): all 38 current QD pad short-axis widths are 0.260 mm, increased from 0.250 mm; centres, lengths, rotations, aligned end midpoints and mapping are preserved. Saved minimum pad spacing {m["pad_to_pad_mm"]:.6f} mm exceeds JLCPCB 0.150 mm; minimum pad-to-foreign-signal gap {m["pad_to_foreign_signal_mm"]:.6f} mm. Five L5-L6 shields move at most {prep["max_shift_mm"]:.6f} mm and L6 GND is locally cleared to preserve 0.200 mm pad clearance. All routes, 76 DC vias, compact masks, 32 L5 C/R cutouts, embedded models, schematic and mapping remain. Saved/reopened DRC 0, stored connections 0, all 71 nets connected, 44 unchanged rules and fresh mask/paste CAM pass. The 22 QD DC via lands remain wider than the pads (0.350 mm vs 0.260 mm), so copper protrusion remains and must not be reported as eliminated. Current PCB `{digest}`; [report](../../QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/IMPLEMENTATION_REPORT.md), [image](../../QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/Saved_Bond_Pad_Width.png). This supersedes previous current-state hashes; compact-mask requirements remain.\n'
s=re.sub(r'^- Bond-pad widening implemented and verified .*\n','',s,flags=re.M);assert heading in s;s=s.replace(heading,heading+bullet,1);s=s.replace('Updated 2026-10-16.','Updated 2026-10-17.',1);req.write_text(s,encoding='utf-8')
readme=P/'README.md';s=readme.read_text();start=s.index('The authoritative current PCB SHA256');end=s.index('\n\n',start)
s=s[:start]+f'The authoritative current PCB SHA256 is `{digest}`. All 38 QD bond pads now have 0.260 mm short-axis width, with a saved minimum pad gap of {m["pad_to_pad_mm"]:.6f} mm. Pad centres, lengths, rotations, mapping and RF/DC routes are preserved; five local shield vias and local L6 clearance are adjusted. Native save/reopen DRC is zero. Compact masks and all 32 L5 C/R cutouts remain. DC via lands still protrude beyond the rectangular pads. See the [current report](Bond_Pad_Width_20261017/IMPLEMENTATION_REPORT.md), [saved close-up](Bond_Pad_Width_20261017/Saved_Bond_Pad_Width.png) and [audit manifest](Bond_Pad_Width_20261017/final_status.json). No new production Gerber is issued.'+s[end:];readme.write_text(s,encoding='utf-8')
assert sha(pcb)==digest
print(json.dumps(dict(passed=True,PCB_sha256=digest,DRC_violations=count,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
