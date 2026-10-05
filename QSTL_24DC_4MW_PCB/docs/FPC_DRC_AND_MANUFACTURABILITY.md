# FPC DRC and manufacturability

Reviewed: 2026-10-05. Units: mm unless stated otherwise.

**Status: engineering designs; not released for fabrication.** This document covers the straight FPC, ZIF-to-two-ZIF branch and ZIF-to-Micro-D adapter. It does not change the carrier PCB's HDI rules. Order settings are recorded in [FPC_ORDER_SPECIFICATION.md](FPC_ORDER_SPECIFICATION.md).

## Saved design baseline

The three PCB files matched their saved geometry-validation SHA-256 values during the 2026-10-05 read-only audit. Copper thickness and track/via sizes were also read directly from the PCB binaries. Documentation work has not changed those files.

| Property | Straight FPC | ZIF-to-two-ZIF | ZIF-to-Micro-D |
| --- | --- | --- | --- |
| Project | [FPC_15015_0451](../FPC_15015_0451/FPC_15015_0451.PrjPcb) | [ZIF_to_2xZIF](../FPC_Adapters_20261002/ZIF_to_2xZIF/ZIF_to_2xZIF.PrjPcb) | [ZIF_to_DSUB25](../FPC_Adapters_20261002/ZIF_to_DSUB25/ZIF_to_DSUB25.PrjPcb) |
| Copper layers / thickness per layer | 1 / 18 um | 2 / 18 um | 2 / 18 um |
| Routed track widths | 0.20 | 0.10, 0.20 | 0.10, 0.20 |
| Integral contact neck / wide finger | 0.10 / 0.30 | 0.10 / 0.30 | 0.10 / 0.30 |
| Contact pitch / mating width | 0.30 / 15.60 | 0.30 / 15.60 | 0.30 / 15.60 |
| Minimum different-net copper gap | 0.0707105 | 0.0707105 | 0.0707105 |
| Via count; drill / land diameter | None | 51; 0.10 / 0.30 | 12; 0.20 / 0.40 |
| Connector signal PTH drill / land | None | None | 0.7112 / 0.9652 |
| Connector signal radial annulus | N/A | N/A | 0.127 |
| Boardlock drills | None | None | 2 x 2.69 |

The contact necks/fingers include copper regions, so track-width checks alone do not cover their geometry. The narrowest gap is at opposing diagonal contact transitions. It is not the 0.10 mm gap between the straight 0.20 mm conductors on 0.30 mm pitch. Micro-D radial annulus is `(0.9652 - 0.7112) / 2 = 0.127`.

## Supplier limits

