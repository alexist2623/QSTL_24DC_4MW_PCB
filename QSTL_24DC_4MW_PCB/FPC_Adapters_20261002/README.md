# FPC adapter designs

Manufacturing documentation (reviewed 2026-10-05): [DRC and manufacturability](../docs/FPC_DRC_AND_MANUFACTURABILITY.md) and [order specification](../docs/FPC_ORDER_SPECIFICATION.md). These documents compare saved rules with supplier limits and list the unresolved order settings. Copper remains 18 um per layer; 12 um has not been selected or applied.

Updated 2026-10-02. Open each `.PrjPcb` to load its PCB and schematic. These are additional designs; the original carrier, straight cable and read-only references are preserved.

| Design | Wiring and geometry | Saved validation |
| --- | --- | --- |
| ZIF_to_2xZIF | All 51 contacts branch C.n = A.n = B.n; output tips separated by **70 mm** | Native reopen and DRC: 0 violations; rebuilt connections: 0; 532 independent checks |
| ZIF_to_DSUB25 | Anton's NorComp Micro-D mapping; 25 signals on even ZIF contacts | Native reopen and DRC: 0 violations; rebuilt connections: 0; 87 independent checks |

Both PCBs were rebuilt through Altium's native API and saved normally. The final saved files were reopened in a fresh Altium process for DRC and connection rebuilding. `Native_DRC.html`, `native_validation.txt`, `geometry_validation.json` and `native_status.json` provide the evidence for each board. The review PNGs show actual saved copper with dimensions; they are not Altium screenshots.

The branch's first native schematic compile reported three missing footprint models. Component-specific local `.PcbLib` files were recovered from actual saved PCB pad/region geometry, and explicit model links plus project membership were added. `footprint_recovery.json` records source hashes and coordinate round-trip checks. Native library reload and schematic recompile remain unverified because Altium window activation times out. Independent saved schematic wire/pin correspondence is verified. Restart Altium and run the prepared read-only `CompileOnly.PrjScr` with both final projects open to finish this check; do not run the obsolete offline PCB writers against these final files. Existing `native_compile.txt` reports predate library recovery and are not final compile passes.

The branch's 420 mm overall length and 10 mm strip-to-strip clear gap remain provisional interpretations of the sketch. The DSUB adapter's 40 mm length, 31 mm base and 1.6 mm finished connector-area backing are design assumptions. The original straight 101.6 mm cable was not shortened; the new branch's A-to-B tip separation is 70 mm.

These files are not released for fabrication. The inherited 0.0707105 mm contact gap, small DSUB PTH annulus, fine branch drilling and finished flex/stiffener stack require supplier acceptance. Native DRC confirms the stored design rules, not universal supplier capability.

Git delivery to the existing repository was requested on 2026-10-03. No supplier upload, fabrication release or order was performed.
