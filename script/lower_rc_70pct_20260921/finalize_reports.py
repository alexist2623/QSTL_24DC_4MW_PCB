"""Publish current revision pointers after all saved-board audits pass."""
from pathlib import Path
import json,shutil,hashlib
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';D=P/'docs'
v=json.loads((H/'validation.json').read_text());requested=json.loads((H/'requested_validation.json').read_text());refined=json.loads((H/'refinements_validation.json').read_text());n=json.loads((H/'native_render_snapshot.json').read_text())
assert all(x['passed'] and x['pcb_sha256']==v['pcb_sha256'] for x in (v,requested,refined))
assert hashlib.sha256((P/'QSTL_24DC_4MW_PCB.PcbDoc').read_bytes()).hexdigest()==v['pcb_sha256']==n['source_sha256']
shutil.copy2(H/'refinements_validation.json',D/'placement_mask_validation.json')
shutil.copy2(H/'requested_validation.json',D/'lower_RC_70pct_placement.json')
f=R/'README.md';s=f.read_text(encoding='utf-8')
s=s.replace('There are 470 solid GND shield vias: 236 along RF routes, 168 around R/C groups, and 66 in SMP signal rings.','There are 480 solid GND shield vias: 243 along RF routes, 171 around R/C groups, and 66 in SMP signal rings.')
s=s.replace('The remaining 54 through vias comprise 24 QD, six DC-side resistor and 24 ZIF fanout vias.','The remaining 48 through vias comprise 18 QD DC, six DC-side resistor and 24 ZIF fanout vias. QD RF pads 1/6/9/12/18/24 have no vias because their signals stay on Bottom.')
old='Both lower pairs moved upward by 1.0 mm; R1/C1 additionally moved 0.35 mm toward the board centre. RF/DC endpoints and existing resistor vias moved with the components. No DC layer-transition vias were added.'
new='After the earlier upward and inward adjustments, both lower pairs now sit at 70% of their previous distance from the X=9.75 mm board centreline. R1/C1 moved another 1.365001 mm inward, and R5/C5 another 1.470000 mm inward, as rigid pairs with Y, spacing and rotations preserved. Pair pad-envelope centres are X=12.935000 and X=6.319999 mm. RF/DC endpoints, the two resistor DC vias, rectangular masks and shield fences follow the new positions. The two DC terminations were simplified to one 45-degree approach on their existing L4 layer; no pin remapping or transition via was needed.'
assert old in s;s=s.replace(old,new)
s=s.replace('252 signal tracks, 20 RF arcs and 524 vias',f"{len(n['tracks'])} signal tracks, {len(n['arcs'])} RF arcs and {len(n['vias'])} vias")
s=s.replace('Resistor_RF_Via_Removal','Lower_RC_70pct')
s=s.replace('Current reports are Lower_RC_70pct_validation.json,','Current reports are lower_RC_70pct_placement.json, placement_mask_validation.json, Lower_RC_70pct_validation.json,')
f.write_text(s,encoding='utf-8')
f=R/'script/README.md';s=f.read_text(encoding='utf-8').replace('Current removal of unused resistor RF vias is in `remove_resistor_rf_vias_20260921/`.','Current lower R/C pair movement to 70% of the previous centreline distance and QD RF-via removal are in `lower_rc_70pct_20260921/`. The preceding removal of unused resistor RF vias is in `remove_resistor_rf_vias_20260921/`.');f.write_text(s,encoding='utf-8')
(H/'README.md').write_text('''# Lower R/C placement at 70% of centreline distance

This revision edits the original PCB only. The schematic and QD footprint library remain unchanged; no pin remap is required.

- Translate R1/C1 by -1.36500108 mm X and R5/C5 by +1.46999960 mm X. The centre of each pair's pad envelope is at 70% of its previous distance from X=9.75 mm. Y, spacing and rotations remain unchanged.
- Remove six unused QD RF through vias at pads 1/6/9/12/18/24. Keep 18 QD DC vias, six resistor DC vias and 24 ZIF fanout vias. Capacitor and resistor RF pads remain via-free.
- Reconnect S1/MW1/S5/MW5 using XY/45-degree straight segments with tangent bends. MW1 uses 0.15 mm tangent radii for its small lateral adjustment; other changed bends use 0.30 mm radii. Simplify ZIF21/ZIF02 terminal approaches on their original L4 layer without extra vias.
- Regenerate 0.90 mm rectangular R/C masks and 480 solid L5-L6 shields: 243 RF-fence, 171 R/C-perimeter and 66 equal-angle SMP-ring vias. Preserve the hole-edge offset, no-interpad-via envelopes and cavity/ground/paste requirements.
- Move only the C1 reference label downward by 1.2 mm to resolve the resulting silk collision.

`prepare_move.py` and `prepare_shields.py` reuse the checked-in native geometry writers and guard the expected starting state. `ApplyMove.pas`, `ApplyShields.pas` and `FixLabel.pas` are one-time native mutations; do not rerun on a different revision. `before.PcbDoc` is a local ignored backup.

Validation reads the saved native PCB: exact requested moves and unaffected geometry, 37-net physical copper graph, one internal DC layer per net, XY/45-degree routing, tangent RF bends outside pads, RF paths through resistor pad centres, mask rectangles, 101 normal SMD paste apertures, QD ground exclusions, solid mounting connections, and 15 enabled Altium DRC rules after reopening. All reports must match the current PCB hash. Existing short track endings wholly inside QD pads 1/24 are recorded separately from exposed trace bends.

`publish_outputs.py` refreshes previews and fabrication companion files; this is not a complete production CAM release. `finalize_reports.py` updates current-report pointers after verification.
''',encoding='utf-8')
print('Finalized current reports for',v['pcb_sha256'])