The following compact reference is from [JLCPCB Flex PCB Capabilities](https://jlcpcb.com/capabilities/flex-pcb-capabilities), checked 2026-10-05. Width/space values use `1 mil = 0.0254 mm`.

| Copper | Regular width / space | Absolute width / space limit |
| --- | --- | --- |
| 12 um | 0.0762 / 0.0762 | 0.0508 / 0.0508 |
| 18 um | 0.0889 / 0.0889 | Supplier inquiry |
| 35 um | 0.1016 / 0.1016 | Supplier inquiry |

The 12 um entry's 2/2 mil absolute limit describes manufacturing capability; it is not a verified separate orderable process name. Extra charges for this line/space capability have not been confirmed. This is distinct from the fine-via option's explicitly stated extra cost below.

| Feature | Published limit |
| --- | --- |
| Via drill / land, regular | 0.30 / 0.55 |
| Via drill / land, two-layer extreme | 0.10 / 0.30; extra cost |
| PTH radial annulus | 0.25 recommended; 0.18 absolute |
| Via land to trace | >= 0.10 |
| Exposed pad to trace | >= 0.15 |
| NPTH to copper | >= 0.20 |
| Coverlay expansion / opening-to-trace | 0.10 / >= 0.15 |
| Coverlay bridge | >= 0.50 |
| Copper to outline / slot | >= 0.30 |
| Gold finger to outline | >= 0.20 |
| Silkscreen height / stroke / pad gap | >= 1.00 / 0.15 / 0.15 |
| Trace-width tolerance | +/-20% |

The [FPC product page](https://jlcpcb.com/pcb-fabrication/flexible-pcb) lists a different regular via drill/land pair, 0.15/0.35, while the detailed capability table lists 0.30/0.55. Obtain a written process-specific answer before relying on the smaller regular pair. Do not silently choose the more permissive webpage.

## Findings for the current artwork

| ID | Finding | Required disposition |
| --- | --- | --- |
| FPC-01 | All three contact gaps are below the 18 um regular minimum. Track widths alone pass that minimum. | Revise the transitions while preserving mating compatibility, or obtain explicit acceptance of the actual artwork and stack. No accepted exception is recorded. |
| FPC-02 | The branch drill/land pair is at the published two-layer extreme limit. | Obtain the matching drill process and cost; keep the junction out of bending zones. |
| FPC-03 | Micro-D signal annulus is below the absolute PTH limit. | Enlarge/rework pads and adjacent routing, or document supplier acceptance. Reducing copper thickness does not increase annulus. |
| FPC-04 | Micro-D 0.20/0.40 vias are below the detailed page's regular pair, although above its two-layer extreme pair. | Resolve the conflicting regular-via publications in the quote. Do not label these vias unconditionally standard. |
| FPC-05 | Current checks establish copper containment, not the required copper/finger setback everywhere along the outline. | Measure actual edge/slot clearances, including contact tips and outer fingers; revise or obtain accepted contact-specific geometry. |
| FPC-06 | Individual DSUB mask webs were replaced by grouped row openings. Via openings are closed; contact arrays use grouped openings. | Check opening registration, unrelated copper near exposed pads, residual bridges and final CAM apertures against the chosen flex process. |
| FPC-07 | Saved stack and backing are reconstruction/design assumptions. | Agree a manufacturable stack and finished connector thickness before export. |
| FPC-08 | Recovered local libraries have independent geometry checks, but final native schematic recompile is pending. | Load libraries and recompile both adapter schematics; resolve real messages and compare the resulting pin/net mapping. |

FPC-01 is a trace/space comparison, not blanket approval of exposed-contact geometry at 12 um. The exposed-pad-to-trace and coverlay requirements are separate checks. Have the supplier review the staggered contact artwork explicitly.

## Existing Altium rules versus a fabrication check

The archived native reports contain 13 listed checks and zero reported violations. They establish compliance with their stored rules only. Their rendered mil values are rounded; the geometric clearance threshold is approximately 0.0707 mm.

| Check | Existing reported setting | Interpretation / future release check |
| --- | --- | --- |
| Global copper clearance | About 0.0707; all objects | Permits the reconstructed contacts. It does not enforce 18 um JLCPCB spacing. |
| Track width | Min 0.10; max 0.30 | Retain at least 0.10 for this design. Evaluate copper-region necks separately. |
| Preferred track width | Straight 0.20; adapters 0.254 | Routing preference, not actual minimum geometry or a supplier requirement. Saved adapter tracks are 0.10/0.20. |
| Hole diameter | Min 0.0254; max 2.54, or 2.70 for Micro-D | Minimum is too permissive for a fabrication profile. Separate vias from connector PTH/NPTH holes and bind sizes to the selected process. |
| Hole-to-hole gap | 0.254 | Stored design constraint; not a verified JLCPCB flex hole-spacing specification. Confirm process requirement. |
| Solder-mask sliver | 0.254 | Does not enforce the flex coverlay-bridge minimum. Validate grouped coverlay openings in CAM. |
| Silk-to-mask / silk-to-silk | 0.254 / 0.254 | Does not establish character height, stroke width or every exposed-pad clearance. |
| Short circuit / unrouted / antenna | Shorts disallowed; zero violations | Keep enabled, rebuild connectivity and inspect after save/reopen. |
| PTH annulus, outline setback, flex stack and stiffeners | Not listed as checks in the archived report | Check explicitly; a zero report cannot imply these passed. |

For an 18 um regular-process revision, use at least 0.0889 mm width/space; the proposed project design target is 0.10 mm for both, where mating geometry permits. Use separate rules for via-to-trace, exposed-pad-to-trace, holes and outline setbacks. For a future 12 um revision, distinguish the 0.0762 mm regular profile from contact geometry relying on the published absolute capability. Do not globally lower clearance to 0.0508 mm just to make the report pass. These are documentation targets, not applied rule edits.

## Optional 12 um copper change

The saved and active baseline is still 18 um. The user has asked about 12 um but has not instructed a design change. Keep the order profile and PCB stack consistent if that changes.

At equal conductor length, width, material and temperature, `R12/R18 = 18/12 = 1.5`. At fixed current, trace voltage drop and resistive heating also increase by 50%. This ratio is not an ampacity rating. Check actual branch currents, allowable voltage error and thermal conditions; the common branch conductor carries the combined output current. No maximum load or cryogenic electrical/thermal qualification is recorded.

The current finger gap would still be below the 12 um regular limit. Its size is above the published absolute line/space limit, but other geometry and manufacturing checks remain outstanding. Recalculate the finished ZIF mating thickness rather than simply changing the nominal copper dropdown.

## Evidence and release procedure

| Design | Saved geometry evidence | Archived native DRC |
| --- | --- | --- |
| Straight | [190 checks](../FPC_15015_0451/saved_geometry_validation.json) | [Report](../FPC_15015_0451/Native_DRC.html) |
| Branch | [532 checks](../FPC_Adapters_20261002/ZIF_to_2xZIF/geometry_validation.json) | [Report](../FPC_Adapters_20261002/ZIF_to_2xZIF/Native_DRC.html) |
| Micro-D | [87 checks](../FPC_Adapters_20261002/ZIF_to_DSUB25/geometry_validation.json) | [Report](../FPC_Adapters_20261002/ZIF_to_DSUB25/Native_DRC.html) |

1. Resolve FPC-01 through FPC-08 and record the selected copper/process in the order document. Keep accepted supplier exceptions scoped to the relevant feature.
2. Apply the agreed rules to the editable source, preserving contact numbering, connector geometry and schematic correspondence. Do not alter read-only references.
3. Save/reopen, run native DRC and schematic checks, then repeat independent copper, drill, mask/paste and outline measurements. Do not reuse old reports for changed artwork.
4. Inspect exported Gerbers and drill files, including mirrored contact faces and backing layers. Record the release hashes and corresponding reports.

No new native DRC, Gerbers, quote, supplier exception or fabrication release was produced by this documentation update.
