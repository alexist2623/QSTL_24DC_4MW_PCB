"""Record the completed revision and retire obsolete current-status descriptions."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
v=json.loads((H/'validation.json').read_text());assert v['passed']
root='''# QSTL carrier PCB

Open [QSTL_24DC_4MW_PCB.PrjPcb](QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PrjPcb) in Altium Designer. The original project contains six active RF channels, 18 DC-only QD pads and six RF bias inputs. ZIF and SMP are on Top; QD, R0603 and C0402 are on Bottom. All eight SMP positions, six mounting holes and the 19.5 x 67.9 mm board outline are preserved.

Read [DESIGN_REQUIREMENTS.md](QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md) before further edits. Helpers are in [script/](script/README.md); the reference PCBs remain read-only.

## QD cavity and pad geometry

The Bottom-entry non-plated pocket is 4.3 x 4.3 mm, centred at (9.75,42.50) mm, with R0.5 internal corners and 1.2 mm depth. It is a fabrication-defined blind pocket, not a through-board cutout or a rendered 3D cavity. Its outline is on Mechanical 2 and its English depth note is on Mechanical 3.

QD pad rows have moved outward by 0.2 mm. The inner pad-end opening is 4.7 x 4.7 mm and the nominal cavity-to-pad gap is 0.2 mm. Pad sizes remain 1.0 x 0.5 mm with 0.7 mm pitch along each row. Pads 1 and 24 remain on the upper edge. The original QD footprint library matches the saved board.

The 4.7 mm inner square is free of GND on L2/L3/L4/L5/L6; Top GND remains under the pocket. RF and DC do not cross the cavity.

## RF and routing stack

From the QD side the stack is **RF / GND / DC / GND / DC / GND**, physically L6/L5/L4/L3/L2/L1. RF uses 0.11 mm width with a 0.2 mm coplanar GND gap, following the supplied 50-ohm JLCPCB HDI calculator geometry. The native stack matches the specified copper/dielectric thicknesses for JLCH06161HN1-1078. Fabricator material Dk, finished copper, mask and width compensation still require confirmation; this is not an impedance simulation or measurement. Delay matching to 1 ps remains deferred.

| Input | Series C / bias R | QD pad | Bias ZIF pin |
|---|---|---:|---:|
| SMP1 | C1 / R1 | 9 | 21 |
| SMP2 | C2 / R2 | 6 | 25 |
| SMP3 | C3 / R3 | 1 | 23 |
| SMP4 | C4 / R4 | 24 | 26 |
| SMP5 | C5 / R5 | 12 | 2 |
| SMP6 | C6 / R6 | 18 | 4 |

SMP7/8 centre pins remain NC. Only ZIF contacts 1-12 and 15-26 are used. [PIN_MAPPING.csv](QSTL_24DC_4MW_PCB/docs/PIN_MAPPING.csv) contains the complete correspondence. Each RF path passes through its resistor RF-side pad centre without a separate resistor branch stub. All 12 redundant capacitor pad through-vias are removed.

There are 78 solid GND shield vias: 54 along RF routes and 24 in circular SMP signal fences. Their span is L6-L5 only, with 0.10 mm hole and 0.25 mm land; they do not enter DC layers. Nominal pitch is 2 mm. The minimum RF trace-edge to via-land-edge gap is 0.33 mm. Component transitions interrupt the fence where necessary for clearance.

The remaining 60 through vias comprise 24 QD, 12 resistor and 24 ZIF fanout vias. DC uses one internal layer per net, 12 nets on each of L2/L4, with no extra transition vias. DC width is 0.125 mm; Top ZIF escapes are 0.15 mm. The central bus pitch is 0.6 mm and the two internal layers share XY routing space. Straight tracks remain XY/45-degree and RF bends use tangent arcs. Two adjacent DC trunks were offset locally by 0.10/0.05 mm to preserve clearance after the QD move.

## Solder mask and paste

The QD Bottom wire-bond field is unmasked. General board areas retain the requested explicit mask openings. Solder-control mask remains at R/C, ZIF, SMP and mounting lands, and over RF outside the QD field with a 0.25 mm protected margin. Narrow mask webs at R3/R4 were corrected without changing copper. Shield vias have explicit tenting overrides in protected mask areas.

No via-specific paste primitives are present. Paste is disabled on all 40 SMP and six mounting pads; the 101 SMD pad apertures are preserved. Removing SMP/mechanical paste does not remove their solder mask.

## Current validation and outputs

The saved original PCB contains 22 components, 147 pads, 37 named nets, 250 signal tracks, 18 RF arcs and 138 vias. Save/reopen verification reports **zero connection lines and zero violations across 15 enabled Altium DRC rules**. An independent graph of saved copper verifies all 37 nets, including the actual L5-L6 shield spans. Component pin assignments remain synchronized with the unchanged schematic for this revision.

[Saved-board validation](QSTL_24DC_4MW_PCB/docs/RF50_HDI_validation.json) | [Connectivity](QSTL_24DC_4MW_PCB/docs/connection_validation.json) | [Altium DRC](QSTL_24DC_4MW_PCB/docs/RF50_HDI_DRC.html)

[RF and shields](QSTL_24DC_4MW_PCB/docs/RF_only.png) | [QD detail](QSTL_24DC_4MW_PCB/docs/QD_detail.png) | [Board overview](QSTL_24DC_4MW_PCB/docs/layout.png)

[Fabrication companion package](QSTL_24DC_4MW_PCB/fabrication/RF50_QD_cavity/README.md) contains the separate Bottom Blind Slots Gerber, a location/section drawing, L6-L5 laser-drill coordinates, stack data and JLCPCB ordering notes. It is not a complete production CAM release. No supplier upload or order has been made.

Current reports are RF50_HDI_validation.json, validation.json, connection_validation.json, RF50_HDI_DRC.html, native_paste_audit.txt, native_reopen_check.txt and RF50_render.json. Earlier RF/DC/model/mask reports are historical and retain their earlier revision hashes; do not use them as current signoff.
'''
(R/'README.md').write_text(root,encoding='utf-8')
(H/'README.md').write_text(f'''# RF50, QD cavity and shield-via revision

Completed and verified against the saved original PCB. SHA-256: `{v['pcb_sha256']}`.

- Cavity: 4.3 x 4.3 mm, Bottom entry, 1.2 mm depth, R0.5, non-plated.
- QD pad-end opening: 4.7 mm after a 0.2 mm outward shift; original pad dimensions/pitch preserved. Original QD library installed and verified.
- RF: 0.11 mm width, 0.2 mm CPW gap, matching 1078 stack thicknesses. 50 ohms is a fabrication target, not a measured result.
- Capacitor pad through-vias removed: 12. Retained through-vias: 60.
- GND shields: 78 L5-L6 blind vias (54 RF fence + 24 SMP ring), 0.1 mm hole / 0.25 mm land. No DC-layer penetration, thermal relief or paste.
- QD Bottom mask opening and non-Top GND exclusion updated. Shield mask overrides and R3/R4 mask margins pass native checks.
- Saved-board connectivity: all 37 nets connected, zero stored connections. Reopened Altium DRC: 15 enabled checks, zero violations.

## Read-only verification

`audit_connectivity.py` builds a layer-aware graph from saved native copper. `verify_final.py` checks saved pads, routes, stack, via spans, ground exclusions, mask, paste, library correspondence and native DRC. `ReopenAudit.pas` closes/reopens the original board and runs native DRC; `AuditPaste.pas` reads native paste flags. Re-run these only after relevant edits, not merely to repeat a passing test.

`publish_outputs.py` renders saved copper and publishes the fabrication companion directory under the original project. `fabrication_notes.py` creates the cavity Gerber/drawing and notes. `update_documentation.py` records this revision. Published reports and the fabrication manifest carry source hashes.

## Mutation history

`ApplyRF50.pas`, `FinishRF50.pas`, `CompleteRF50.pas` and library-install helpers are one-time change records. Do not rerun them against the completed board. The original interrupted script used unsupported FabText.X/Y properties; the completed continuation uses MoveToXY. The final mask repair is recorded in `RepairMask.pas`. `before.PcbDoc` and `before.PcbLib` preserve the starting state.

See the repository README and project DESIGN_REQUIREMENTS.md for current constraints. The fabrication companion package is not a complete production CAM release. Fabricator acceptance of the combined cavity/HDI process and actual controlled impedance is still required before production.
''',encoding='utf-8')
s=H.parent/'README.md';text=s.read_text(encoding='utf-8');text=text.replace('Current mask, via-paste and QD ground-exclusion work is in `mask_ground_20260920/`. Previous RF/DC routing work is in `rf_six_inward_20260920/`.','Current RF50, blind shield-via, QD pad/cavity and mask work is in `rf50_hdi_milling_20260920/`. Previous mask work is in `mask_ground_20260920/`; previous RF/DC routing work is in `rf_six_inward_20260920/`.');s.write_text(text,encoding='utf-8')
d=P/'docs/DESIGN_REQUIREMENTS.md';text=d.read_text(encoding='utf-8').replace('Updated 2026-09-20.','Updated 2026-09-21.');d.write_text(text,encoding='utf-8')
print('Updated current revision documentation')
