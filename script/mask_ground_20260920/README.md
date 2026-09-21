# Mask, paste and QD ground update

This phase edits the original project only. All helper code and audit outputs stay under the repository. Read `../../AGENTS.md` and the project design requirements before any replay.

- `prepare_change.py` and `ApplyMaskGround.pas` prepare/apply the two general solder openings, removal of the 144 explicit via paste regions, and five QD copper-pour cutouts. The source-hash and existing-object guards prevent replay on an already modified board.
- `DisablePaste.pas` is the required follow-up: it explicitly disables both paste faces of all SMP/mounting pads and clears interim expansion values. `GetState_IsTopPasteEnabled` and `GetState_IsBottomPasteEnabled` persist for pads.
- The generic via `PasteMaskEnabled` property does not persist as a disabled flag in this Altium version. Vias have no native pad-style paste aperture; the former explicit paste regions are removed. Normal SMD pad paste coincident with via-in-pad remains intentionally present.
- `ProbePaste.pas`, `ProbeRegion.pas` and `ProbeMaskPresence.pas` are API research probes, not production steps. The last probe cannot call `HasMaskExpansion` through the scripting layer and is not validation evidence.
- `ReopenAudit.pas` saves no new geometry; it closes/reopens the saved board, counts connection lines and runs all 13 enabled DRC rules. `AuditPaste.pas` reads native pad paste/solder properties after reopening.
- `verify_mask_ground.py` compares the saved board with `before.PcbDoc`, checking masks, pad paste, RF clearance, GND exclusion, preserved design files and connectivity. A four-native-unit coordinate tolerance handles contour quantization at the QD boundary.
- `verify_design.py` reruns the complete prior routing/schematic audit with the new paste requirement and current DRC report. It does not weaken routing or schematic checks.
- `publish_reports.py` renders the native mask/stencil review and updates the current-state documentation.

Final saved-board SHA-256: `bd8c71fd36253a7f13eab69a7828f3587760a34894e2eb19c72f3818caaff793`.
