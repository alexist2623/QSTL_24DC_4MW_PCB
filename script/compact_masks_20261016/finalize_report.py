"""Publish source-bound evidence for the compact solder-mask revision."""
from pathlib import Path
import json,re,hashlib,shutil
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Compact_Masks_20261016'
pcb=P/(P.name+'.PcbDoc');sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();digest=sha(pcb)
evidence={}
for name in ['compact_audit.json','saved_native_audit.json','support_audit.json','mask_cam_audit.json']:
    obj=json.loads((H/name).read_text());assert obj['passed'],name
    assert (obj['source_sha256'] if 'source_sha256' in obj else obj['checks']['native_sha256'])==digest,name
    evidence[name]=dict(sha256=sha(H/name),passed=True)
render=json.loads((H/'render_manifest.json').read_text());assert render['source_sha256']==digest
for name,d in render['images'].items():assert sha(OUT/name)==d
html=(H/'Native_DRC.html').read_text();count=int(re.search(r'Rule Violations:</td>.*?DRC_summary_header_col3[^>]*>(\d+)',html,re.S)[1]);assert count==0
assert 'POST_DRC_SAVED_CONNECTION_COUNT=0' in (H/'native_validation.txt').read_text()
assert (H/'Native_DRC.html').stat().st_mtime>=(H/'apply_log.txt').stat().st_mtime
alignment=json.loads((H/'model_alignment_before.json').read_text());maxerr=max(r['hausdorff_mm'] for r in alignment['rows'])
assert len(alignment['rows'])==32 and maxerr<.00001
prep=json.loads((H/'preparation_audit.json').read_text());area=prep['mask_area_mm2']
report=f'''# Compact solder-mask correction

Saved PCB SHA256: `{digest}`.

The oversized axis-aligned C/R pair rectangles were removed. Each Bottom C/R footprint now uses its own rotated two-pad convex hull with a **0.20 mm** mask margin. The opposite face uses local circular covers extending **0.15 mm beyond each via land**, instead of duplicated C/R rectangles. All 22 Top QD vias are locally covered; the central metal remains exposed. The user-approved RF protection strips, SMP solder-control masks, ZIF protection and normal pad apertures remain. Six mounting lands and the Bottom QD bonding field remain mask-free.

General retained-mask area decreases from {area['37']['before']:.3f} to {area['37']['after']:.3f} mm2 on Top (**{area['37']['reduction_percent']:.1f}%**) and from {area['38']['before']:.3f} to {area['38']['after']:.3f} mm2 on Bottom (**{area['38']['reduction_percent']:.1f}%**), before subtracting normal component-pad apertures. Four genuine native 0.10 mm mask-sliver violations were corrected by trimming only the nearby general openings. Six local boundaries, including two already above 0.10 mm, now target 0.12 mm separation; the total added mask for this repair is only {sum(r['added_mask_area_mm2'] for r in prep['local_sliver_repairs']):.6f} mm2. Rules were not weakened.

All sixteen exact Yageo CC1206JKNPO9BN104 models align with their pad centres and axes. All 32 C/R native body outlines match their expected envelopes to within {maxerr:.9f} mm. Components were not relocated. The maximum capacitor body remains 3.50 x 1.80 x 1.80 mm; all R/C pads and embedded models are byte-for-byte preserved.

## Validation

- Saved/reopened Altium DRC: **0 violations**, 44 unchanged rules.
- All 71 named nets connected; stored connections 0; exact compiled schematic membership and zero enumerated compiler violations.
- Every RF/DC route, pad, via, component/model, nonmask region, outline, schematic and pin map preserved. The native stream and geometric scope checks pass.
- All 32 persistent L5-only C/R hull cutouts remain free of GND copper.
- Fresh native Top/Bottom solder-mask CAM matches the expected openings and normal pad apertures. All 22 Top QD via lands remain fully covered.
- Fresh paste CAM contains exactly 53 Top and 64 Bottom normal SMD apertures, with no extra via, SMP, mounting or QD paste.
- 211 compact-mask/preservation checks pass. RF protection and all component/terminal mask features pass.

## Review images

- [Before and after](Mask_Before_After.png)
- [Both corrected faces](Corrected_Masks_Both_Faces.png)
- [Capacitor pad/model registration](Capacitor_Pad_Registration.png)
- [Native mask output and unchanged L5 cutouts](Solder_Mask_and_L5_Openings.png)
- [Native DRC](../../script/compact_masks_20261016/Native_DRC.html)

Images are renders of saved native geometry and actual native CAM, not GUI screenshots. Both faces use the same XY orientation for comparison. The previous geometry is backed up under `script/compact_masks_20261016/baseline/`. Mask/paste export is for validation only; no production release, order/cart action or Git push is part of this revision.
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
status=dict(passed=True,PCB_sha256=digest,DRC_violations=count,mask_areas=area,audits=evidence,images=render['images'],report_sha256=sha(OUT/'IMPLEMENTATION_REPORT.md'))
(OUT/'final_status.json').write_text(json.dumps(status,indent=2))
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';s=req.read_text();heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- Compact masks implemented and verified (2026-10-16): current PCB `{digest}` uses individual rotated C/R hulls +0.20 mm on Bottom and local via-land covers +0.15 mm on Top, replacing the rejected 0.90 mm pair rectangles and broad QD frame. General Top/Bottom mask areas decrease {area["37"]["reduction_percent"]:.1f}%/{area["38"]["reduction_percent"]:.1f}%. RF strips, SMP/ZIF masks, normal pad apertures and exposed mounting/QD fields remain. Four native mask-sliver failures were repaired locally; final saved/reopened DRC is zero with 44 unchanged rules. Copper/routes, 32 L5 C/R cutouts, component/model geometry, schematic and mapping are unchanged; 71 nets connected, stored connections zero, fresh mask/paste CAM passes. See [report](../../QSTL_QD4_2SET_38PAD/Compact_Masks_20261016/IMPLEMENTATION_REPORT.md) and [comparison](../../QSTL_QD4_2SET_38PAD/Compact_Masks_20261016/Mask_Before_After.png). This is the current state and supersedes earlier mask dimensions and hashes below.\n'
s=re.sub(r'^- Compact masks implemented and verified .*\n','',s,flags=re.M);assert heading in s;req.write_text(s.replace(heading,heading+bullet,1),encoding='utf-8')
readme=P/'README.md';s=readme.read_text();start=s.index('The authoritative current PCB SHA256');end=s.index('\n\n',start)
s=s[:start]+f'The authoritative current PCB SHA256 is `{digest}`. Compact solder masks replace the oversized C/R rectangles and opposite-face patches: rotated C/R hull +0.20 mm on Bottom, local via-land covers +0.15 mm on Top. Component registration, all copper/routes, mapping and all 32 L5 C/R cutouts are preserved. Saved/reopened native DRC is zero. See the [current report](Compact_Masks_20261016/IMPLEMENTATION_REPORT.md), [before/after](Compact_Masks_20261016/Mask_Before_After.png), [both faces](Compact_Masks_20261016/Corrected_Masks_Both_Faces.png) and [audit manifest](Compact_Masks_20261016/final_status.json). The earlier thirteen SMP-entry roundings and retained C13/SMP02/SMP24 remain unchanged. No new production Gerber is issued.'+s[end:];readme.write_text(s,encoding='utf-8')
assert sha(pcb)==digest
print(json.dumps(dict(passed=True,PCB_sha256=digest,DRC_violations=count,report=str(OUT/'IMPLEMENTATION_REPORT.md')),indent=2))
