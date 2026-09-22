# Native split-mount drawing workflow

Run PowerShell helpers under Windows PowerShell with Inventor 2027 running. Use the repository `script/.venv` for Python. The saved Rev B CAD and DWG files are the deliverables. Ignored `tmp/` inspection outputs and pre-edit backups are not part of the delivery.

- `generate_content_center_fasteners.ps1`: generate actual supplied DIN 7991 M3x10 and ISO 4762 M3x8 members, retaining Content Center identity and source hashes.
- `replace_content_center_fasteners.ps1`: update current assembly occurrences and countersink fit; no washers are installed.
- `add_device_relief_grooves.ps1`: one-time native feature creation with a duplicate-feature guard. Do not rerun against the already relieved plate.
- `build_native_dwg.ps1`: rebuild five sheets, six native DWGs and the PDF from saved model geometry and the existing native IPN.
- `verify_native_dwg.ps1` / `verify_standard_hardware.ps1`: reopen validation, native dimensions, standard hardware and thread metadata.
- `package_dwg.py`: verify delivery hashes and produce the Rev B ZIP.
- `inspect_device_reliefs.py` / `verify_device_reliefs.py`: measurement and independent relief checks. The latter uses ignored pre-edit STEP backups from the original session.
- `../probe_rod_inspection/verify_dropped_adapter.py`: saved assembly geometry, placement and interference audit; unresolved device-slot intersections are explicitly reported.

Other helpers retain reference-inspection and prototype history. Older prototype and presentation preparation builders use the superseded illustrative screw and must not overwrite the delivery. Use the current Content Center replacement and native drawing workflow for updates.
