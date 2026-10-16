# QD4 / 2SET 38-pad carrier

## Current saved design (2026-10-16)

Open [QSTL_QD4_2SET_38PAD.PrjPcb](QSTL_QD4_2SET_38PAD.PrjPcb). The accepted 16-RF / 38-DC relocation is implemented in this project's PCB and schematic, including 0603 resistors, exact Yageo CC1206JKNPO9BN104 1206 capacitors, the 32.600 x 99.025 mm outline, relocated ZIF and reference P/A mounting axes.

DC is routed on L2 and L3, nineteen nets per layer, with the long runs centred at X=9.75 mm in a 4.805 mm copper envelope. L4 is GND. The updated ZIF assignments are synchronized with the schematic and [pin map](pin_mapping.csv). Saved/reopened native checks found 71 connected named nets, zero unrouted connections, zero DRC violations and zero enumerated schematic compiler violations.

The authoritative current PCB SHA256 is `0adecc99d347b092775e4fe84506e643e7af0a8ce49d43413f4dc0239a6f58de`. See the [current implementation report](Native_Applied_20261016/IMPLEMENTATION_REPORT.md), [saved RF/DC image](Native_Applied_20261016/Saved_RF_DC_Layers.png) and [validation manifest](Native_Applied_20261016/final_status.json). Manufacturing stack acceptance, impedance certification and the inherited SMP component-PTH annular-ring review remain separate. No production Gerber release accompanies this commit.

The sections and dated proposal folders below preserve design history. They do not describe the current native geometry or layer assignment when they disagree with the current report above.

## Historical relocation component basis (2026-10-14)

The [latest SMP-to-QD connection plan](Relocation_RF_Plan_20261014/README.md) uses the exact horizontal-end-pair mechanical relocation coordinates and the corrected pad midpoints below. Its image labels all 16 existing SMP circuit IDs and QD destinations with a matching table. Existing circuit membership and all DC mapping are retained; physical circuit locations change only in the proposed plan. The coloured guides are not a native reroute or proof of R0603/C1206 component fit.

The corrected relocation review aligns the **midpoints of both short end edges** of all 38 QD bond pads on common per-side inner and outer lines. The [midpoint comparison and enlarged detail](../script/qd38_dual_pad_alignment_20261014/Short_Edge_Midpoints_Aligned_Review.png) marks those midpoints with cyan and pink dots. Width stays 0.25 mm, existing bond-parallel directions stay fixed, and lengths become 0.800..1.005 mm. Inner midpoint guides are X=7.32/12.18, Y=39.57/45.43 mm; outer guides are X=6.52/12.98, Y=38.77/46.23 mm. The 0.08 mm outward shift from the previous corner guides preserves at least 0.20 mm physical cavity clearance. Pad-only checks give 0.162111 mm pad gap, 0.150327 mm foreign signal-via gap, 0.211723 mm cavity clearance and containment of all existing QD drills. See the [review manifest](../script/qd38_dual_pad_alignment_20261014/midpoint_review_manifest.json). This is an unapplied geometry review; native PCB/schematic/library are unchanged, and full routing, GND, shield, mask and native DRC checks remain pending implementation.

The previous [extremal-corner comparison](../script/qd38_dual_pad_alignment_20261014/Both_Pad_Ends_Aligned_Review.png) misinterpreted the datum and is rejected/superseded. It was not applied to the native design. The saved native revision documented below remains historical evidence for its own geometry only.

The user specifies 0603 imperial resistors and exact Yageo `CC1206JKNPO9BN104` 1206 capacitors for all 16 bias-tee pairs in subsequent relocation reviews. The saved board and historical relocation preview below still contain 0603 resistors and `FP-GCM155-0_05-IPC_A` 0402 capacitors; they do not establish fit for the larger parts. This requirement is recorded but no native replacement or placement change is applied by this clarification. See the [current design requirements](../QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md).

## Last saved native revision

Revision status: 2026-10-11, QD pad-end alignment correction. **Applied to the native PCB and canonical library, saved, reopened and verified. All 38 DC channels and 16 RF bias tees remain connected; stored connections are zero. Full Altium DRC reports zero violations across 23 rule instances.** Native PCB SHA256: `9607d5bfbdd962c49c9a6d4ecce671a4de9f5552322f134225bcbadf5796e351`. The [final completion audit](../script/qd38_pad_alignment_20261011/alignment_completion_audit.json) binds the saved copper, schematic, library, stack, rules, surfaces, models, paste CAM and comparison images.

