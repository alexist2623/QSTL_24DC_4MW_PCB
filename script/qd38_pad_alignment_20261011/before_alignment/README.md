# QD4 / 2SET 38-pad carrier

Revision status: 2026-10-11. The +90-degree QD placement and replacement DC/RF routing have been applied to the native PCB, saved and reopened. **Saved copper/connectivity, schematic membership, models, rules, stack, masks and ground checks pass. Full Altium DRC reports zero violations across 23 rule instances, and the saved board has zero outstanding connections.** The current native PCB SHA256 is `1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c`; the corresponding final candidate SHA256 is `835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495`.

**Effective paste-only CAM verification and the final mutually hash-bound completion audit also pass.** [revision_completion_audit.json](../script/qd38_rotation_20261011/revision_completion_audit.json) records `completion: true` for the hashes above. The design revision and its stated verification are complete; this is not a fabrication release or an end-to-end RF-performance certification. Current saved-geometry previews: [DC on both internal layers](review/DC_saved_two_layers.png) and [Bottom RF](review/RF_saved_bottom.png).

Open [QSTL_QD4_2SET_38PAD.PrjPcb](QSTL_QD4_2SET_38PAD.PrjPcb) from `C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD`. This is the separate project explicitly requested for the QD4/2SET redesign. Preserve the original `QSTL_24DC_4MW_PCB` project, reference PCBs and source GDS. [copy_provenance.json](copy_provenance.json) records the original source hashes; all 12 recorded original project/source files are unchanged in the current saved-native audit.

## Current revision geometry

- The saved board outline remains 19.5 x 67.9 mm, with 50 components, 243 physical pads, 582 signal tracks, 66 Bottom RF arcs and 744 vias. Native route cleanup split the candidate's 62 RF arcs into 66 stored RF arcs; the combined line/arc/pad geometry remains equivalent within the unchanged 0.00001 mm spatial tolerance. The vias comprise 76 signal endpoints and 668 GND shields.
- Rotate the complete QD bond-pad field and blind-pocket geometry +90 degrees counterclockwise about the unchanged sample centre, **(9.75, 42.5) mm**. Keep all 38 chip-terminal numbers and bond directions. Eleven direct-DC bond pads are shifted outward along their existing bond directions by at most 0.225 mm to accommodate contained through drills; their sizes and angles, and all 16 RF bond-pad positions, are preserved.
- The rotated Bottom blind pocket measures **4.3 mm in X by 5.3 mm in Y**, R0.5, and remains **1.2 mm deep**. Its rectangular envelope is X=7.60..11.90 mm and Y=39.85..45.15 mm. Mechanical 3 documents the non-plated blind pocket; it must not become a through-board cutout.
- The rotated **4.7 x 5.7 mm** inner QD rectangle excludes GND on every layer except Top. Preserve Top GND and the Bottom bond-field mask opening.
- Sixteen SMP connectors use seven rows: **3 / 2 / 2 / 2 (QD) / 2 / 2 / 3**, at Y=24.5, 30.5, 36.5, 42.5, 48.5, 54.5 and 60.5 mm. The side columns are X=3.75 and 15.75 mm; the extra connector in each end row is X=9.75 mm. Thus seven connectors are above the sample, seven below, and two beside it.
- R/C placements are adjusted to create legal DC corridors and inline RF approaches. The complete five-pad SMP envelopes and the resistor two-pad/inter-pad envelopes are excluded from DC routing on both internal DC layers. An intended DC route may enter only its own resistor pad 2 from outside the excluded body.

The shared physical placement is [placement_lower_over_smp_candidate.json](../script/qd38_rotation_20261011/placement_lower_over_smp_candidate.json), SHA256 `99a7cc8fef9c21e235f47fbdc24733121a37e6ddc4a939d6d92f4fbdb1d70c0e`. Its [static placement audit](../script/qd38_rotation_20261011/placement_lower_over_smp_audit.json) does not replace the subsequent routing or saved-native checks.

