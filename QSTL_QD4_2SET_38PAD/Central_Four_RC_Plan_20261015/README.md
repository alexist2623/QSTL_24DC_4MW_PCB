# Central four R/C placement proposal

Date: 2026-10-15. Status: picture-only proposal; native implementation remains paused.

The user clarified that the central channels are **SMP02, SMP05, SMP21 and SMP24**, not QD pad numbers 2, 5, 21 and 24. Existing circuit membership is retained:

| Channel | Components | QD pad |
| --- | --- | --- |
| SMP05 | R05 / C05 | 11 |
| SMP21 | R21 / C21 | 31 |
| SMP02 | R02 / C02 | 12 |
| SMP24 | R24 / C24 | 30 |

The drawing places these four pairs in mirrored L arrangements, using horizontal 0603 imperial resistors and vertical Yageo CC1206JKNPO9BN104 1206 capacitors. Upper pairs sit above the QD pad field and lower pairs below it. The component centres are trial placement coordinates, not user-specified dimensions. Current SMP, QD and mounting coordinates are retained as the background basis.

- [Placement plan and coordinate table](Central_02_05_21_24_RC_Placement.png)
- [Enlarged placement](Central_RC_Enlarged.png)
- [Placement coordinates](placement.csv)
- [Geometry and preservation audit](central_rc_placement_audit.json)

Capacitor pads use 1.00 x 1.80 mm lands at 3.00 mm pitch, giving a 4.00 x 1.80 mm copper envelope. The maximum capacitor body is 3.50 x 1.80 mm. Existing resistor lands are 1.10 x 1.00 mm at 1.70 mm pitch; the body projection uses nominal 1.60 x 0.80 mm. Checks use the union of body and pad projections. Minimum R/C-to-R/C envelope gap is 0.500 mm, R/C-to-SMP 5.50 mm body-box gap is 0.500 mm, and R/C-to-QD-pad gap is 0.244329 mm. There are no checked component overlaps.

Only the short local capacitor-pad-2 to resistor-pad-1 junctions are drawn. Full SMP-to-capacitor and resistor-to-QD routing, the other twelve R/C pairs, DC routing, shields, masks, manufacturing clearance and native DRC are not solved or certified by this placement. In particular, this is not a claim that the earlier RF guide shape can be retained unchanged through these new component locations. The M2.5 mounting conflicts remain unresolved. Native PCB, schematic, QD library, mapping and both preserved copper STEP references are hash-verified unchanged.
