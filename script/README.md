# PCB working scripts

The latest M1 ZIF-end mounts, native save/reopen audit, Inventor standard-hardware fit review and fresh CAM package are in [pcb_end_mounts_20260925/](pcb_end_mounts_20260925/README.md). The current Gerber ZIP is under `fabrication/JLCPCB_HDI_20260925/`. Native L2/L4 GND pour work is in [dc_ground_pour_20260924/](dc_ground_pour_20260924/README.md). Completed Rev E DWG refresh is in [dwg_gerber_refresh_20260924/](dwg_gerber_refresh_20260924/README.md). Earlier CAM/quote records are historical.

The current 2026-09-23 DC remap is in `dc_even_zif_20260923/`: physical J1 contacts 2..48 even only, with pin 50 and every odd contact NC. `FixZIFPads.pas` records the required `SetState_InNet` update and native connectivity rebuild. Saved-file connectivity, schematic correspondence, DRC, preserved RF/mask geometry and DC previews are verified there. Mutation scripts are one-time records; do not rerun them against a different starting revision.

The complete native Altium CAM package and JLCPCB HDI quote record from 2026-09-22 are generated/validated by `jlcpcb_hdi_quote_20260922/package_cam.py`. `ReopenAudit.pas` reopens the original saved board and runs native DRC without changing the design. Quote evidence is stored in `QSTL_24DC_4MW_PCB/fabrication/JLCPCB_HDI_20260922/`.

Create and run helper code inside this repository's `script/` directory. Write Markdown, code comments and technical annotations in English. Communicate with the user in Korean.

Read [DESIGN_REQUIREMENTS.md](../QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md) and [AGENTS.md](../AGENTS.md) before editing the original `QSTL_24DC_4MW_PCB/` project.

Current lower R/C pair movement to 70% of the previous centreline distance and QD RF-via removal are in `lower_rc_70pct_20260921/`. The preceding removal of unused resistor RF vias is in `remove_resistor_rf_vias_20260921/`. The preceding R/C placement, rectangular-mask and hole-edge shield work is in `rc_mask_clearance_20260921/`. The preceding component-fence/mount work is in `shield_rc_ring_20260921/`; earlier dense fences are in `shield_spacing_20260921/`. The preceding RF50, QD pad/cavity and mask work is in `rf50_hdi_milling_20260920/`. Previous mask work is in `mask_ground_20260920/`; previous RF/DC routing work is in `rf_six_inward_20260920/`. `_support/` contains local parsing, rendering and schematic helpers; older revision names there do not denote a separate final project.

Use `script/.venv/Scripts/python.exe -X utf8` with `requirements.txt`. Native Altium scripts must target the original project and be followed by save/reopen checks. Python validators read saved documents. Current reports must match the saved PCB SHA-256.

Previous mutation scripts such as `ApplyRF6.pas`, `FixRF6.pas`, `AdjustRF6.pas`, `FinalDC.pas` and `FixModels.pas` are one-time change records. They assume a specific starting state and must not be rerun blindly. The preceding via-paste validator is historical: the latest user instruction explicitly removes via-specific paste apertures while retaining normal SMD paste.

Keep reference designs read-only, avoid extra DC transition vias, and preserve the current RF/soldering masks and non-Top QD GND exclusions during later edits.
