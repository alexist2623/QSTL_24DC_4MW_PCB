# Remove unused resistor RF-side vias

Saved original PCB SHA-256: `b173b9c072e841f28fbcb25979e917d688061a3a3b2fa08889f660b3afcafd10`.

Removed exactly six 0.50 mm land / 0.25 mm drill through vias, one at RF pad 1 of each R1-R6 (MW1-MW6). The RF path remains on Bottom and passes through the resistor pad centre. Each resistor retains its DC pad 2 via. QD and ZIF vias remain.

Saved counts: 54 signal through vias, 470 L5-L6 GND shield microvias, 524 total vias. All 37 nets are physically connected, with zero stored connection lines and zero violations across 15 enabled native Altium DRC checks after save/reopen.

`before.PcbDoc` is the recovery copy. `prepare.py` and `RemoveRFVias.pas` are one-time scripts guarded against the exact starting revision and six via targets. Only the six vias were removed and GND polygons repoured. Saved component/pad/track/arc/text/fill/net streams and the schematic/library hashes are checked against the baseline. The masks, QD ground exclusions and remaining via locations/spans are validated independently. The requirement is recorded in AGENTS.md and DESIGN_REQUIREMENTS.md to prevent reintroduction.

`audit_connectivity.py`, `verify_final.py`, `verify_refinements.py`, `ReopenAudit.pas` and `AuditPaste.pas` contain validation. `publish_outputs.py` and `finalize.py` refresh previews, documentation and fabrication companion revision hashes. No Git push or supplier submission was performed in this revision.
