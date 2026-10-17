"""Publish verified native C/R mask restoration and the via-land-size answer."""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'RC_Mask_Margin_20261017'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
evidence={}
for name in ('compact_audit.json','saved_native_audit.json','support_audit.json','mask_cam_audit.json'):
    r=json.loads((H/name).read_text(encoding='utf-8'));assert r['passed'],name
    assert (r['source_sha256'] if 'source_sha256' in r else r['checks']['native_sha256'])==digest,name
    evidence[name]=dict(passed=True,sha256=sha(H/name))
prep=json.loads((H/'preparation_audit.json').read_text(encoding='utf-8'));render=json.loads((H/'render_manifest.json').read_text(encoding='utf-8'));assert render['source_sha256']==digest
for name,d in render['images'].items():assert sha(OUT/name)==d
drc=(H/'Native_DRC.html').read_text(encoding='utf-8');count=int(re.search(r'Rule Violations:</td>.*?DRC_summary_header_col3[^>]*>(\d+)',drc,re.S)[1]);assert count==0
assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in (H/'native_validation.txt').read_text()
assert (H/'Native_DRC.html').stat().st_mtime>=(H/'apply_log.txt').stat().st_mtime
report=f'''# C/R solder-control margin restoration

Saved native PCB SHA256: `{digest}`.

All 16 capacitors and 16 resistors retain individual rotated pad-hull masks on the component face, with their nominal margin enlarged from **0.20 to 0.90 mm**. The contours follow the accepted component rotations instead of reverting to axis-aligned pair rectangles. Normal component-pad openings remain unchanged. General Bottom mask area increases from {prep['Bottom_mask_area_before_mm2']:.6f} to {prep['Bottom_mask_area_after_mm2']:.6f} mm2 before normal pad apertures. Where the contours overlap, they merge; the exposed QD bond field and mounting lands remain explicit exceptions.

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
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
status=dict(passed=True,PCB_sha256=digest,RC_margin_before_mm=.2,RC_margin_after_mm=.9,Top_mask_unchanged=True,DRC_violations=0,audits=evidence,images=render['images'],report_sha256=sha(OUT/'IMPLEMENTATION_REPORT.md'))
(OUT/'final_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8');heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- C/R solder-control margin restoration verified (2026-10-17): all 32 individual rotated C/R pad-hull mask margins are now 0.90 mm on Bottom, with normal pad openings retained. Top mask regions, all copper/pads/vias/routes, 49 models, all 32 L5 cutouts, schematic and pin map are unchanged. Native save/reopen DRC 0, stored connections 0, 71 connected nets and fresh mask/paste CAM pass. Current PCB `{digest}`; [report](../../QSTL_QD4_2SET_38PAD/RC_Mask_Margin_20261017/IMPLEMENTATION_REPORT.md), [comparison](../../QSTL_QD4_2SET_38PAD/RC_Mask_Margin_20261017/Mask_Before_After.png). The current 0.350/0.200 mm QD via lands/holes remain unchanged; their possible reduction was reviewed only, not authorized or applied. This supersedes previous current-state hashes and the 0.20 mm Bottom C/R mask margin.\n'
s=re.sub(r'^- C/R solder-control margin restoration verified .*\n','',s,flags=re.M);assert heading in s;s=s.replace(heading,heading+bullet,1);req.write_text(s,encoding='utf-8')
readme=P/'README.md';s=readme.read_text(encoding='utf-8');start=s.index('The authoritative current PCB SHA256');end=s.index('\n\n',start)
s=s[:start]+f'The authoritative current PCB SHA256 is `{digest}`. All 32 C/R component-face masks now use individual rotated pad hulls with 0.90 mm margins and normal pad apertures. Top local via covers, all copper, 0.260 mm QD pads, all via dimensions, component positions and electrical mapping are preserved. All 32 L5 C/R cutouts remain. Native saved/reopened DRC is zero and fresh mask/paste CAM passes. See the [current report](RC_Mask_Margin_20261017/IMPLEMENTATION_REPORT.md), [mask comparison](RC_Mask_Margin_20261017/Mask_Before_After.png) and [audit manifest](RC_Mask_Margin_20261017/final_status.json). DC via lands still protrude beyond the rectangular bond pads. No new production Gerber is issued.'+s[end:];readme.write_text(s,encoding='utf-8')
assert sha(pcb)==digest
print(json.dumps(dict(passed=True,PCB_sha256=digest,DRC_violations=0,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