## Electrical topology and ZIF correspondence

All **38 QD terminals have independent DC connections**. The 16 selected RF-capable terminals additionally use resistor/capacitor bias tees; an RF connection never replaces the terminal's DC connection. The other 22 terminals connect directly to DC.

Use exactly **24 legacy even ZIF contacts 2,4,...,48 plus the first 14 unused odd contacts 1,3,...,27**. Pin 50 remains unused. The user permits chip-terminal-to-ZIF reassignment to resolve crossings. The saved PCB, copied schematic, synchronized libraries and [pin_mapping.csv](pin_mapping.csv) agree with the final candidate; live compiled membership and native component SourceUniqueIDs have been checked. Use the current pin table rather than a historical mapping.

Preserving the 24 legacy contact positions does not preserve an invented functional mapping between the old 24-pad device and the new 38-pad chip. Anton's unchanged 25-pin adapter reaches the 24 even-contact channels only; it cannot carry all 38 independent DC channels. The separately rerouted FPC DSUB adapter also has its own mapping.

Each DC net uses **one complete internal routing layer**, L2 or L4, between two existing full-through endpoint vias. There are **no standalone DC layer-transition vias**. The selected route has 19 channels on each layer; equal layer counts are a result, not a design requirement. DC trunks use horizontal/vertical straight segments and 45-degree transitions, with no turns exceeding 45 degrees outside their endpoint copper.

RF remains entirely on **Bottom**, with **zero RF signal vias**. The chain is SMP signal pin -> capacitor pad 1, then capacitor pad 2 -> resistor RF pad 1 -> QD pad. Resistor pad 2 supplies the independent DC bias. The accepted SMP/bias-tee-to-QD permutation is synchronized across the schematic, DC net labels, ZIF assignments and pin table. Saved RF topology and tangent arcs pass the independent checks; unrelated copper does not cross a resistor's two-pad/body envelope.

## Routing and rule changes

The saved revision preserves the six-layer stack, 0.11 mm RF width and 0.20 mm coplanar GND gap. The inherited stack records approximately 15.199 um copper on L2/L4 and 35.001 um on the outer layers; saved stack preservation is verified. The 50-ohm target continues to depend on the existing matching 1078 outer dielectric geometry. It is not an end-to-end impedance measurement or a claim that dense QD approaches maintain isolated 50-ohm transmission-line behaviour.

| Constraint | Revision requirement |
| --- | --- |
| Internal DC width | 0.125 mm |
| Different DC nets on L2/L4 | 0.100 mm minimum, with additional solver margin |
| Internal L2/L4 DC to actual GND copper, including plated GND lands | 0.200 mm minimum |
| DC to unrelated non-DC copper | 0.150 mm minimum |
| DC to complete SMP five-pad envelope | 0.150 mm minimum |
| DC to resistor body/inter-pad envelope | 0.150 mm minimum, except local entry to its own DC pad 2 |
| Other-layer endpoint/fanout clearances | Existing 0.150 mm minimum retained |

The saved rule set includes `QD38_DC_PAIR_GAP_0P1` for the authorized selective DC clearance and `QD38_QD_VIA_0P4_0P2` for direct QD endpoint vias. The DC-pair and DC/GND scopes use `ExistsOnLayer` to include actual internal-layer copper of through vias and pads; the independent saved-copper checks retain the original spacing on other layers. The general 0.15 mm clearance, 0.20 mm DC/GND rule, hole spacing, mask sliver limits and existing rule enable states are preserved. There are 44 saved rule objects, including four routing-via rules; no genuine violation was suppressed to obtain the 23-instance zero-violation DRC result.

| Via group | Count | Land / drill | Span |
| --- | ---: | --- | --- |
| Direct QD DC endpoints | 22 | 0.40 / 0.20 mm | Top through Bottom, drill contained in its bond pad |
| Bias-resistor DC pad 2 | 16 | 0.50 / 0.25 mm | Top through Bottom |
| ZIF fanout endpoints | 38 | 0.40 / 0.20 mm | Top through Bottom |
| GND RF shields | 668, verified in the saved native PCB | 0.25 / 0.10 mm | L5 to Bottom only |

