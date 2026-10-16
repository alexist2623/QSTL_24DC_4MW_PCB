# Sample_Holder PCB size comparison

Read-only review on 2026-10-15. Reference source: `F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/PCB/Sample_Holder/Sample_Holder.PcbDoc`.

| Design state | Width (mm) | Length (mm) |
| --- | ---: | ---: |
| Reference Sample_Holder | 32.60 | 107.10 |
| Saved QSTL 16-RF PCB | 19.50 | 67.90 |
| Latest QSTL 16-RF plan, not applied | 19.50 | 77.50 |

The reference is 13.10 mm wider and 29.60 mm longer than the latest plan, with approximately 2.31 times its outline area. Dimensions are extracted from all saved board-outline vertices. The reference `Sample_Holder.GM` outline within `Sample_Holder_gerbers_new_2025.08.21.zip` independently confirms 32.60 x 107.10 mm; the line aperture is not added to the manufacturing-outline centreline dimensions.

[Equal-scale comparison and centred overlay](Sample_Holder_Size_Comparison.png) | [Source hashes and dimensions](size_comparison.json)

The overlay aligns board centres only; it does not assert mounting-hole, cavity, sample or copper-carrier compatibility. No native PCB or reference files were modified.

## Henning rod width added

[Comparison including rod rails](Sample_Holder_Size_Comparison_With_Rod.png) | [Rod source and measurements](size_comparison_with_rod.json)

The preserved `Mechanical_Assembly/Probe_H_Frame/Probe_H_Frame.step` was read again. The two long rail solids have X bounds 0..6 and 45..51 mm, giving **51 mm outside width**, **39 mm clear inside width**, and **6 mm per rail**. This simplified existing model is based on user-supplied drawing `SO01373.10-Probe-R01.pdf`, A00424 R01, section X2-X2. The actual model length is 360 mm; the comparison shows a cropped rail segment, without crossbars.

For laterally centred board outlines, clearance to each inner rail is 3.20 mm for the 32.60 mm reference and 9.75 mm for either 19.50 mm current-board state. These are width-only clearances, excluding the copper carriers, fasteners, crossbars and tolerances. The source STEP hash is checked before and after rendering; no CAD or PCB source was changed.