The verified [alignment_full_candidate.json](../script/qd38_pad_alignment_20261011/alignment_full_candidate.json) has SHA256 `4e4264afef78d39bbc27740630d56468f2d3029b03f5019c05e0e3c32f80f28c`. This is a design verification candidate, not a fabrication release or measured RF-performance certification.

Open [QSTL_QD4_2SET_38PAD.PrjPcb](QSTL_QD4_2SET_38PAD.PrjPcb) in `C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD`. This is the copied project explicitly requested for the 38-pad redesign. Preserve the original `QSTL_24DC_4MW_PCB` project, read-only reference PCBs and source GDS. Source hashes are recorded in [copy_provenance.json](copy_provenance.json).

## Pad-end correction and retained geometry

The earlier layout combined bond-direction rotation with independent pad offsets for via clearance. This produced uneven inward pad-end boundaries. The correction treats bond direction and inner boundary as separate constraints: retain each rectangular pad's **0.80 x 0.25 mm** size and bond-parallel angle, and translate along its existing long axis until its inward supporting corner touches the assigned common boundary.

- Sample centre remains **(9.75, 42.5) mm**; the complete QD geometry remains rotated +90 degrees counterclockwise. All 38 terminal numbers, chip-to-pad bond directions and bond ordering are retained.
- Common inward supporting lines are **X=7.40/12.10 mm** and **Y=39.65/45.35 mm**, enclosing a **4.7 x 5.7 mm** rectangle. These align the nearest inward corners, **not the complete tilted short edges or outer ends**. Corner-category pads retain their assigned horizontal side.
- Fourteen pad centres move; RF pads 2 and 21 are included. The existing RF terminal copper still overlaps those two pads, so every RF track and arc is retained unchanged. Twelve direct-DC endpoint positions and their local DC tails are repaired; other routing and all net assignments remain unchanged.
- All 22 direct QD DC vias use **0.35 mm lands and unchanged 0.20 mm through drills**, with the complete drill contained inside its bonding pad. The former 0.40 mm lands could not satisfy the 0.15 mm foreign-copper gap with the aligned, fixed-size pads. The new nominal radial annular ring is 0.075 mm; this geometry alone is not supplier acceptance.
- The Bottom blind pocket remains **4.3 mm in X by 5.3 mm in Y**, R0.5, **1.2 mm deep**, with envelope X=7.60..11.90 mm and Y=39.85..45.15 mm. The inner pad boundary retains 0.20 mm cavity clearance. Mechanical 3 documents the non-plated blind pocket; it is not a through-board cutout.
- Keep GND out of the 4.7 x 5.7 mm inner rectangle on every copper layer except Top. Preserve Top GND there and the complete Bottom bond-field mask opening.

The board outline remains 19.5 x 67.9 mm. Sixteen SMP connectors retain seven rows, **3 / 2 / 2 / 2 (QD) / 2 / 2 / 3**, at Y=24.5, 30.5, 36.5, 42.5, 48.5, 54.5 and 60.5 mm. Side columns remain X=3.75/15.75 mm, with an additional X=9.75 mm connector in each end row. All SMP, R/C and ZIF placements are unchanged by this correction.

## Electrical topology and routing

All **38 QD terminals have independent DC connections**. Sixteen selected terminals also have RF bias tees; the other 22 connect directly to DC. The exact ZIF contact set remains **all 24 even contacts 2,4,...,48 plus the first 14 odd contacts 1,3,...,27**. Pin 50 is unused. The schematic, PCB, libraries and [pin_mapping.csv](pin_mapping.csv) must retain the same current mapping.

Anton's unchanged 25-pin adapter reaches only the 24 even-contact channels; it cannot transport all 38 independent channels. The separately rerouted FPC DSUB adapter has its own mapping. Neither should be assumed functionally compatible merely because the mating contact positions are shared.

Each DC net uses one complete internal layer, L2 or L4, with no standalone transition vias. There are 19 routes on each layer. DC straight segments follow the intended routing axes with 45-degree transitions and no sharper turns outside endpoint copper. Both internal layers exclude the complete five-pad SMP envelope and the full resistor two-pad/body envelope; only the intended local approach to a resistor's own DC pad 2 is permitted.

