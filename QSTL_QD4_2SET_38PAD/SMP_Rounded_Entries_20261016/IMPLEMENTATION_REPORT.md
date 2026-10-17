# Broad circular SMP approaches

Implemented in the existing `QSTL_QD4_2SET_38PAD.PrjPcb` project on 2026-10-16. Saved PCB SHA256: `cc4b516bb2a595396ce22cec023afa5312c15f7b7ff8f72017cb110756e87819`.

## Applied and retained entries

Thirteen additional capacitor-to-SMP paths were revised. SMP34, SMP32, SMP35, SMP31, SMP05, SMP21, SMP12, SMP16 and SMP15 now use a single native circular arc of **R 1.600 mm**. SMP09, SMP30, SMP11 and SMP28 use two tangent native arcs of **R 1.400 mm**, with a straight connection between the arcs. These four need an S bend because the capacitor launch direction and the retained radial SMP approach do not permit the same one-arc geometry. All line/arc joins are tangent; launches are normal to the capacitor pad and SMP signal boundary. The accepted C13 R1.600 mm quarter-circle is retained exactly.

**SMP02 and SMP24 are unchanged**, including their RF routes and local shielding. Trial broader turns approached mounting lands A4 and A3 closely enough to interrupt their outer shield rows. The trials were rejected before native application. The original two entries remain in the saved design under the user's instruction to retain and report uncertain entries. This is a limitation of the checked candidates, not proof that no different future geometry could fit.

The modified entries remain mirror-symmetric about X=9.75 mm. Their terminal positions, R/C/SMP/QD footprints and electrical mappings did not move. Straight radial SMP approaches range from 1.600 to 3.400 mm depending on the broad curve; the two-sided fence continuity, rather than an arbitrary fixed straight length, was verified explicitly.

## Shielding, preserved routing and surfaces

RF width is 0.110 mm. The final board contains **1,514 GND shield microvias**, land/hole 0.250/0.100 mm, exclusively between L5 and L6. Both rows connect to every SMP ring with maximum centre-to-centre step **0.420 mm** in the measured 3.6 mm approach zone. No RF signal vias were added.

Candidate minima are RF copper to shield-hole edge 0.331217 mm, shield land to shield land 0.152204 mm, component pad to shield land 0.201498 mm, and DC terminal-via land to shield land 0.203373 mm. Full L5/L6 land coverage is checked. Saved route/shield identity and native DRC independently verify the applied geometry.

QD-side RF and all centralized L2/L3 DC routes are preserved. All 76 terminal DC vias, 241 pads, 50 components, 49 embedded model geometries/transforms, schematic membership, pin map, board/mounting/cavity geometry, L1-L4 ground and Top mask are retained. L5/L6 ground and Bottom mask were regenerated locally around the revised RF paths. Protected C13/SMP02/SMP24 RF and fence geometry matches the previous saved revision. The maximum saved difference among preserved routes is 0.000000000 mm.

The earlier close QD-pair correction remains: MW13/MW15 gap 1.095581 mm and MW30/MW28 gap 0.780813 mm in their review windows, with the authorized short shared-fence QD exception. This revision does not change that exception.

## Saved native validation

- The omitted L5 C/R openings were restored after the user's reminder. All 32 individual two-pad convex hulls, including their inter-pad bridges, are now free of L5 GND copper. Persistent native L5-only cutout objects retain these exclusions during a future repour. No intentional margin was added beyond outward native-grid rounding. Approximately 149.803126 mm2 of L5 copper was removed, with all shield lands still covered. The separate L5 correction preserved every RF/DC route and all other layer regions exactly.
- Actual native Top/Bottom solder-mask CAM matches the saved general openings plus normal component-pad apertures, within 0.0003 mm CAM tolerance. The 91 feature checks cover all RF protection strips, SMP and 0.90 mm R/C control masks, the ZIF mask rectangles, and all 22 Top QD via covers. The central Top metal rectangle and Bottom QD bonding field remain exposed.
- 71 named nets connected in the independently reconstructed saved copper graph.
- Stored connection count 0 after native rebuild and save/reopen.
- Enabled native DRC violations 0; all 44 rules retained.
- Exact compiled schematic pin membership, zero enumerated compiler violations.
- Fresh native paste CAM: 53 Top and 64 Bottom normal SMD apertures, no extra via/SMP/mounting/QD paste.
- QD exclusions, solder-mask protection/openings and all embedded model transforms checked.

The native net rebuild resolves stale connection-cache entries; no connection objects or genuine DRC failures are suppressed. The native compiler Boolean return remains historically unreliable, so its enumerated membership and violation list are checked. These are geometry/connectivity checks, not EM simulation or new impedance/manufacturing approval. L5 reference removal beneath the component footprints is intentional; its local impedance effect has not been field-solver validated. No new production Gerber, cart update or Git push is included. The local mask/paste exports are verification-only files.

## Images

- [Whole RF board](Saved_RF_Whole_Board.png)
- [Actual mask output and all 32 L5 openings](Solder_Mask_and_L5_Openings.png)
- [Whole RF and DC layers](Saved_RF_DC_Layers.png)
- [All sixteen capacitor-to-SMP paths](Saved_All_SMP_Entries.png)
- [Unchanged SMP02/SMP24 and rejected broad-turn overlays](Unchanged_SMP02_SMP24.png)
- [Evidence manifest](final_status.json)
- [Native DRC](../../script/smp_broad_rounding_20261016/Native_DRC.html)

Scripts, the preceding native backup, candidate geometry and audits are in `script/smp_broad_rounding_20261016/`.
