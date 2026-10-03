# Adapter helpers and current state

The final designs are under `QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/`.

## Safe verification

- `validate_branch.py` and `validate_dsub.py` read the final saved designs, verify copper/contacts/masks and regenerate dimensional PNGs and geometry reports.
- `CompileOnly.PrjScr` is a read-only native schematic compile/export helper. After restarting Altium, open both final `.PrjPcb` files (including their local footprint libraries), then run `CompileOnly.pas > CompileOnly`. Inspect every violation and compare its recovered pin map with `schematic_correspondence.json` before marking compile as passed.
- `ColdAudit.PrjScr` opens saved final boards, rebuilds connectivity and runs native DRC. It is unnecessary unless the saved boards change. It does not save an altered PCB.
- `recover_footprint_libraries.py` recovers component-specific pad/region geometry, adds explicit schematic model links and project membership. It preserves PCB bytes and stores original schematic/project backups in `before_library_recovery/`. Native library loading remains to be checked.
- `publish_validation_status.py` currently publishes the verified PCB evidence and the pending native library/compile limitation. Update its status logic when native compilation actually passes; do not claim a pass from this documentation writer.

## Obsolete or single-use scripts

Do not run offline PCB writers, `BuildNativeBoth`, `NativeFinish`, `FinalAudit` or `FixViaFlags` against populated final documents. The native PCB rebuild and mask repair have already been applied. `NativeFinish` would add duplicate coverlay regions if repeated. `FinalAudit` performs saves and is superseded by the separate read-only audits. `FixViaFlags` arose from an incorrect interpretation of generic inherited via cache flags; saved native mask overrides already close the via openings. Its attempted unsaved changes must not be promoted to final files.

`native_work/` and `before_native_validation/` contain historical build inputs/results, not final deliverables. The final review PNGs are rendered from actual saved copper, not captured from Altium.

The current Altium sessions did not respond to window activation. The first branch compile reported missing models; libraries were then supplied on disk. Pending work is native reload/compile and verification of those explicit library links. Git delivery was requested on 2026-10-03; the pending native validation remains documented and no fabrication release has been performed.
