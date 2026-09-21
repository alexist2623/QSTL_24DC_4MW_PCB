"""Document the verified dense shield-via revision."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
v=json.loads((H/'validation.json').read_text());p=json.loads((H/'preflight.json').read_text());assert v['passed']
readme=R/'README.md';s=readme.read_text(encoding='utf-8')
s=s.replace('There are 78 solid GND shield vias: 54 along RF routes and 24 in circular SMP signal fences.','There are 287 solid GND shield vias: 217 along RF routes and 70 in circular SMP signal fences.')
s=s.replace('Nominal pitch is 2 mm.','Nominal via-land-edge spacing is 0.15 mm, corresponding to 0.40 mm centre spacing for the retained 0.25 mm lands. Rounded sections and rings use chord spacing. Pad/hole and RF-exit clearances create larger gaps locally.')
s=s.replace('and 138 vias.','and 347 vias.').replace('RF50_HDI_validation.json','Shield_spacing_validation.json').replace('RF50_HDI_DRC.html','Shield_spacing_DRC.html')
readme.write_text(s,encoding='utf-8')
index=H.parent/'README.md';s=index.read_text(encoding='utf-8').replace('Current RF50, blind shield-via, QD pad/cavity and mask work is in `rf50_hdi_milling_20260920/`.','Current shield-spacing work is in `shield_spacing_20260921/`. The preceding RF50, QD pad/cavity and mask work is in `rf50_hdi_milling_20260920/`.');index.write_text(s,encoding='utf-8')
(H/'README.md').write_text(f'''# Dense L5-L6 shield vias

User clarification: 0.15 mm is the spacing between shield-via copper-land edges, not the distance from RF copper. Retain the 0.25 mm land and 0.10 mm hole; nominal centre spacing is 0.40 mm. RF-to-via edge spacing remains 0.33 mm.

Saved original PCB SHA-256: `{v['pcb_sha256']}`.

- 287 L5-L6 GND shields: 217 RF fence and 70 SMP ring vias.
- Saved minimum land-edge gap: {v['RF']['shield_to_shield_edge_gap_mm']:.9f} mm, within native coordinate precision of 0.15 mm.
- 283 of 287 vias have a nearest neighbour within 0.005 mm of the nominal gap. Component pads, holes, RF exits and fence endpoints create the larger local gaps.
- All 60 signal through-vias, component/pad placements, signal tracks/arcs, schematic, library, stack, cavity, mask and paste geometry are preserved.
- All 37 nets physically connected; zero stored connections; zero violations across 15 enabled Altium DRC checks after reopening.
- Shield vias remain solid GND, L5-L6 only, with no DC-layer penetration or via-specific paste.

`prepare.py` creates a plan and a guarded one-time native mutation from `before.PcbDoc`. Do not rerun mutation scripts against the completed board. `audit_connectivity.py` and `verify_final.py` inspect the saved copper; `verify_fabrication.py` checks the cavity and updated 287-hole laser-drill companion. Native logs are retained here. Published reports are under the original project's docs directory.

`publish_outputs.py` updates the saved-native previews and fabrication companion package. This package is not a complete production CAM release; no upload or order was made.
''',encoding='utf-8')
(P/'docs/shield_spacing.json').write_text(json.dumps(dict(**p,saved_pcb_sha256=v['pcb_sha256'],saved_minimum_land_edge_gap_mm=v['RF']['shield_to_shield_edge_gap_mm'],DRC_violations=v['DRC']['violations'],connectivity_passed=v['connectivity']),indent=2)+'\n')
print('Current documentation updated for',v['pcb_sha256'])
