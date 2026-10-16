# Current proposal versus preserved copper parts

Review date: 2026-10-15. Result: **not compatible as drawn**.

The 19.50 x 77.50 x 1.58839662 mm PCB proposal uses QD centre (9.75,46.15) mm and the original lower M2 pair. Actual `Bottom_reference.step` and `Top_ForFridge_reference.step` geometry is transformed into the PCB frame using the preserved rigid transform. Independent cylinder-axis checks match both lower M2 axes to both copper parts within 0.000001 mm.

| Check | Result |
| --- | --- |
| PCB beyond Bottom copper positive-Y outer end | 2.060001 mm |
| Top_ForFridge positive-Y gross outer margin | 1.939999 mm |
| PCB end beyond existing Bottom end-lip start | 9.460001 mm |
| Upper M2 axis mismatch from existing copper | 9.660001 mm |
| Inherited right-skirt overlap | 0.061109 mm |
| Proposed board solid / Bottom copper overlap | 120.982357 mm3 |
| Proposed board solid / Top_ForFridge overlap | 61.514059 mm3 |

The PCB solid includes its current mounting holes and moved 4.30 x 5.30 mm blind pocket, 1.20 mm deep. The overlap audit separately includes old/new rectangular envelope results to distinguish inherited overlaps from extension effects. The rendered copper is translucent; red solids are computed intersections. The projected upper-end drawing uses actual STEP edges, not a guessed bounding rectangle.

SMP drill/opening mismatches are intentionally excluded, following the prior user instruction. R/C bodies, screw heads, connector plugs, cable and rod are not evaluated. Source PCB, schematic and both copper references are hash-verified unchanged. Neither this report nor the separate RF connection diagram implements a native PCB or carrier revision.

[Review picture](Current_Proposal_Copper_Clearance_Review.png) | [Numerical/source audit](current_proposal_copper_audit.json)
