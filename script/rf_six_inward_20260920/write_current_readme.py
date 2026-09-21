"""Write the current revision overview inside this Git repository."""
from pathlib import Path
import json,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';D=P/'docs'
dc=json.loads((D/'DC_simplified.json').read_text());assert dc['passed'] and not dc['extra_DC_transition_vias']
readme='''# QSTL carrier PCB

Open [QSTL_24DC_4MW_PCB.PrjPcb](QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PrjPcb) in Altium Designer. The original project name is retained; the current circuit has **six active RF channels, 18 DC-only QD pads, and six RF DC-bias inputs**. All changes are in this Git repository's original PCB and schematic.

The working constraints are recorded in [DESIGN_REQUIREMENTS.md](QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md). Python and Altium helper scripts are under [script/](script/README.md). `AGENTS.md` requires reading and updating the constraints before further changes.

## Current routing

DC uses L2 or L4, with **one internal layer per net and zero additional layer-transition vias**. ZIF23 now connects to R3 pin 2 and ZIF25 to R2 pin 2; PCB and schematic are synchronized. The former standalone via at (13.35, 16.4) mm is removed. The parallel bus uses the same XY positions on both internal layers, from x=6.35 to 12.95 mm, at 0.6 mm pitch and approximately 0.475 mm copper-edge spacing.

The routes pass straight between the large GND mounting holes, with minimum copper gaps of 0.3625 mm on the left and 0.5625 mm on the right. The latest simplification removes 96 internal track segments, from 292 to 196. DC width is 0.125 mm; short Top ZIF escapes are 0.15 mm. The measured same-layer DC trace clearance minimum is approximately 0.175 mm. All DC turns change direction by no more than 45 degrees.

[GND-hole detail](QSTL_24DC_4MW_PCB/docs/DC_simplified.png) | [DC routes](QSTL_24DC_4MW_PCB/docs/DC_only.png) | [Separated routing layers](QSTL_24DC_4MW_PCB/docs/Routing_layers.png) | [DC audit](QSTL_24DC_4MW_PCB/docs/DC_simplified.json)

RF runs on Bottom, alongside QD and R/C. The QD-side stack is **RF / GND / DC / GND / DC / GND**, physically L6 / L5 / L4 / L3 / L2 / L1. ZIF and SMP are on Top. All six R/C pairs are moved inward, and the lower R1/C1 and R5/C5 pairs are rotated 90 degrees from their previous arrangement. Each RF path passes through the resistor RF-side pad centre without a separate resistor branch stub. R is 0603 / 10 kohm and C is 0402 / 1 nF. R1–R6 now use an embedded generic 0603 resistor STEP model; C1–C6 models align with their pad axes. The two passive footprint libraries are updated as well, with pad geometry preserved.

| Input | Series C / bias R | QD pad | Bias ZIF pin |
|---|---|---:|---:|
| SMP1 | C1 / R1 | 9 | 21 |
| SMP2 | C2 / R2 | 6 | 25 |
| SMP3 | C3 / R3 | 1 | 23 |
| SMP4 | C4 / R4 | 24 | 26 |
| SMP5 | C5 / R5 | 12 | 2 |
| SMP6 | C6 / R6 | 18 | 4 |

SMP7/8 centre pins remain NC. All eight SMP positions and six mounting holes are preserved. Only ZIF pins 1–12 and 15–26 are used; [PIN_MAPPING.csv](QSTL_24DC_4MW_PCB/docs/PIN_MAPPING.csv) includes the complete QD correspondence.

[RF routes](QSTL_24DC_4MW_PCB/docs/RF_only.png) | [RF pad-through audit](QSTL_24DC_4MW_PCB/docs/RF_stubless.json) | [3D model audit](QSTL_24DC_4MW_PCB/docs/model_validation.json) | [Model source](QSTL_24DC_4MW_PCB/Models/README.md)

## Preserved geometry and validation

The board is 19.5 × 67.9 mm with six copper layers. QD's inner pad-end opening is 4.3 × 4.3 mm; its pads are 1.0 × 0.5 mm at 0.7 mm pitch, with pads 1 and 24 on the upper edge. RF and DC avoid the QD opening. Straight copper is horizontal, vertical, or 45 degrees; RF corners use tangent 0.3 mm-radius arcs.

There are 72 through vias: 24 QD pad vias, 24 R/C pad vias, and 24 ZIF fanout vias. No shield/stitch vias are present. All retain Top/Bottom via tent flags and 144 explicit paste apertures. Via-in-pad holes share the component pad's Bottom mask opening. Three GND polygons occupy L1/L3/L5. The read-only reference PCB is unchanged.

The saved PCB has 22 components, 147 pads, 37 named nets, 250 straight tracks and 18 arcs. After closing and reopening it, Altium reports **zero connection lines and zero violations across 13 enabled DRC rules**. An independent layer-aware copper graph verifies all 37 nets as continuous; PCB pin assignments match the saved schematic. The native schematic compiler API returns `False` with zero violations, as in earlier revisions. Its complete 68-net export (37 named and 31 intentional NC) matches the saved documents; the raw Boolean is retained rather than described as a successful compile.

[Validation](QSTL_24DC_4MW_PCB/docs/validation.json) | [Copper connectivity](QSTL_24DC_4MW_PCB/docs/connection_validation.json) | [Current DRC](QSTL_24DC_4MW_PCB/docs/RF6_DRC.html) | [Angles](QSTL_24DC_4MW_PCB/docs/RF_position_and_angles.json) | [Schematic](QSTL_24DC_4MW_PCB/docs/schematic.png)

RF delay matching remains deferred by the user. [RF lengths](QSTL_24DC_4MW_PCB/docs/RF_delay.json) measure planar tracks and arcs; they do not establish 1 ps matching or 50-ohm impedance. Fabrication stack dimensions are unchanged.

[PCB overview](QSTL_24DC_4MW_PCB/docs/layout.png) | [QD detail](QSTL_24DC_4MW_PCB/docs/QD_detail.png)

Earlier symmetry, resizing, surface-stack DRC and comparison artifacts are historical. Current reports listed above contain the current board's SHA-256; check that hash before reusing results after edits.
'''
(R/'README.md').write_text(readme,encoding='utf-8')
shutil.copy2(D/'RF_only.png',D/'placement_detail.png')
print('Current README and placement view updated.')