Every RF route stays on Bottom with **zero RF signal vias**: SMP signal pin -> capacitor pad 1, then capacitor pad 2 -> resistor RF pad 1 -> QD pad. Resistor pad 2 supplies DC bias. The accepted RF-channel permutation and genuine tangent curves are retained. Unrelated RF copper must not cross resistor body/inter-pad envelopes.

## Stack, clearances and vias

From the QD side, the six-layer stack is RF / GND / DC / GND / DC / GND. Preserve the matching 1078 outer dielectric stack and existing layer thicknesses: nominal copper 0.035/0.0152/0.0152/0.0152/0.0152/0.035 mm, dielectric gaps 0.0784/0.55/0.2008/0.55/0.0784 mm. The historical native stack measured approximately 15.199 um internal signal copper and 35.001 um outer copper; the new saved board must preserve it.

| Constraint | Requirement |
| --- | --- |
| Bottom RF width / coplanar GND gap | 0.11 / 0.20 mm |
| Internal DC width | 0.125 mm |
| Different DC nets on L2/L4 | At least 0.10 mm, with routing margin |
| Internal DC to actual GND copper, including plated lands | At least 0.20 mm |
| Other foreign signal, SMP-envelope and resistor-envelope clearance | At least 0.15 mm |
| Hole-to-hole clearance | Existing 0.254 mm requirement |

The selective DC-pair rule must include actual internal copper of through vias and pads. Preserve the remaining clearance scopes, hole rules, mask-sliver rules and enabled checks; do not suppress genuine failures. The direct-QD routing-via rule must now match 0.35/0.20 mm.

| Via group | Count | Land / drill | Span |
| --- | ---: | --- | --- |
| Direct QD DC endpoints | 22 | 0.35 / 0.20 mm | Top through Bottom; drill contained in pad |
| Bias-resistor DC pad 2 | 16 | 0.50 / 0.25 mm | Top through Bottom |
| ZIF fanout endpoints | 38 | 0.40 / 0.20 mm | Top through Bottom |
| GND RF shields | 668 | 0.25 / 0.10 mm | L5 to Bottom only |

All 16 SMP rings retain 11 shield vias each, on the existing 1.05 mm radius and 22.5-degree angular grid with symmetric RF escape gaps. RF fences retain the nominal 0.435 mm trace-to-via centre offset where possible. Shield vias never penetrate either DC layer and do not cross R/C body envelopes.

## Local ground, masks and paste

The alignment update removes ground only where the moved signal copper requires additional clearance. It starts from the actual saved-native contours, retains old voids, and does not refill or rebuild remote ground. Native-grid comparison proves **no GND additions and no changes outside X=5.5..14.0, Y=36.0..49.0 mm on all six layers**. The resulting GND remains one connected network. Prequantized replacement contours must be exported without a second global simplification.

All existing mask regions and shields are retained. The approved larger QD mask opening fully exposes the new pad field and cavity; it is intentionally not reduced to the new bounding rectangle. Preserve the protected RF strip, 0.90 mm rectangular R/C mask margins, Bottom ZIF-via rectangle, normal component openings and SMP solder-control masks. Mounting lands remain exposed on both faces with direct GND connections and no thermals.

Retain the previous 0.025 mm aperture expansion on the 18 repaired Bottom R/C pads and all other mask settings. Paste remains disabled for vias, SMP, mounting and QD wire-bond pads; ordinary J1 and R/C SMD paste remains, including normal pad paste over via-in-pad joints. Native via paste-enabled flags alone do not establish CAM aperture presence. Fresh effective Top/Bottom paste CAM has been checked against the final saved hash.

## Completed verification

The following geometric reports bind to this correction:

- [Full alignment audit](../script/qd38_pad_alignment_20261011/alignment_full_audit.json): all signal connectivity, permitted DC turns, foreign clearances, ground connectivity, mask, shield and QD exclusion checks pass.
- [Local DC audit](../script/qd38_pad_alignment_20261011/alignment_local_delta_audit.json): twelve local endpoint repairs, unchanged distant routing, net/layer assignments and RF copper. Minimum DC gap is approximately 0.105 mm.
- [Independent via placement audit](../script/qd38_pad_alignment_20261011/independent_aligned_via_placement.json): full drill containment; minimum foreign-pad gap 0.150327 mm, via-land gap 0.150417 mm and hole gap 0.300416 mm after native-grid quantization.
- [Independent surface audit](../script/qd38_pad_alignment_20261011/independent_alignment_surfaces.json) and [native-grid locality audit](../script/qd38_pad_alignment_20261011/alignment_native_grid_locality.json): unchanged masks/RF/668 shields, local subtractive ground only, and at least 0.20 mm signal-to-GND clearance. Retained RF overlap areas at QD pads 2/21 are approximately 0.028952/0.029233 mmÂ².

