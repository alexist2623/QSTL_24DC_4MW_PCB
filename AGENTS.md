# PCB working rules

Read and follow `QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md` before modifying any design file. Immediately update it when the user changes a requirement. Later user instructions take precedence.

Write Markdown documents, source comments and technical annotations in English. Communicate with the user in Korean.

Create and run all Python and Altium helper scripts inside this repository's `script/` directory. Do not create new helper code in external work folders. Never modify the read-only reference PCBs.

Edit the original PCB and schematic belonging to `QSTL_24DC_4MW_PCB.PrjPcb`. Do not create a separate V2 project or leave the final PCB as a Free Document. Keep PCB and schematic pin assignments synchronized.

Resolve DC crossings by reassigning ZIF pins in the schematic. Each DC net must use only one internal routing layer. Do not add standalone DC layer-transition vias.

The green coating is solder mask, not paste mask. Remove solder mask from general board areas while preserving solder-control masks around soldering sites and a protected strip along RF copper with clearance. Preserve normal component-pad openings. Remove paste from vias, mechanical mounting pads and SMP pads; retain normal SMD pad paste. The user explicitly clarified that SMP/mechanical paste removal must not remove their solder-control mask.

Keep the central QD cavity 4.3 x 4.3 mm, centred at (9.75,42.5) mm. Move the QD pads outward by 0.2 mm, preserving pad dimensions, to make a 4.7 x 4.7 mm inner pad-end square and 0.2 mm cavity-to-pad clearance. Keep the 4.7 mm inner square free of GND copper on every layer except Top. Preserve Top GND inside this boundary. The non-through pocket is 1.2 mm deep from the QD/Bottom face. Document it on a separate Bottom Blind Slots fabrication layer; never turn it into a through-board cutout.

QD is a wire-bonding area: remove Bottom solder mask over the pad field and cavity. RF outside the pad field retains solder mask. Target 50 ohms using the user's JLCPCB HDI calculator geometry: 0.11 mm RF width, 0.2 mm coplanar GND gap, and the matching 1078 outer dielectric stack. Add solid GND shield microvias only between L6 RF and L5 GND, with nominal 0.15 mm land-edge spacing (0.40 mm centre pitch for 0.25 mm lands) and approximately 3 trace widths from RF copper edge to laser-hole edge. Include circular fences around active SMP signal centres. No shield via may penetrate a DC layer.

Before reporting completion, verify saved copper connectivity, stored connection count, schematic correspondence, mask geometry, absence of via-specific paste, the QD GND exclusions, and Altium DRC after save/reopen. Do not suppress genuine DRC failures.

Surround R/C footprints with shield vias without crossing the two-pad/inter-pad body envelopes. SMP rings use an equal-angle grid with symmetric RF escape gaps. Remove solder mask around all six mounting holes on both faces and use direct GND connections without thermal relief; this supersedes the earlier mounting-mask preservation instruction. Preserve SMP masks and keep mounting paste disabled.

The RF shield offset is measured to the laser hole edge: 0.435 mm centre offset for 0.11 mm RF and 0.10 mm holes. R/C solder-control masks use 0.90 mm rectangular group margins; the Bottom ZIF via array has a rectangular mask boundary. Preserve these conditions during subsequent edits.
