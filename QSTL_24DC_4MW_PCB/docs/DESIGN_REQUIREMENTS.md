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

- Centre the device on the plate's longitudinal bisecting plane X=25.5 mm. After its end-for-end reversal, move the device and mating boss together by +2.088496738338 mm in X. The boss's local X minimum becomes 19.794248369169 mm; its width remains 13.5 mm. The device centre is defined by the midpoint of the complete carrier's X bounds. Preserve all hole pitches and the inward-facing mounting arrangement.

- Latest correction supersedes the previous whole-group rotation: attach the plate to the opposite rod face while keeping its boss directed inward between the two rods. The plate occupies Z=-4 to 0 mm; rods remain Z=0 to 6 mm and the boss occupies Z=0 to 6 mm. Keep the screenshot-confirmed device orientation with ZIF uppermost (180-degree in-plane turn). Move this device/boss group inward without turning the boss outward. Rod screws enter from Z=-4 mm toward +Z. Keep only this corrected arrangement as the final assembly.

- Shorten the mounting plate to approximately the complete device length. The unchanged carrier spans 79.43999922 mm along the rods; use an 80 mm plate from assembly Y=135 to 215 mm. Retain its 51 mm width, 4 mm thickness and 13.5 x 6 mm boss cross section. The boss length becomes 72 mm. Keep the existing carrier and occupied screw positions; retain five M3 x 0.5 - 6H holes per boss side at 16 mm pitch (Y=144.82802366515844 through 208.82802366515844 mm) and four rod fasteners per rod at Y=140,160,180,200 mm. This supersedes the longer plate, eight-hole boss rows and 16 rod fasteners. Reversal reviews use the shortened plate.

- Final orientation is the screenshot explicitly confirmed by the user: ZIF is at the upper end and the carrier is rotated 180 degrees in the plate plane, then the complete plate/carrier/fastener group is mounted on the opposite rod face. The confirmed open document was `Orientation_Review/Both_reversed.iam`. Promote this exact placement to the main assembly and retain only this final result. The device uses the opposite threaded boss face at reference Y=160.82802366515844 and 176.82802366515844 mm. The full group reversal is 180 degrees about the rod-axis line X=25.5, Z=3 mm. Preserve rod and sleeve positions, the 80 mm plate and all source part geometry. Archive intermediate alternatives in the script temporary folder.

- Add matching threaded rows to both opposite side faces of the raised device-mounting boss. Each side has eight right-hand M3 x 0.5 - 6H threads at the same 16 mm pitch and aligned Y/Z centres, for 16 threads total. Retain 6 mm modeled bore/thread depth per side and the 13.5 mm boss width, leaving a 1.5 mm solid web between opposed bores. Preserve the existing two device screws, all assembly placements and the sleeve.

- Add a separate open-ended cylindrical sleeve around the H frame: inner diameter 51 mm, outer diameter 54 mm, with its axis through the midpoint of the two rod centre lines. Current frame rod centres are (X,Z)=(3,3) and (48,3) mm, so the sleeve axis is X=25.5 mm, Z=3 mm, parallel to Y. Use 360 mm length matching the rods unless the user specifies another length. Preserve these requested diameters and the existing geometry; measure and report actual intersections rather than silently resizing the sleeve or other parts. Add the sleeve to the current mechanical assembly and keep the standalone part editable.

- Match the Coldfinger-v2 lower device-mounting hole row on the indicated raised boss face: 16 mm centre spacing, right-hand M3 x 0.5 - 6H internal threads. Extend the current two device mounting holes into eight positions at local Y=17.82802366515844 + 16*n mm (n=0..7), retaining the existing two screw locations and unchanged carrier placement. Preserve the solid plate and boss. Record real Inventor thread features, not only plain bores. The reference drawing has an inconsistent 4 mm drill / 6 mm thread depth callout; retain the existing 6 mm model depth rather than copying the contradictory 4 mm pilot depth.