Saved-native results also pass:

- [Saved copper and schematic correspondence](../script/qd38_pad_alignment_20261011/saved_revision_audit.json): 50 components, 243 pads, 585 signal tracks, 66 Bottom RF arcs and 744 vias; zero stored connections; all DC nets remain on one internal layer and RF has no signal vias.
- [Canonical library](../script/qd38_pad_alignment_20261011/canonical_library_audit.json) and [local alignment delta](../script/qd38_pad_alignment_20261011/saved_alignment_delta.json): pad sizes, bond angles, terminal identities and net mapping retained, with common inward supporting lines. Only library XY fields changed; other library bytes and GUIDs are unchanged.
- [Saved rules](../script/qd38_pad_alignment_20261011/saved_alignment_rules.json), [surfaces](../script/qd38_pad_alignment_20261011/saved_revision_surface.json) and [models](../script/qd38_pad_alignment_20261011/saved_revision_models.json): only the three QD-via diameter fields changed in the rules; masks, shields, model transforms and stack are preserved.
- [Complete native DRC](../script/qd38_pad_alignment_20261011/Native_DRC.html): 23 rule instances, zero violations. Live compiled membership matches; the UI reported "Compile successful, no errors found" while the compiler API still returned False with zero reported violations.
- [Effective paste CAM](../script/qd38_pad_alignment_20261011/revision_native_paste_cam_validation.json): 53 Top and 64 Bottom ordinary SMD apertures, with no extra via/SMP/mount/QD paste.
- [Actual saved pad comparison](review/QD_pad_end_alignment_before_after.png), [aligned QD close-up](review/QD_pad_end_alignment.png), [current DC](review/DC_saved_two_layers.png) and [current RF](review/RF_saved_bottom.png).

The first save retained 751 connection-display records despite independently connected physical copper and zero unrouted DRC violations. This evidence is preserved under [first_save_connection_cache](../script/qd38_pad_alignment_20261011/first_save_connection_cache/). Rebuilding every existing net with Altium's native Rebuild operation, followed by fresh save/reopen and DRC, produced zero stored records. No connection objects were manually deleted and no rule was disabled.

The 50-ohm RF geometry is a target, not a measured result. Unchanged close QD approaches include RF gaps near 0.151 mm and cannot all accommodate independent coplanar GND strips with a 0.20 mm gap on both sides. Historical proximity analysis found about 2.04-2.06 mm of MW28/MW30 and 4.54-4.72 mm of MW11/MW12 below a 0.40 mm edge gap outside the prior field. Passing copper DRC does not validate their coupling, impedance, assembled hardware behaviour or bench performance.

## Historical verified revision

The immediately preceding native PCB SHA256 was `1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c`, paired with candidate `835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495`. Its [completion audit](../script/qd38_rotation_20261011/revision_completion_audit.json) passed: zero stored connections, 23 Altium DRC instances with zero violations, effective paste CAM with 53 Top/64 Bottom apertures, synchronized schematic/library and source-preservation checks. Those results apply only to the recorded historical hashes. That revision used 0.40/0.20 mm QD vias and independently shifted pad ends; its geometry is superseded here.

The previous native compiler API returned `False` despite the UI reporting successful compilation and the independently verified membership showing 86 compiled nets and zero violations. Preserve this distinction; do not recast the API result as `True`. The earlier pre-rotation PCB also passed its native DRC while failing independent routing-shape checks; DRC alone is not proof of the requirements above.

The preceding board and README are preserved in [before_alignment](../script/qd38_pad_alignment_20261011/before_alignment/), with earlier evidence under [qd38_rotation_20261011](../script/qd38_rotation_20261011/) and [qd38_carrier_20261010](../script/qd38_carrier_20261010/).

No production Gerber package, supplier release, purchase or Git push is part of this correction. Diagnostic paste CAM is verification evidence, not a manufacturing package. Fabrication acceptance and bench performance remain unverified.
