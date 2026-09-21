# User design requirements

Updated 2026-09-21. Later user instructions supersede earlier ones. Read this file before every design-file modification.

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
- The central QD cavity remains 4.3 x 4.3 mm. The latest user correction requires moving the QD pads outward by 0.2 mm, making the square defined by inward-facing pad ends 4.7 x 4.7 mm. Preserve the 1.0 x 0.5 mm pad sizes and 0.7 mm pitch along each row; cavity-to-pad clearance is 0.2 mm.
- Move at most one pad from each side to the upper edge, only if necessary to resolve a corner collision. Current upper pads are 1 and 24.
- Use 0603 resistors and 0402 capacitors. Component rotations must be multiples of 45 degrees.
- Place all six R/C pairs inward as shown by the user. The lower R1/C1 and R5/C5 groups are rotated 90 degrees from the previous arrangement.
- Align capacitor 3D models with their pad axes and use a proper 0603 resistor package model.

## RF and DC connectivity

- RF QD pads are 1, 6, 9, 12, 18 and 24. Preserve the physical positions of the initial four RF channels; QD12 and QD18 are additional RF connections.
- Current mapping: SMP1 to QD9, SMP2 to QD6, SMP3 to QD1, SMP4 to QD24, SMP5 to QD12, SMP6 to QD18. SMP7/8 centre pins are NC.
- Each RF channel has a series capacitor and DC bias resistor. The RF path must pass through the resistor RF-side pad centre without a separate resistor branch stub.
- Use via-in-pad for the 18 QD DC pads and the DC-feeding bias-resistor pads. QD RF pads 1/6/9/12/18/24 connect entirely on Bottom and must have no vias; this supersedes the earlier all-QD-pad via requirement. R1-R6 must have exactly one via each, at DC pad 2. RF pad 1 connects entirely on Bottom and must have no via; do not add a through via to a same-layer RF junction. This explicitly supersedes the former two-vias-per-resistor implementation. RF series capacitors remain entirely on Bottom: remove their redundant through vias to avoid RF stubs. Retain their normal SMD pads and paste. Place R/C close together, with C naturally aligned to the RF path.
- Connect 18 DC-only QD pads and six RF bias resistors to ZIF pins 1-12 and 15-26 only. Preserve the verified carrier-to-footprint physical contact numbering.
- Resolve crossings by changing ZIF assignments in the schematic and PCB together. Each DC net must complete its route on one internal signal layer. Do not add standalone DC layer-transition vias.
- Current bias assignments: ZIF21 to R1.2, ZIF25 to R2.2, ZIF23 to R3.2, ZIF26 to R4.2, ZIF02 to R5.2, ZIF04 to R6.2.

## Routing and layer stack

- From the QD side: RF / GND / DC / GND / DC / GND. Physical layers: L6 RF, L5 GND, L4 DC, L3 GND, L2 DC, L1 GND.
- RF is on Bottom with QD and R/C. RF and DC must not cross the QD interior.
- Straight tracks may only be horizontal, vertical or 45 degrees. RF corners must be tangent curves. Each DC corner must turn at most 45 degrees; do not use a single sharp 90-degree corner.
- Use XY overlap between the two independent DC layers. Preserve clearance to other nets on the same layer and to through-hole pads/vias on every layer.
- Gather DC routes near the board centre. Do not pull them toward large GND holes. Preserve clearance and minimize bends.
- Current DC width is 0.125 mm and Top ZIF escapes are 0.15 mm. RF width changes to 0.11 mm with a 0.2 mm coplanar GND gap, following the supplied JLCPCB 50-ohm HDI calculation. Default non-RF clearance stays 0.15 mm. Central DC bus pitch is 0.6 mm.
- Preserve short RF centreline routes and tangent arcs. The user deferred 1 ps delay matching. Specify 50 ohms as the controlled-impedance target; calculator geometry is not a measured guarantee for connector, component or wire-bond transitions.
- Use the supplied 6-layer 1078 HDI stack: copper 0.035/0.0152/0.0152/0.0152/0.0152/0.035 mm, and dielectric gaps 0.0784/0.55/0.2008/0.55/0.0784 mm. Match L6/L5 to the symmetric L1/L2 calculator geometry. Use the current calculator's actual stack code in fabrication notes.

## Solder mask, paste mask and QD ground exclusion