The 76 signal-via positions in the selected DC route match the shared frozen placement. A limited J1 stagger was tested separately and not selected. RF shield microvias must never penetrate L2 or L4. Regenerated SMP rings use the equal-angle grid and symmetric RF escape gaps; R/C shielding must respect the full two-pad/body envelopes.

## Selected offline DC route

The selected input is [dc_final_candidate.json](../script/qd38_rotation_20261011/dc_final_candidate.json), SHA256 `eefbfe8ff5a56f85c61db86a75646cf87397af0d012d526a2af8694ae3d064ca`. This is the DC geometry checkpoint before final RF channel relabelling and full ground/mask integration. Its hash is not the eventual native PCB hash.

The [independent quantized DC audit](../script/qd38_rotation_20261011/dc_fallback_rechecked_independent_audit.json) passes all 38 connections, one internal layer per net, exact ZIF contact pool, full-through endpoint checks, width, direction, clearance, pocket and envelope checks. Coordinates were quantized to the native 2.54e-6 mm unit before measurement.

| Measured DC property | Selected route |
| --- | ---: |
| Total turns / maximum per net | 345 / 15 |
| Total internal DC length | 1784.768 mm |
| Length-weighted mean distance from X=9.75 mm | 4.822 mm |
| Minimum DC-to-DC copper gap | 0.104999 mm |
| Minimum DC-to-GND copper gap | 0.212499 mm |
| Minimum resistor-envelope gap | 0.162758 mm |
| Minimum full SMP-envelope gap | 0.212499 mm |
| Minimum Top fanout gap | 0.324999 mm |

[dc_selection_report.json](../script/qd38_rotation_20261011/dc_selection_report.json) preserves the comparison with two J1-stagger alternatives. The corrected two-pass trial reserves only selected-layer escape stubs while retaining all actual via lands on both layers. It passed, but reduced the mean centreline distance by only 0.124 mm and total route length by 19.951 mm while adding 36 turns and raising the maximum to 20. The simpler 345-turn route was retained. This is a practical comparison, not a proof of global routing optimality. [DC route preview](../script/qd38_rotation_20261011/dc_final_preview.png).

The table above describes the selected DC-route checkpoint. After final GND integration and native save/reopen, the measured DC width is **0.12500102 mm**, minimum DC-to-DC gap is **0.10499852 mm**, and minimum DC-to-GND gaps are **0.202028725 mm on L2** and **0.202011980 mm on L4**. These saved measurements supersede the route-checkpoint GND-gap figure for the final board. The 0.20 mm DC/GND requirement applies to the two internal DC layers; it does not assert a 0.20 mm gap on every other layer. Existing Bottom endpoint geometry includes an approximately 0.18 mm gap governed by the unchanged general 0.15 mm rule.

The final offline RF input is [rf_widened_candidate.json](../script/qd38_rotation_20261011/rf_widened_candidate.json), SHA256 `1a8daecb578d5f708311ee388f1221cd238111ea655ebc8db318443bf0f8a53e`. Its **62 tangent RF arcs** replace the superseded sharp-corner geometry. The [geometry and topology audit](../script/qd38_rotation_20261011/rf_widened_audit.json) reports a pass, zero quality flags, minimum RF/foreign static gap 0.151013 mm, minimum RF/RF gap 0.151012 mm and minimum unrelated resistor-body gap 0.153182 mm. This widened route supersedes the earlier `rf_planar_fullpad_curved_candidate.json` input.

