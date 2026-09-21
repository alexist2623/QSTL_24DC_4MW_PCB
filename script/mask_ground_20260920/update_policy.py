"""Record the user's current design requirements in English."""
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
(R/'AGENTS.md').write_text('''# PCB working rules

Read and follow `QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md` before modifying any design file. Immediately update it when the user changes a requirement. Later user instructions take precedence.

Write Markdown documents, source comments and technical annotations in English. Communicate with the user in Korean.

Create and run all Python and Altium helper scripts inside this repository's `script/` directory. Do not create new helper code in external work folders. Never modify the read-only reference PCBs.

Edit the original PCB and schematic belonging to `QSTL_24DC_4MW_PCB.PrjPcb`. Do not create a separate V2 project or leave the final PCB as a Free Document. Keep PCB and schematic pin assignments synchronized.

Resolve DC crossings by reassigning ZIF pins in the schematic. Each DC net must use only one internal routing layer. Do not add standalone DC layer-transition vias.

The green coating is solder mask, not paste mask. Remove solder mask from general board areas while preserving solder-control masks around soldering sites and a protected strip along RF copper with clearance. Preserve normal component-pad openings. Remove paste from vias, mechanical mounting pads and SMP pads; retain normal SMD pad paste. The user explicitly clarified that SMP/mechanical paste removal must not remove their solder-control mask.

Keep the 4.3 x 4.3 mm square defined by QD inner pad ends free of GND copper on every layer except Top. Preserve Top GND inside this boundary. Use copper-pour exclusions, never a physical board cutout.

Before reporting completion, verify saved copper connectivity, stored connection count, schematic correspondence, mask geometry, absence of via-specific paste, the QD GND exclusions, and Altium DRC after save/reopen. Do not suppress genuine DRC failures.
''',encoding='utf-8')
(P/'docs/DESIGN_REQUIREMENTS.md').write_text('''# User design requirements

Updated 2026-09-20. Later user instructions supersede earlier ones. Read this file before every design-file modification.

## Language and workspace

- Write Markdown documents, code comments and technical annotations in English. Use Korean in conversation with the user.
- Edit the original project, PCB and schematic. Do not create a separate V2 project or a final Free Document.
- Keep Python and Altium helper scripts in the repository-root `script/` directory.
- The initial reference PCB and the carrier PCB used to inspect ZIF wiring are read-only.
- Push to Git only when the user requests it.

## Mechanical geometry and placement

- Preserve the reference 19.5 x 67.9 mm outline, all eight SMP positions and six mechanical mounting holes.
- ZIF and SMP are on Top. QD and all R/C components are on Bottom.
- Preserve the requested QD orientation and pad numbering 1-24.
- The square defined by inward-facing pad ends is 4.3 x 4.3 mm. QD pads are 1.0 x 0.5 mm at 0.7 mm pitch.
- Move at most one pad from each side to the upper edge, only if necessary to resolve a corner collision. Current upper pads are 1 and 24.
- Use 0603 resistors and 0402 capacitors. Component rotations must be multiples of 45 degrees.
- Place all six R/C pairs inward as shown by the user. The lower R1/C1 and R5/C5 groups are rotated 90 degrees from the previous arrangement.
- Align capacitor 3D models with their pad axes and use a proper 0603 resistor package model.

## RF and DC connectivity

- RF QD pads are 1, 6, 9, 12, 18 and 24. Preserve the physical positions of the initial four RF channels; QD12 and QD18 are additional RF connections.
- Current mapping: SMP1 to QD9, SMP2 to QD6, SMP3 to QD1, SMP4 to QD24, SMP5 to QD12, SMP6 to QD18. SMP7/8 centre pins are NC.
- Each RF channel has a series capacitor and DC bias resistor. The RF path must pass through the resistor RF-side pad centre without a separate resistor branch stub.
- Use via-in-pad for QD and RF tee R/C pads. Place R/C close together, with C naturally aligned to the RF path.
- Connect 18 DC-only QD pads and six RF bias resistors to ZIF pins 1-12 and 15-26 only. Preserve the verified carrier-to-footprint physical contact numbering.
- Resolve crossings by changing ZIF assignments in the schematic and PCB together. Each DC net must complete its route on one internal signal layer. Do not add standalone DC layer-transition vias.
- Current bias assignments: ZIF21 to R1.2, ZIF25 to R2.2, ZIF23 to R3.2, ZIF26 to R4.2, ZIF02 to R5.2, ZIF04 to R6.2.

## Routing and layer stack

- From the QD side: RF / GND / DC / GND / DC / GND. Physical layers: L6 RF, L5 GND, L4 DC, L3 GND, L2 DC, L1 GND.
- RF is on Bottom with QD and R/C. RF and DC must not cross the QD interior.
- Straight tracks may only be horizontal, vertical or 45 degrees. RF corners must be tangent curves. Each DC corner must turn at most 45 degrees; do not use a single sharp 90-degree corner.
- Use XY overlap between the two independent DC layers. Preserve clearance to other nets on the same layer and to through-hole pads/vias on every layer.
- Gather DC routes near the board centre. Do not pull them toward large GND holes. Preserve clearance and minimize bends.
- Current DC width is 0.125 mm, Top ZIF escapes 0.15 mm, RF approximately 0.214 mm. Minimum copper clearance is 0.15 mm. Central bus pitch is 0.6 mm with approximately 0.475 mm copper-edge spacing.
- Prioritize short, simple RF routes. The user deferred 1 ps delay matching. Do not claim verified 50-ohm impedance or a 1 ps match.

## Solder mask, paste mask and QD ground exclusion

- The request to remove the green coating means solder-mask removal. Use explicit Top/Bottom Solder openings on general board areas, retaining mask at soldering sites and RF routes.
- Retain solder-control mask around SMD R/C, QD bond pads, ZIF contacts/fanout, SMP signal/ground pins and mounting lands. Preserve existing pad openings: lands must remain solderable while adjacent copper remains protected against solder spread.
- Preserve mask over RF tracks and tangent curves, including a margin from the RF copper edge. Initial implementation uses a 0.25 mm protected margin. Do not change RF copper to achieve a visual mask change.
- Latest explicit follow-ups: remove every via-specific Top/Bottom Paste aperture and all paste apertures on mechanical mounting pads and SMP pads. Normal SMD component-pad paste openings must remain. This overrides the earlier request for paste apertures on every via.
- The user clarified that removing paste on mechanical parts and SMP does not mean removing their solder mask. Retain solder-control masks at these sites.
- Retain via tenting in protected soldering areas. Solder-mask coating and paste-mask stencil apertures are separate features and must be audited separately.
- Remove GND within the QD inner-end square on every copper layer except Top. The boundary is x=7.6-11.9 mm and y=40.35-44.65 mm, centred at (9.75,42.5) mm.
- Keep Top GND within that square. Add persistent layer-specific polygon-pour cutouts on L2/L3/L4/L5/L6. Do not create a board cutout, change the substrate, move pads or disturb signal routes.
- Recheck these mask and GND conditions after every subsequent layout or polygon modification.

## Vias and validation

- Do not add shield/stitch vias. If GND vias are requested later, use solid connections without thermal spokes.
- Preserve via-in-pad; component pad mask openings remain distinct from via-specific tent flags. Via-specific paste apertures must be absent.
- Avoid unintended component, pad and routing overlaps. Intentional same-net joints and via-in-pad are allowed.
- Keep PCB, schematic and library pin definitions consistent. Save/reopen and check DRC and retained connection counts. Independently verify actual copper connectivity on all layers.
- Verify solder-mask openings against protected RF/soldering geometry, normal SMD paste preservation, absence of via-specific paste, and GND exclusion on all non-Top layers with Top GND retained.
''',encoding='utf-8')
(R/'script/README.md').write_text('''# PCB working scripts

Create and run helper code inside this repository's `script/` directory. Write Markdown, code comments and technical annotations in English. Communicate with the user in Korean.

Read [DESIGN_REQUIREMENTS.md](../QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md) and [AGENTS.md](../AGENTS.md) before editing the original `QSTL_24DC_4MW_PCB/` project.

Current mask, via-paste and QD ground-exclusion work is in `mask_ground_20260920/`. Previous RF/DC routing work is in `rf_six_inward_20260920/`. `_support/` contains local parsing, rendering and schematic helpers; older revision names there do not denote a separate final project.

Use `script/.venv/Scripts/python.exe -X utf8` with `requirements.txt`. Native Altium scripts must target the original project and be followed by save/reopen checks. Python validators read saved documents. Current reports must match the saved PCB SHA-256.

Previous mutation scripts such as `ApplyRF6.pas`, `FixRF6.pas`, `AdjustRF6.pas`, `FinalDC.pas` and `FixModels.pas` are one-time change records. They assume a specific starting state and must not be rerun blindly. The preceding via-paste validator is historical: the latest user instruction explicitly removes via-specific paste apertures while retaining normal SMD paste.

Keep reference designs read-only, avoid extra DC transition vias, and preserve the current RF/soldering masks and non-Top QD GND exclusions during later edits.
''',encoding='utf-8')
print('English working rules and design requirements updated.')