- The request to remove the green coating means solder-mask removal. Use explicit Top/Bottom Solder openings on general board areas, retaining mask at soldering sites and RF routes.
- QD is a wire-bonding area. Remove Bottom solder mask across its pad field and central cavity. Retain solder-control mask around SMD R/C, ZIF contacts/fanout, SMP signal/ground pins, and retain mask on RF away from the QD bond-pad field. The Top reverse side retains its previous via tenting.
- Preserve mask over RF tracks and tangent curves, including a margin from the RF copper edge. Initial implementation uses a 0.25 mm protected margin. Do not change RF copper to achieve a visual mask change.
- Latest explicit follow-ups: remove every via-specific Top/Bottom Paste aperture and all paste apertures on mechanical mounting pads and SMP pads. Normal SMD component-pad paste openings must remain. This overrides the earlier request for paste apertures on every via.
- The user clarified that removing paste on mechanical parts and SMP does not mean removing their solder mask. Retain SMP solder-control masks; the later explicit mounting-hole request now removes mounting masks.
- Retain via tenting in protected soldering areas. Solder-mask coating and paste-mask stencil apertures are separate features and must be audited separately.
- Remove GND within the QD inner-end square on every copper layer except Top. The updated inner pad-end boundary is x=7.4-12.1 mm and y=40.15-44.85 mm, centred at (9.75,42.5) mm.
- Keep Top GND within that square and retain layer-specific polygon-pour cutouts on L2/L3/L4/L5/L6. The latest user request authorizes a non-through milled pocket from the QD/Bottom face, with a 4.3 x 4.3 mm outer envelope and 1.2 mm depth. This supersedes the earlier instruction not to mill the substrate. Do not create a through-board cutout. Move the QD pads outward as specified above and reconnect their existing via-in-pad fanouts.
- The pocket envelope is x=7.6-11.9 mm, y=40.35-44.65 mm, inset 0.2 mm from each 4.7 mm pad-end boundary. The latest user correction preserves the 4.3 mm QD cavity and moves the pads, superseding the earlier proposal to shrink the cavity to 3.9 mm. Use rounded internal CNC corners and state the cutter radius in the drawing.
- JLCPCB requires a separate Bottom Blind Slots Gerber, side/depth/metallization order fields, a location/section drawing and an order remark naming the layer. Specify a non-plated cavity. Verify the remaining substrate and nearest copper clearance; no production order is authorized.
- Recheck these mask and GND conditions after every subsequent layout or polygon modification.

## Vias and validation

- Extend shield fences around R1-R6 and C1-C6. Treat each two-pad convex hull (including the inter-pad bridge/body area) as a forbidden region for shield-via lands; surround the outside instead of cutting between the pads.
- Active SMP rings must use equal angular increments and symmetric RF exits. Choose an equal-angle grid from the hole-edge clearance radius and nominal 0.40 mm chord pitch. Keep the RF exit gap symmetric; do not retain an obsolete fixed via count when the radius changes.
- Latest mechanical-hole instruction supersedes the earlier protected mounting mask: expose all six mounting lands and their surrounding ring on both solder-mask layers. Connect these GND mounting pads directly to every GND polygon with no thermal spokes/voids. SMP solder-control masks and normal SMD paste remain unchanged; mounting paste remains disabled.

- Add GND shield vias along both sides of RF routes, with nominal 0.15 mm copper-land-edge spacing, equivalent to 0.40 mm centre spacing for the retained 0.25 mm lands. Use chord spacing at curves/rings; larger local gaps are allowed only to preserve pad/hole and RF-exit clearance. This supersedes the previous 2 mm pitch. The latest correction measures three RF widths from the RF copper edge to the laser-drill hole edge, not to the via land. For 0.11 mm RF and 0.10 mm holes, the centre offset is 0.435 mm; the 0.25 mm land edge is 0.255 mm from RF copper.
- Shield vias connect L6/Bottom RF coplanar GND to adjacent L5 GND only. Use laser blind microvias, nominal 0.1 mm drill and 0.25 mm land, with solid connections and no thermal spokes or paste apertures. They must not reach L4/L2 DC layers. Continue the fence inside each active SMP footprint as a ring around its signal centre, leaving the RF escape corridor clear.
- Preserve via-in-pad; component pad mask openings remain distinct from via-specific tent flags. Via-specific paste apertures must be absent.
- Avoid unintended component, pad and routing overlaps. Intentional same-net joints and via-in-pad are allowed.
- Keep PCB, schematic and library pin definitions consistent. Save/reopen and check DRC and retained connection counts. Independently verify actual copper connectivity on all layers.
- Verify solder-mask openings against protected RF/soldering geometry, normal SMD paste preservation, absence of via-specific paste, and GND exclusion on all non-Top layers with Top GND retained.

## Latest placement and rectangular mask refinement

- Latest lower-pair refinement: move R1/C1 and R5/C5 toward X=9.75 mm so that each pair centre is at 70% of its previous distance from this board centreline. Define each pair centre by the union of its pad envelopes. Move each pair rigidly in X, preserving Y, spacing and rotations; reconnect RF and DC and rebuild masks and shielding. This is an additional move from the saved revision immediately before this request.
- Move upper R3/C3 and R4/C4 upward by 2.0 mm, away from the QD bond pads. Move both lower R1/C1 and R5/C5 upward by 1.0 mm, as confirmed by the user. Additionally move R1/C1 inward by 0.35 mm. Preserve pair spacing and rotations; reconnect RF/DC without adding transition vias.
- Increase the retained solder-control margin around each R/C group from 0.30 to 0.90 mm. Use exact axis-aligned group rectangles, not rounded convex-hull patches. Preserve normal SMD pad openings and paste, RF coverage and the unmasked QD field.
- Cover the complete Bottom ZIF fanout-via array with a rectangular solder-mask area, extending 0.40 mm beyond its via lands.
