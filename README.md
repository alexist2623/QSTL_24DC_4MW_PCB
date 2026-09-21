# QSTL carrier PCB

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

There are 470 solid GND shield vias: 236 along RF routes, 168 around R/C groups, and 66 in SMP signal rings. They span L6-L5 only, with 0.10 mm holes and 0.25 mm lands. Straight fences use nominal 0.15 mm land-edge spacing (0.40 mm centre pitch). The RF clearance is measured from the RF copper edge to the laser-hole edge: 0.33 mm, corresponding to a 0.435 mm centre offset and 0.255 mm land clearance. Each active SMP uses an equal-angle 13-position grid at radius 0.88 mm; two symmetric RF-exit positions are omitted, leaving 11 vias with 0.421 mm chord spacing. R/C fences stay outside each complete two-pad/body envelope.

The remaining 60 through vias comprise 24 QD, 12 resistor and 24 ZIF fanout vias. DC uses one internal layer per net, 12 nets on each of L2/L4, with no extra transition vias. DC width is 0.125 mm; Top ZIF escapes are 0.15 mm. The central bus pitch is 0.6 mm and the two internal layers share XY routing space. Straight tracks remain XY/45-degree and RF bends use tangent arcs. Two adjacent DC trunks were offset locally by 0.10/0.05 mm to preserve clearance after the QD move.

## Solder mask and paste

Upper R3/C3 and R4/C4 moved upward by 2.0 mm, giving 2.05 mm minimum clearance to QD pads. Both lower pairs moved upward by 1.0 mm; R1/C1 additionally moved 0.35 mm toward the board centre. RF/DC endpoints and existing resistor vias moved with the components. No DC layer-transition vias were added.

The QD Bottom wire-bond field is unmasked. All six R/C groups now have rectangular solder-control areas extending 0.90 mm beyond their pad-group bounds, increased from 0.30 mm. The Bottom ZIF fanout-via array has a rectangular mask boundary with 0.40 mm land margin. RF outside the QD field retains its protected mask strip. SMP solder-control masks remain. All six mounting lands and their surrounding rings are unmasked on both faces and join GND polygons directly, without thermal relief. Shield vias retain explicit tenting overrides in protected areas.

No via-specific paste primitives are present. Paste is disabled on all 40 SMP and six mounting pads; the 101 SMD pad apertures are preserved. SMP mask remains; mounting mask removal is separately authorized by the later user instruction.

## Current validation and outputs

The saved original PCB contains 22 components, 147 pads, 37 named nets, 252 signal tracks, 20 RF arcs and 530 vias. Save/reopen verification reports **zero connection lines and zero violations across 15 enabled Altium DRC rules**. An independent graph of saved copper verifies all 37 nets, including the actual L5-L6 shield spans. Component pin assignments remain synchronized with the unchanged schematic for this revision.

[Saved-board validation](QSTL_24DC_4MW_PCB/docs/RC_Mask_Clearance_validation.json) | [Connectivity](QSTL_24DC_4MW_PCB/docs/connection_validation.json) | [Altium DRC](QSTL_24DC_4MW_PCB/docs/RC_Mask_Clearance_DRC.html)

[R/C mask detail](QSTL_24DC_4MW_PCB/docs/RC_mask_detail.png) | [ZIF mask detail](QSTL_24DC_4MW_PCB/docs/ZIF_mask_detail.png)

[RF and shields](QSTL_24DC_4MW_PCB/docs/RF_only.png) | [QD detail](QSTL_24DC_4MW_PCB/docs/QD_detail.png) | [Board overview](QSTL_24DC_4MW_PCB/docs/layout.png)

[Fabrication companion package](QSTL_24DC_4MW_PCB/fabrication/RF50_QD_cavity/README.md) contains the separate Bottom Blind Slots Gerber, a location/section drawing, L6-L5 laser-drill coordinates, stack data and JLCPCB ordering notes. It is not a complete production CAM release. No supplier upload or order has been made.

Current reports are RC_Mask_Clearance_validation.json, validation.json, connection_validation.json, RC_Mask_Clearance_DRC.html, native_paste_audit.txt, native_reopen_check.txt and RF50_render.json. Earlier RF/DC/model/mask reports are historical and retain their earlier revision hashes; do not use them as current signoff.