The [RF proximity review](../script/qd38_rotation_20261011/rf_widened_parallel_regions.json) still identifies closely spaced approaches near the QD. MW28/MW30 have a minimum edge gap of approximately 0.151013 mm and about 2.04-2.06 mm of route below a 0.40 mm edge gap outside the QD field. MW11/MW12 reach 0.156 mm, with approximately 4.54-4.72 mm below 0.40 mm outside that field. A 0.40 mm edge gap is only the sum of two 0.20 mm coplanar clearances, before allowing any intervening GND width; it is not an additional approved manufacturing clearance rule. These passages cannot accommodate separate coplanar GND strips with the nominal gap on both sides. Passing copper-clearance checks does not verify their coupling, impedance or RF performance; those effects have not been measured or electromagnetically validated.

The final [full_copper_candidate.json](../script/qd38_rotation_20261011/full_copper_candidate.json), SHA256 `835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495`, includes the final RF permutation, selected DC geometry, ground, shielding, explicit mask regions and the 18 ordinary-pad mask-expansion overrides described below. Its [complete offline copper audit](../script/qd38_rotation_20261011/full_copper_audit.json) passes with 582 track primitives, 62 signal arcs, 76 signal vias and no disconnected nets or invalid DC turns. The [shield/surface geometry audit](../script/qd38_rotation_20261011/shield_surface_audit.json) passes for 668 GND microvias, all grounded on both intended layers, with a minimum Bottom signal-to-shield-land gap of **0.203391 mm**. All 16 SMP rings have **11 vias each**, on a 1.05 mm radius and 22.5-degree grid with symmetric escape gaps. The corresponding saved-native copper, surface and ring checks also pass.

## Saved masks, paste and ground

Saved explicit mask geometry removes general coverage while retaining solder-control regions around ordinary soldering sites, the protected RF strip, 0.90 mm rectangular R/C group margins and the Bottom ZIF via-array rectangle with its 0.40 mm margin. Ordinary pad openings and SMP solder-control masks remain. The complete Bottom QD bond-pad/pocket field is open. Mounting lands are exposed on both faces and connected directly to GND without thermal relief.

The first saved/reopened revision reported 16 genuine minimum solder-mask sliver violations. Repair changed only the positive aperture expansion of 18 Bottom R/C pads from **0.050 to 0.025 mm**: C09-1/2, C12-1/2, C15-2, C21-2, C28-1/2, C31-1/2, R09-1, R12-1, R15-1/2, R21-1/2, R28-1 and R31-1. The smallest repaired pairwise mask sliver is approximately **0.105 mm**, above the unchanged 0.10 mm rule. [The saved mask-repair audit](../script/qd38_rotation_20261011/saved_mask_repair_audit.json) verifies both stored expansion fields on exactly those 18 pads, all 225 unselected pad records, all 243 pad paste settings and all pad copper/net/identity fields. The R/C protected rectangles, SMP masks, RF strip, QD opening, mounting exposure, copper and routing were not changed. The pre-repair candidate `a8e96043d9dcabcbf3b855f37ff28962a55389783f7ca484c95fda7b37b253fe`, native PCB `c179d313dc7d7c1c5851517d779616fbe7c9c3b1e9a5f4ac565e0541c3e0a047` and failed DRC are preserved under [pre_mask_repair](../script/qd38_rotation_20261011/pre_mask_repair/).

The [effective native paste-only CAM audit](../script/qd38_rotation_20261011/revision_native_paste_cam_validation.json) passes with **53 Top apertures and 64 Bottom apertures**, matching normal J1 and R/C SMD pads. No extra or missing paste area is present outside the 0.00005 mm comparison tolerance. There are no via-specific apertures or paste on 80 SMP pads, eight mounting pads or 38 QD wire-bond pads. Normal R/C SMD paste overlapping a via-in-pad is intentionally retained. Altium's native paste-enabled getter reports True for 744 vias despite their negative paste expansion; the actual CAM output, rather than that flag, establishes absence of additional via paste. The rotated non-Top GND exclusion, shield microvias and explicit mask geometry, including RF arcs, also pass saved-native checks.

## Completed verification evidence

The following reports pass and bind to final candidate `835347e3...` and saved native PCB `1ac42a09...` where applicable:

