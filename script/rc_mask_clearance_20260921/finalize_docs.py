"""Publish a coherent final revision summary after all saved-board audits pass."""
from pathlib import Path
import json,shutil,re
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';v=json.loads((H/'validation.json').read_text());x=json.loads((H/'refinements_validation.json').read_text());n=json.loads((H/'native_render_snapshot.json').read_text());plan=json.loads((H/'plan.json').read_text())
assert v['passed'] and x['passed'] and v['pcb_sha256']==x['pcb_sha256']==n['source_sha256']
s=(R/'README.md').read_text(encoding='utf-8')
s=re.sub(r'There are 287 solid GND shield vias:.*?Component transitions interrupt the fence where necessary for clearance\.', 'There are 470 solid GND shield vias: 236 along RF routes, 168 around R/C groups, and 66 in SMP signal rings. They span L6-L5 only, with 0.10 mm holes and 0.25 mm lands. Straight fences use nominal 0.15 mm land-edge spacing (0.40 mm centre pitch). The RF clearance is measured from the RF copper edge to the laser-hole edge: 0.33 mm, corresponding to a 0.435 mm centre offset and 0.255 mm land clearance. Each active SMP uses an equal-angle 13-position grid at radius 0.88 mm; two symmetric RF-exit positions are omitted, leaving 11 vias with 0.421 mm chord spacing. R/C fences stay outside each complete two-pad/body envelope.',s)
s=s.replace('The QD Bottom wire-bond field is unmasked. General board areas retain the requested explicit mask openings. Solder-control mask remains at R/C, ZIF, SMP and mounting lands, and over RF outside the QD field with a 0.25 mm protected margin. Narrow mask webs at R3/R4 were corrected without changing copper. Shield vias have explicit tenting overrides in protected mask areas.','The QD Bottom wire-bond field is unmasked. All six R/C groups now have rectangular solder-control areas extending 0.90 mm beyond their pad-group bounds, increased from 0.30 mm. The Bottom ZIF fanout-via array has a rectangular mask boundary with 0.40 mm land margin. RF outside the QD field retains its protected mask strip. SMP solder-control masks remain. All six mounting lands and their surrounding rings are unmasked on both faces and join GND polygons directly, without thermal relief. Shield vias retain explicit tenting overrides in protected areas.')
s=s.replace('Removing SMP/mechanical paste does not remove their solder mask.','SMP mask remains; mounting mask removal is separately authorized by the later user instruction.')
s=s.replace('250 signal tracks, 18 RF arcs and 347 vias',f"{len(n['tracks'])} signal tracks, {len(n['arcs'])} RF arcs and {len(n['vias'])} vias")
s=s.replace('Shield_spacing_validation.json','RC_Mask_Clearance_validation.json').replace('Shield_spacing_DRC.html','RC_Mask_Clearance_DRC.html')
paragraph='Upper R3/C3 and R4/C4 moved upward by 2.0 mm, giving 2.05 mm minimum clearance to QD pads. Both lower pairs moved upward by 1.0 mm; R1/C1 additionally moved 0.35 mm toward the board centre. RF/DC endpoints and existing resistor vias moved with the components. No DC layer-transition vias were added.\n\n'
s=s.replace('## Solder mask and paste\n\n','## Solder mask and paste\n\n'+paragraph)
s=s.replace('[RF and shields]', '[R/C mask detail](QSTL_24DC_4MW_PCB/docs/RC_mask_detail.png) | [ZIF mask detail](QSTL_24DC_4MW_PCB/docs/ZIF_mask_detail.png)\n\n[RF and shields]')
(R/'README.md').write_text(s,encoding='utf-8')
shutil.copy2(H/'refinements_validation.json',P/'docs/placement_mask_validation.json')
shutil.copy2(H/'preflight.json',P/'docs/shield_spacing.json')
script_readme=R/'script/README.md';s=script_readme.read_text(encoding='utf-8').replace('Current shield-spacing work is in `shield_spacing_20260921/`.','Current R/C placement, rectangular-mask and hole-edge shield work is in `rc_mask_clearance_20260921/`. The preceding component-fence/mount work is in `shield_rc_ring_20260921/`; earlier dense fences are in `shield_spacing_20260921/`.');script_readme.write_text(s,encoding='utf-8')
(H/'README.md').write_text(f'''# R/C placement, mask rectangles and corrected shield offsets

Final saved original PCB SHA-256: `{v['pcb_sha256']}`.

- R3/C3 and R4/C4: +2.0 mm Y; minimum QD pad gap 2.05 mm.
- R1/C1 and R5/C5: +1.0 mm Y. R1/C1 additionally -0.35 mm X. A proposed -0.70 mm X move failed offline clearance checks and was not applied.
- Retained R/C mask margin: 0.30 to 0.90 mm, exact group rectangles. Bottom ZIF array: rectangular mask, 0.40 mm land margin.
- Shield clearance: RF copper edge to laser-hole edge 0.33 mm. Land clearance 0.255 mm; centre offset 0.435 mm. 470 L5-L6 shields, 0.15 mm nominal land-edge spacing.
- SMP rings: 13 equal-angle positions with two symmetric RF-exit omissions, 11 vias per active SMP. No shield land crosses an R/C two-pad/body hull.
- All six mounts have bare surrounding rings on both faces and solid GND joins on L1/L3/L5/L6; SMP mask and normal SMD paste remain.
- Saved copper: 37 connected nets; zero connection lines; 15 native DRC checks, zero violations.

`before.PcbDoc` is the original pre-turn recovery copy. `prepare_move.py`, `ApplyMove.pas`, `ApplyShields.pas` and `FixLabels.pas` are one-time mutation records, not general rerunnable tools. The first native attempt stopped on an uninitialized interface comparison before route replacement; the corrected continuation used explicit Boolean presence flags and absolute destinations, then saved successfully. All final geometry was independently checked.

`verify_final.py`, `verify_refinements.py`, `audit_connectivity.py`, `ReopenAudit.pas` and `AuditPaste.pas` validate the saved source. `publish_outputs.py` and `finalize_docs.py` update previews and hash-bound fabrication companions. Earlier reports are historical. The original schematic and QD library were unchanged in this revision. No Git push or supplier submission was performed.
''',encoding='utf-8')
print('Documentation finalized for',v['pcb_sha256'])
