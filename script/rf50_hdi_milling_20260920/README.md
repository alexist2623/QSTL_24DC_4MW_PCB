# RF50, QD cavity and shield-via revision

Completed and verified against the saved original PCB. SHA-256: `5d8bfeaebc0bdc2be4a6a13aa78f0bf1a0d7c5f48fc40d0f0ef8d9b645276ae4`.

- Cavity: 4.3 x 4.3 mm, Bottom entry, 1.2 mm depth, R0.5, non-plated.
- QD pad-end opening: 4.7 mm after a 0.2 mm outward shift; original pad dimensions/pitch preserved. Original QD library installed and verified.
- RF: 0.11 mm width, 0.2 mm CPW gap, matching 1078 stack thicknesses. 50 ohms is a fabrication target, not a measured result.
- Capacitor pad through-vias removed: 12. Retained through-vias: 60.
- GND shields: 78 L5-L6 blind vias (54 RF fence + 24 SMP ring), 0.1 mm hole / 0.25 mm land. No DC-layer penetration, thermal relief or paste.
- QD Bottom mask opening and non-Top GND exclusion updated. Shield mask overrides and R3/R4 mask margins pass native checks.
- Saved-board connectivity: all 37 nets connected, zero stored connections. Reopened Altium DRC: 15 enabled checks, zero violations.

## Read-only verification

`audit_connectivity.py` builds a layer-aware graph from saved native copper. `verify_final.py` checks saved pads, routes, stack, via spans, ground exclusions, mask, paste, library correspondence and native DRC. `ReopenAudit.pas` closes/reopens the original board and runs native DRC; `AuditPaste.pas` reads native paste flags. Re-run these only after relevant edits, not merely to repeat a passing test.

`publish_outputs.py` renders saved copper and publishes the fabrication companion directory under the original project. `fabrication_notes.py` creates the cavity Gerber/drawing and notes. `update_documentation.py` records this revision. Published reports and the fabrication manifest carry source hashes.

## Mutation history

`ApplyRF50.pas`, `FinishRF50.pas`, `CompleteRF50.pas` and library-install helpers are one-time change records. Do not rerun them against the completed board. The original interrupted script used unsupported FabText.X/Y properties; the completed continuation uses MoveToXY. The final mask repair is recorded in `RepairMask.pas`. `before.PcbDoc` and `before.PcbLib` preserve the starting state.

See the repository README and project DESIGN_REQUIREMENTS.md for current constraints. The fabrication companion package is not a complete production CAM release. Fabricator acceptance of the combined cavity/HDI process and actual controlled impedance is still required before production.

## Desktop display observation

The original project/PCB is open in Altium. The automation screenshot showed a blank PCB canvas even after a graceful application restart and selecting L6; this display/capture issue was not resolved. No unsaved document changes remained, and the final on-disk PCB hash is unchanged. Saved-native previews and all connectivity/DRC reports above are verified, but they must not be described as successful visual verification of Altium's live canvas.