1. [Complete copper audit](../script/qd38_rotation_20261011/full_copper_audit.json), synchronized schematic/net table and [canonical QD footprint-library audit](../script/qd38_rotation_20261011/canonical_library_audit.json).
2. [Saved-native audit](../script/qd38_rotation_20261011/saved_revision_audit.json): application, save/reopen, zero stored connections, 38 independent DC paths, 16 RF bias tees, zero RF vias, pad/net/track/arc/via/region equivalence, direct QD drill containment and unchanged original sources.
3. Live compiled membership matches the synchronized schematic. Altium's UI displayed **"Compile successful, no errors found"**; the log has 86 compiled nets and zero violations. The compiler API nevertheless returned `False`, which remains recorded in [native_compile.txt](../script/qd38_rotation_20261011/native_compile.txt). The verified membership and observed UI success are not a claim that the API returned `True`.
4. Saved DC and RF geometry includes complete SMP/resistor envelopes, actual GND clearance, permitted DC angles, RF tangent arcs and the rotated blind pocket.
5. [Saved rules](../script/qd38_rotation_20261011/saved_revision_rules.json), unchanged stack, [surface/ground semantics](../script/qd38_rotation_20261011/saved_revision_surface.json), direct mounting GND, all 16 SMP rings, [embedded model transforms](../script/qd38_rotation_20261011/saved_revision_models.json) and [ordinary-pad mask repair](../script/qd38_rotation_20261011/saved_mask_repair_audit.json).
6. [Full Altium DRC after save/reopen](../script/qd38_rotation_20261011/Native_DRC.html): **23 reported rule instances, including four routing-via rules, zero violations and no early stop**. This includes the unchanged minimum solder-mask sliver rule.
7. [Effective native paste CAM](../script/qd38_rotation_20261011/revision_native_paste_cam_validation.json): 53 Top and 64 Bottom apertures, no extra or missing apertures, and no via/SMP/mount/QD paste.
8. [Final completion audit](../script/qd38_rotation_20261011/revision_completion_audit.json): `passed: true`, `completion: true`, with candidate, native PCB, schematic, canonical library, rules, model, mask, paste, source-preservation and actual CAM file hashes cross-checked.

The final [completion checker](../script/qd38_rotation_20261011/audit_revision_completion.py) passed at `2026-10-11T22:46:10.860762+00:00`. Its evidence applies only to the recorded files and hashes; subsequent edits require appropriate revalidation. RF coupling, assembled hardware behaviour and fabrication acceptance remain outside this verification scope.

## Historical checkpoint and preservation

The superseded pre-rotation native PCB has SHA256 `f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632`. It was saved/reopened and reported zero stored connections and zero violations across 21 native DRC instances, but independent review found **1,440 DC turns over 45 degrees, 300 sharp RF corners with no native arcs, and 22 direct QD DC vias outside their pads**. Its zero-violation DRC did not establish compliance with those geometric requirements. That checkpoint also used the earlier eight-above/eight-below SMP layout and unrotated 5.3 x 4.3 mm pocket; these are superseded by this revision.

The earlier state and README are preserved under [before_rotation](../script/qd38_rotation_20261011/before_rotation/). Historical evidence remains under [qd38_carrier_20261010](../script/qd38_carrier_20261010/), including the native validation/DRC reports, saved copper and surface audits, embedded-model checks and paste-only CAM audit. Those reports certify only their recorded hashes and scopes. The earlier schematic compiler API returned False despite zero reported violations; preserve that distinction rather than relabelling its result.

The earlier desktop-access and project-open failures were resolved using this computer's `C:\GIT_Workspace` directory and `DM_OpenProject(ProjectPath, True)`. The historical successful native probe records runtime evidence; no unobserved operating-system cause for the prior Access denied message is asserted.

No production Gerber package, supplier release or Git push is part of this revision task. Diagnostic paste-only CAM remains a verification artifact, not a manufacturing package.
