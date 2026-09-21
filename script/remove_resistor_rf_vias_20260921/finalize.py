"""Publish current via counts and the saved-board validation revision."""
from pathlib import Path
import json,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';D=P/'docs';v=json.loads((H/'validation.json').read_text());ref=json.loads((H/'refinements_validation.json').read_text());n=json.loads((H/'native_render_snapshot.json').read_text())
assert v['passed'] and ref['passed'] and v['pcb_sha256']==ref['pcb_sha256']==n['source_sha256']
s=(R/'README.md').read_text(encoding='utf-8')
s=s.replace('The remaining 60 through vias comprise 24 QD, 12 resistor and 24 ZIF fanout vias.','The remaining 54 through vias comprise 24 QD, six DC-side resistor and 24 ZIF fanout vias. R1-R6 each have one via on DC pad 2; the six unused RF-side pad 1 vias have been removed. RF pad 1 connects entirely on Bottom, preserving the through-pad RF path without a via stub.')
s=s.replace('and 530 vias','and 524 vias').replace('RC_Mask_Clearance_validation.json','Resistor_RF_Via_Removal_validation.json').replace('RC_Mask_Clearance_DRC.html','Resistor_RF_Via_Removal_DRC.html')
(R/'README.md').write_text(s,encoding='utf-8')
f=R/'script/README.md';s=f.read_text(encoding='utf-8');s=s.replace('Current R/C placement, rectangular-mask and hole-edge shield work is in `rc_mask_clearance_20260921/`.','Current removal of unused resistor RF vias is in `remove_resistor_rf_vias_20260921/`. The preceding R/C placement, rectangular-mask and hole-edge shield work is in `rc_mask_clearance_20260921/`.');f.write_text(s,encoding='utf-8')
shutil.copy2(H/'refinements_validation.json',D/'placement_mask_validation.json')
(D/'resistor_RF_via_removal.json').write_text(json.dumps(dict(pcb_sha256=v['pcb_sha256'],removed=json.loads((H/'plan.json').read_text())['removed_resistor_RF_vias'],remaining_resistor_DC_vias=6,remaining_signal_through_vias=54,shield_vias=470,total_vias=524,DRC_violations=0,connected_nets=37),indent=2))
(H/'README.md').write_text(f'''# Remove unused resistor RF-side vias

Saved original PCB SHA-256: `{v['pcb_sha256']}`.

Removed exactly six 0.50 mm land / 0.25 mm drill through vias, one at RF pad 1 of each R1-R6 (MW1-MW6). The RF path remains on Bottom and passes through the resistor pad centre. Each resistor retains its DC pad 2 via. QD and ZIF vias remain.

Saved counts: 54 signal through vias, 470 L5-L6 GND shield microvias, 524 total vias. All 37 nets are physically connected, with zero stored connection lines and zero violations across 15 enabled native Altium DRC checks after save/reopen.

`before.PcbDoc` is the recovery copy. `prepare.py` and `RemoveRFVias.pas` are one-time scripts guarded against the exact starting revision and six via targets. Only the six vias were removed and GND polygons repoured. Saved component/pad/track/arc/text/fill/net streams and the schematic/library hashes are checked against the baseline. The masks, QD ground exclusions and remaining via locations/spans are validated independently. The requirement is recorded in AGENTS.md and DESIGN_REQUIREMENTS.md to prevent reintroduction.

`audit_connectivity.py`, `verify_final.py`, `verify_refinements.py`, `ReopenAudit.pas` and `AuditPaste.pas` contain validation. `publish_outputs.py` and `finalize.py` refresh previews, documentation and fabrication companion revision hashes. No Git push or supplier submission was performed in this revision.
''',encoding='utf-8')
print('Finalized resistor RF-via removal:',v['pcb_sha256'])
