# Native sixteen-RF carrier implementation

The accepted 16-RF / 38-DC proposal and subsequent DC centralization are implemented in the existing `QSTL_QD4_2SET_38PAD.PrjPcb` PCB and schematic. The final saved PCB SHA256 is `0adecc99d347b092775e4fe84506e643e7af0a8ce49d43413f4dc0239a6f58de`.

## Final geometry

- Board: 32.600 x 99.025 mm. QD centre: (9.75, 46.15) mm; 90-degree rotation; aligned bond-pad end midpoints.
- Accepted paired SMP placement, reference P/A mounting axes, relocated ZIF, sixteen 0603 resistors and sixteen Yageo CC1206JKNPO9BN104 1206 capacitors are applied.
- Bottom blind pocket: 4.3 x 5.3 mm, R0.5 mm, 1.2 mm deep. The fabrication annotation remains separate from the board outline; it is not a through cutout.
- Physical roles: L1 GND and short ZIF fanout; L2 DC-A; L3 DC-B; L4 GND; L5 GND; L6 RF/QD.
- RF: 0.11 mm width, tangent arcs and no signal vias. The 1,439 solid shield microvias span L5-L6 only, including the accepted shared QD fences and unfenced immediate bond-pad launches.

## Final DC correction

The long DC runs now gather around X=9.75 mm. At Y=2, 10 and 20 mm, each internal layer has nineteen lanes from X=7.41000042 to 12.09000122 mm. Their copper envelope is 4.8050008 mm wide and centred at X=9.75000082 mm. Routing fans out around the fixed QD/pocket and resistor terminals and at the relocated ZIF.

All 38 DC lines retain 0.125 mm width and one internal layer per net. There are exactly 76 terminal vias: 22 direct QD terminals, 16 resistor DC pads and 38 ZIF terminals. No standalone DC transition vias were introduced. RF, fixed via geometry, component/pad geometry, solder masks, outline and unaffected ground layers are preserved during this correction; L2/L3 ground and antipads were regenerated.

Twenty-six ZIF contact assignments changed to avoid crossings. The existing 24 even contacts 2–48 and fourteen odd contacts 1–27 remain the contact pool; pin 50 is unused. The saved schematic labels, compiled net membership and `pin_mapping.csv` agree. Each chip terminal still receives DC, and the sixteen RF terminals retain their C/R bias tees.

## Saved native verification

After native save, close, reopen, DRC, save and reopen:

| Check | Result |
|---|---:|
| Connected named nets | 71 / 71 |
| Stored connections / unrouted lines | 0 |
| Native DRC violations | 0 |
| Enumerated schematic compile violations | 0 |
| Native DC layers | 19 nets on L2; 19 on L3 |
| RF signal vias | 0 |
| DC trace-to-trace minimum | 0.134998 mm |
| DC trace-to-foreign-via-land minimum | 0.105193 mm |
| DC trace-to-foreign-drill-edge minimum | 0.205193 mm |
| DC-to-GND minimum | 0.202839 mm |
| DC-to-resistor body/inter-pad envelope minimum | 0.157562 mm |
| DC-to-complete-SMP-pad-hull minimum | 2.198751 mm |
| DC-to-blind-pocket minimum | 0.167309 mm |
| RF copper-to-shield-hole edge minimum | 0.331218 mm |

Native compiled named-net membership exactly matches the PCB and schematic, with fifteen unused single-contact ZIF nets. The compile API Boolean is False despite zero enumerated violations; acceptance uses the enumerated net membership and violations, not that Boolean alone.

QD non-Top ground exclusions, retained Top metal, Bottom bond-field mask opening, Top protected-via frame/exposed centre, mounting-mask openings and full shield-land coverage pass saved-geometry checks. Fresh native paste CAM contains exactly 53 Top and 64 Bottom normal SMD apertures; no additional via, QD, SMP or mounting paste appears. All 49 embedded component models pass geometry-hash, side, height and transform checks. RF centreline comparison uses a 0.00010 mm arc tessellation bound; maximum measured plan/native difference is 0.000101441 mm.

## Evidence and files

- [Saved RF/L2/L3 image](Saved_RF_DC_Layers.png): rendered from the saved native file, not a conceptual route substitute or an Altium screenshot.
- [PCB](../QSTL_QD4_2SET_38PAD.PcbDoc), [schematic](../QSTL_QD4_2SET_38PAD.SchDoc), [project](../QSTL_QD4_2SET_38PAD.PrjPcb), [pin map](../pin_mapping.csv).
- [Central DC measurements](../../script/native_16rf_apply_20261016/central_saved_audit.json), [saved copper/connectivity audit](../../script/native_16rf_apply_20261016/saved_native_audit.json), [route identity](../../script/native_16rf_apply_20261016/route_identity_audit.json), [models/masks/paste/compile](../../script/native_16rf_apply_20261016/support_audit.json), [native DRC](../../script/native_16rf_apply_20261016/Native_DRC.html).

The original native files and the intermediate state preceding centralization are backed up under `script/native_16rf_apply_20261016/backup` and `before_dc_centralization`. All helper code is repository-local under `script/`. The separate original 24-pad project and external reference designs were not edited in this implementation.

This is a native design implementation and verification result. It does not resolve manufacturer acceptance of the requested 1078 stack/inner copper, certify measured 50-ohm impedance, or clear the inherited SMP component-PTH annular-ring manufacturing review. No production Gerber package, shopping-cart update or Git push was requested or performed in this turn. Paste CAM is an internal verification output.
