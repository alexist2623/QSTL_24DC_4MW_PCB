"""Record the saved resistor mesh correction and native visual verification."""
from pathlib import Path
import json,hashlib,re
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Resistor_Models_20261017'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();pcb=P/(P.name+'.PcbDoc');digest=sha(pcb)
a=json.loads((H/'audit.json').read_text());assert a['passed'] and a['source_sha256']==digest
photo=OUT/'Altium_RC_Models_Corrected.png';assert photo.stat().st_size>10000
rows=[r for r in a['RC_axis_checks'] if r['changed']]
table='\n'.join(f"| {r['ref']} | {r['model_Z_before_deg']:g} | {r['model_Z_after_deg']:g} |" for r in rows)
report=f'''# Resistor 3D registration correction

Current saved PCB SHA256: `{digest}`.

Eight tilted Bottom resistor meshes retained the same incorrect rotation sign previously found in the capacitors. The capacitor-only correction did not change these resistors. This follow-up corrects their model Z rotations without moving their copper footprints or component origins.

| Reference | Previous model Z (degrees) | Corrected model Z (degrees) |
|---|---:|---:|
{table}

All 16 resistor and 16 capacitor projected long axes now agree with their two-pad axes within 0.000051 degrees, and each model remains centred between its pads. This includes the previously corrected capacitors. Actual Altium 3D inspection after save/reopen confirmed their terminals line up with the pads. The 0603 resistor geometry, 0.45 mm height and embedded STEP content are unchanged.

- [Saved and reopened Altium 3D view](Altium_RC_Models_Corrected.png)
- [Native view before resistor correction](Altium_Resistors_Before.png)

## Validation

- Native save/reopen DRC: **0 violations**; stored unconnected objects: **0**.
- {len(a['checks'])} preservation/model checks passed. Only eight resistor model Z fields changed in both native body representations; all other 41 model instances, including all 16 capacitors, retain their transforms and embedded geometry.
- Pad, track, arc, via, region, component, net, rule and physical layer-stack streams are byte-identical to the validated baseline. All 44 design rules are unchanged.
- The 22 QD via lands remain nominal 0.300 mm with 0.200 mm drills; all 1,590 vias and 1,514 L5-L6 shield vias are unchanged.
- The schematic and pin mapping are byte-identical. All 71-net connectivity, one-layer-per-DC-net routing and RF signal-via exclusions from the validated baseline remain applicable because every electrical geometry and net stream is unchanged.
- All mask/paste-driving pad, via, region and rule data are unchanged. The baseline's verified normal paste apertures (53 Top / 64 Bottom), absence of via/QD/SMP/mounting paste, 0.90 mm C/R masks, QD mask openings and all 32 L5 C/R copper cutouts therefore remain. This mesh-only update does not generate new manufacturing CAM.
- Native save serialization also updates model indexing, save-time metadata and unused text buffer bytes; text strings and geometric fields remain unchanged. Embedded STEP identity was checked by decompressed content hashes rather than model stream indices.

[Native DRC](../../script/resistor_models_20261017/Native_DRC.html), [saved audit](../../script/resistor_models_20261017/audit.json), [serialization audit](../../script/resistor_models_20261017/serialization.json).
'''
(OUT/'IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
(OUT/'final_status.json').write_text(json.dumps(dict(passed=True,PCB_sha256=digest,changed_resistor_models=8,RC_instances_checked=32,native_3D_after_reopen_checked=True,DRC_violations=0,stored_connections=0,audit_sha256=sha(H/'audit.json'),photo_sha256=sha(photo)),indent=2))
req=ROOT/'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8');heading='## All sixteen R/C placement plan requested 2026-10-16\n\n'
bullet=f'- Resistor 3D registration correction verified (2026-10-17): corrected the model Z rotations of R09/R11/R12/R16/R28/R30/R31/R35 for Bottom rendering. All 16 resistor and 16 capacitor body axes now match their two-pad axes, and all were visually verified in native Altium 3D after save/reopen. Embedded model geometry/heights/origins, corrected capacitor transforms, every copper/pad/via/mask/net/rule/stack stream, schematic and map are preserved. Native DRC 0 and stored connections 0; {len(a["checks"])} saved checks pass. Current PCB `{digest}`; [report](../../QSTL_QD4_2SET_38PAD/Resistor_Models_20261017/IMPLEMENTATION_REPORT.md), [actual 3D](../../QSTL_QD4_2SET_38PAD/Resistor_Models_20261017/Altium_RC_Models_Corrected.png). This supersedes prior current-state hashes and any implication that the earlier capacitor-only correction also corrected the resistors.\n'
s=re.sub(r'^- Resistor 3D registration correction verified .*\n','',s,flags=re.M);assert heading in s;req.write_text(s.replace(heading,heading+bullet,1),encoding='utf-8')
readme=P/'README.md';s=readme.read_text(encoding='utf-8');start=s.index('The authoritative current PCB SHA256');end=s.index('\n\n',start)
current=f'The authoritative current PCB SHA256 is `{digest}`. All 16 resistor and 16 capacitor model axes are now aligned with their pad axes and were checked in native Altium 3D after save/reopen. The latest change corrects eight tilted resistor Z rotations; copper footprints/routes, all vias, masks, 32 L5 openings, schematic and mapping are unchanged. QD via lands remain 0.300 mm with 0.200 mm drills; QD pad widths remain 0.260 mm and C/R mask margins remain 0.90 mm. Native DRC and stored connection counts are zero. See the [current report](Resistor_Models_20261017/IMPLEMENTATION_REPORT.md), [actual Altium 3D view](Resistor_Models_20261017/Altium_RC_Models_Corrected.png) and [manifest](Resistor_Models_20261017/final_status.json). No new production Gerber is issued.'
readme.write_text(s[:start]+current+s[end:],encoding='utf-8')
assert sha(pcb)==digest
print(json.dumps(dict(passed=True,PCB_sha256=digest,photo=str(photo)),indent=2))
