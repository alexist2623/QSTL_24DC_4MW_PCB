# QD4 / 2SET 38-pad carrier

The requested copied carrier is applied to the native Altium project, saved and reopened, but the design is **incomplete because earlier routing requirements are not satisfied**. Electrical connectivity and the enabled native DRC checks pass; those results do not establish compliance with the required corner geometry or QD via-in-pad placement. Open [QSTL_QD4_2SET_38PAD.PrjPcb](QSTL_QD4_2SET_38PAD.PrjPcb) from `C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD`.

The original project and its 12 tracked source project/library files retain their recorded SHA256 hashes. This separate project is the copy explicitly requested for the QD4/2SET redesign.

## Saved design

- All 38 QD terminals have independent DC connections. The 16 selected RF terminals additionally use resistor/capacitor bias tees; RF does not replace their DC connections.
- There are 16 SMP connectors, arranged symmetrically as eight above and eight below the sample. The board retains the 19.5 x 67.9 mm outline.
- The wire-bonding pads follow the bonding directions. The Bottom blind pocket is 5.3 x 4.3 mm, R0.5, centred at (9.75, 42.5) mm and 1.2 mm deep. Mechanical 3 documents the non-plated, non-through pocket.
- The saved board contains 50 components, 243 pads, 2,106 signal-track primitives, 76 Top-to-Bottom signal vias and 640 L5-to-Bottom GND shield vias: 716 vias total. Forty-nine source-derived embedded component models are present; the QD bonding area has no invented package model.
- [pin_mapping.csv](pin_mapping.csv) records the current assignments. Odd ZIF contacts are used and pin 50 remains unused. The former even-only adapter mapping is incompatible with this 38-channel design.
- The twelve close R/C pairs now have approximately 0.270 mm body clearance after the 0.100 mm capacitor displacement, exceeding the unchanged 0.254 mm component-clearance rule.

## Unresolved routing requirements

[DESIGN_REQUIREMENTS.md, Routing and layer stack](../QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md#routing-and-layer-stack), line 258, requires each DC turn to be at most 45 degrees and RF corners to use tangent curves.

- The saved DC routing contains 1,440 turns exceeding 45 degrees across 38 DC nets. One confirmed 90-degree example is DC15 on L2 at (2.06000096, 9.54000124) mm, where a vertical segment meets a horizontal segment. These corners require chamfering or rerouting to meet the existing rule.
- The saved RF routing contains 300 sharp corners across 14 MW nets and zero native arc primitives. It does not satisfy the required tangent-curve geometry; the RF corners need correction and renewed clearance, shielding, mask and connectivity checks.
- All 22 direct QD DC fanout vias are outside their pads, approximately 0.90 mm from the pad centres. This does not preserve the QD via-in-pad requirement recorded in [DESIGN_REQUIREMENTS.md](../QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md), lines 245 and 287. The 16 bias-resistor DC-pad-2 vias remain correctly in-pad; single-internal-layer DC routing and the absence of additional standalone DC transition vias are preserved.

The [saved routing-requirement audit](../script/qd38_carrier_20261010/saved_routing_requirement_audit.json) counts degree-two track turns outside same-net pad and via lands, using the saved native coordinates. Pad/via junctions are excluded from these counts.

The current review has not changed routing. These deficiencies remain open despite the zero-violation DRC report. Do not treat this copy as a completed design or a fabrication release.

## Completed electrical and geometry checks

The frozen `.PcbDoc` SHA256 is `f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632`.

- Native save/reopen validation completed. Stored connection count is zero both before DRC and after the post-DRC save.
- Native batch DRC returned True: 21 reported rule instances, zero violations and no early-stop warning. Coverage includes all three via-style rules and the component-clearance rule. Existing manufacturing limits remain active.
- Saved mask/ground checks pass: sixteen R/C rectangles use 0.90 mm margins; the RF protected strip and Bottom ZIF rectangle remain covered; all eight mounting lands are exposed on both faces and directly connected to GND on all six copper layers. The 5.7 x 4.7 mm inner QD rectangle excludes GND on every non-Top layer while retaining Top GND.
- Saved embedded-model hashes, origins, rotations and board sides match the source-derived model definitions.
- Native schematic compilation ran and reported zero violations, but its API Boolean return was False. The log is retained without relabelling that return as a successful compile. Saved pad/net assignments and the returned compiled net list are checked independently against the copied schematic.

The independent saved-copper audit passes, including geometric equivalence after Altium split some track primitives during Analyze/Clean. This audit checks connectivity and copper equivalence, not the unresolved DC/RF corner and QD via-in-pad requirements above.

Native paste-only CAM verification passes: 53 Top apertures and 64 Bottom apertures match the intended SMD pads; no additional via, SMP, mounting or QD paste is present.

## Evidence and review

- [Native save/reopen log](../script/qd38_carrier_20261010/native_validation.txt)
- [Native DRC report](../script/qd38_carrier_20261010/Native_DRC.html)
- [Saved copper and schematic correspondence audit](../script/qd38_carrier_20261010/through_dc_saved_native_audit.json)
- [Saved mask, QD exclusion and direct-GND audit](../script/qd38_carrier_20261010/saved_surface_semantics.json)
- [Saved embedded-model audit](../script/qd38_carrier_20261010/saved_model_validation.json)
- [Native schematic compiler log](../script/qd38_carrier_20261010/native_compile.txt)
- [Paste-only native CAM audit](../script/qd38_carrier_20261010/native_paste_cam_validation.json)
- [Source-file hashes](copy_provenance.json)

The earlier desktop-access and project-open failures are resolved. The working project path is this computer's `C:\GIT_Workspace` directory, and the corrected project-open call is `DM_OpenProject(ProjectPath, True)`. [The successful native probe](../script/qd38_carrier_20261010/probe_native_fixed.txt) and subsequent saved-board validation provide the runtime evidence; no claim is made about an unobserved operating-system cause of the earlier Access denied error.

No production Gerber package has been released and no Git push has been performed for this copied carrier. Diagnostic paste-only output under `script/` is a verification artifact, not a fabrication release. Historical preparation files describe earlier checkpoints; each hash-matched report above establishes only its stated scope. The unresolved routing requirements still prevent completion.