- Latest top-view correction and annotated follow-up: fill both empty longitudinal openings completely, making one solid plate across the rods. The device screw-mounting face must project integrally above this plate. Put this raised boss under the holder body on the inside of its existing flange, matching the PPT end-view silhouette. The follow-up clarifies the missing plate material and projecting mounting face; retain the existing device slots rather than inventing another hole pattern. Preserve the original holder and maximize rod contact. This supersedes the open-frame adapter and the previous boss outside the holder footprint.

- The user identified `assembly_coldfinger_v2.SLDASM` as the combined reference. Its imported assembly confirms that Top_ForFridge mounts by its existing side slots to the narrow Coldfinger-v2 support. Use this side-clamp interface, with the device body exposed. The current concept uses 150 x 6 mm continuous contact on each rod in the free middle bay and two M3 device screws at the existing 16 mm slot pitch. All new thicknesses and fastener details remain provisional; preserve the existing device slots and rod holes.

- Build the user's sketched rod-to-holder adapter as a separate mechanical part and review assembly. Latest correction: do not cover or surround the original device/holder with a broad saddle. Use the hanging and screw-tightened attachment method demonstrated in the read-only ColdFinger DilFridge mechanical v2 reference. Inspect that mechanism before redesigning the adapter. Maximize contact with both rods using extended contact surfaces and distributed clamping, while keeping the device body exposed. Retain the carrier, PCB, and H-frame source models unchanged. Match the rod M3 pattern and use the existing device mounting feature; record provisional dimensions as editable parameters. Do not add or move holes in the reference holder. This supersedes the previous broad raised-saddle adapter.

- Build a separate simplified H-shaped probe support frame from the supplied SO01373.10-Probe-R01.pdf: two copper rods, 360 mm long, 6 mm wide, with 45 mm centre spacing (51 mm overall width and 39 mm clear gap), 33 M3 through-thread locations per rod at 10 mm pitch starting 30 mm below the top. Exclude the upper anchor, lower mechanism and enclosing tube. Use two crossbars at approximately 110 and 270 mm below the top, with estimated 8 mm height. Rod/crossbar front-to-back depth is not dimensioned: use an explicitly provisional 6 mm and retain editable parameters. Model M3 threads as simplified cylindrical openings; do not invent unshown fastener details. Preserve the existing PCB/carrier assembly and save the frame separately in the repository.

- Export the current PCB as a simplified mechanical 3D model for an Inventor assembly. Preserve board outline, thickness, mounting holes, QD pocket, component positions and sides, and component envelope dimensions/heights. Simplify resistor and capacitor models but retain their physical sizes and heights. Fit the SMP/Top PCB face to Bottom.SLDPRT, and the opposite QD/Bottom PCB face to Top_ForFridge.SLDPRT from the read-only Narrow_V3_24DC_8MW reference folder. The latest user clarification selects Top_ForFridge instead of Top.SLDPRT and accepts the SMP overlaps for this assembly pass. Save the derived assembly and models in the working repository; do not overwrite the reference SolidWorks files.

- Latest lower-pair refinement: move R1/C1 and R5/C5 toward X=9.75 mm so that each pair centre is at 70% of its previous distance from this board centreline. Define each pair centre by the union of its pad envelopes. Move each pair rigidly in X, preserving Y, spacing and rotations; reconnect RF and DC and rebuild masks and shielding. This is an additional move from the saved revision immediately before this request.
- Move upper R3/C3 and R4/C4 upward by 2.0 mm, away from the QD bond pads. Move both lower R1/C1 and R5/C5 upward by 1.0 mm, as confirmed by the user. Additionally move R1/C1 inward by 0.35 mm. Preserve pair spacing and rotations; reconnect RF/DC without adding transition vias.
- Increase the retained solder-control margin around each R/C group from 0.30 to 0.90 mm. Use exact axis-aligned group rectangles, not rounded convex-hull patches. Preserve normal SMD pad openings and paste, RF coverage and the unmasked QD field.
- Cover the complete Bottom ZIF fanout-via array with a rectangular solder-mask area, extending 0.40 mm beyond its via lands.
