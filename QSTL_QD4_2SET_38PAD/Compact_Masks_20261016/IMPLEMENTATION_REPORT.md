# Compact solder-mask correction

Saved PCB SHA256: `0abc5c7a8258df4c239ed4535fba5e120190757f4976b8fbe72d4fae5b1eaad0`.

The oversized axis-aligned C/R pair rectangles were removed. Each Bottom C/R footprint now uses its own rotated two-pad convex hull with a **0.20 mm** mask margin. The opposite face uses local circular covers extending **0.15 mm beyond each via land**, instead of duplicated C/R rectangles. All 22 Top QD vias are locally covered; the central metal remains exposed. The user-approved RF protection strips, SMP solder-control masks, ZIF protection and normal pad apertures remain. Six mounting lands and the Bottom QD bonding field remain mask-free.

General retained-mask area decreases from 989.559 to 372.932 mm2 on Top (**62.3%**) and from 1112.785 to 908.262 mm2 on Bottom (**18.4%**), before subtracting normal component-pad apertures. Four genuine native 0.10 mm mask-sliver violations were corrected by trimming only the nearby general openings. Six local boundaries, including two already above 0.10 mm, now target 0.12 mm separation; the total added mask for this repair is only 0.007531 mm2. Rules were not weakened.

All sixteen exact Yageo CC1206JKNPO9BN104 models align with their pad centres and axes. All 32 C/R native body outlines match their expected envelopes to within 0.000004020 mm. Components were not relocated. The maximum capacitor body remains 3.50 x 1.80 x 1.80 mm; all R/C pads and embedded models are byte-for-byte preserved.

## Validation

- Saved/reopened Altium DRC: **0 violations**, 44 unchanged rules.
- All 71 named nets connected; stored connections 0; exact compiled schematic membership and zero enumerated compiler violations.
- Every RF/DC route, pad, via, component/model, nonmask region, outline, schematic and pin map preserved. The native stream and geometric scope checks pass.
- All 32 persistent L5-only C/R hull cutouts remain free of GND copper.
- Fresh native Top/Bottom solder-mask CAM matches the expected openings and normal pad apertures. All 22 Top QD via lands remain fully covered.
- Fresh paste CAM contains exactly 53 Top and 64 Bottom normal SMD apertures, with no extra via, SMP, mounting or QD paste.
- 211 compact-mask/preservation checks pass. RF protection and all component/terminal mask features pass.

## Review images

- [Before and after](Mask_Before_After.png)
- [Both corrected faces](Corrected_Masks_Both_Faces.png)
- [Capacitor pad/model registration](Capacitor_Pad_Registration.png)
- [Native mask output and unchanged L5 cutouts](Solder_Mask_and_L5_Openings.png)
- [Native DRC](../../script/compact_masks_20261016/Native_DRC.html)

Images are renders of saved native geometry and actual native CAM, not GUI screenshots. Both faces use the same XY orientation for comparison. The previous geometry is backed up under `script/compact_masks_20261016/baseline/`. Mask/paste export is for validation only; no production release, order/cart action or Git push is part of this revision.
