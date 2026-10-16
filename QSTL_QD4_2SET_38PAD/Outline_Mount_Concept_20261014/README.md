# PCB extension, mounting and SMP concept

## Current QD28 correction: enter SMP28 from the left

[Corrected QD28 route and close-up](QD28_Left_Entry_Single_SMP_Turn.png) supersedes the forced vertical-entry interpretation below. The descending bus now turns directly at the SMP row and enters horizontally from the left, with one smooth turn at the SMP approach. Its existing QD-side transition remains. The other 15 guide paths and every terminal position/mapping are unchanged.

The limited 0.11 mm geometry check reports no guide crossings or foreign-pad overlap. [Audit](qd28_left_entry_audit.json). No native PCB/CAD changes were made. The prior obstacle was specific to the rejected vertical approach, not a reason to retain the unnecessary SMP-end double turn. Full component/routing validation and copper-carrier incompatibility remain unresolved.

## Latest correction: remove the unnecessary entry doglegs

[Single-turn review](Single_Turn_SMP_Entry_Review.png): QD11/SMP05, QD12/SMP02 and QD30/SMP24 have one tangent turn between a straight departure along the pad axis and the vertical SMP approach. Their prior intermediate doglegs are removed.

QD28's direct alternative is obstructed: its vertical segment on X=16.75 mm passes through SMP24 signal pad 1 at Y=40.10 mm and overlaps QD30. It is shown dashed red and is rejected. QD28 retains the previous safe bypass; the diagram does not claim that all four channels now have one turn. Terminal positions and assignments are unchanged. The retained 16 guides pass the limited crossing/foreign-pad projection check, but R/C placement, actual RF/DC/GND/shields and native DRC remain pending. [Audit](single_turn_smp_entry_audit.json).

## Latest review: vertical SMP entries and copper incompatibility

The user confirmed QD **11/12/28/30**, correcting "20" to "30". The [vertical SMP-entry proposal](Vertical_SMP_Entry_QD11_12_28_30.png) routes QD11/SMP05 from below and QD12/SMP02, QD30/SMP24, QD28/SMP28 from above. Connector/pad positions, mapping and the other 12 guides remain unchanged. The limited guide check finds no crossings or overlap with SMP/foreign QD pads; it is not a component-placement, ground/shield, mask, impedance or native-DRC validation. [Audit](vertical_smp_entry_audit.json).

The current extended outline **does not fit the unchanged copper**. The [actual STEP review](../Mechanical_Review_20261015/Current_Proposal_Copper_Clearance_Review.png) shows 2.06 mm positive-Y overhang beyond Bottom copper, collision with the end lip, and 9.66 mm upper M2 axis mismatch. Lower M2 axes remain aligned. The Top_ForFridge outer envelope has 1.94 mm positive-Y margin but still has internal overlap; gross outer containment is not clearance. The original 0.061 mm right-skirt overlap remains. Do not call this proposal mechanically compatible without a corresponding board/carrier revision. Native design/reference CAD files are unchanged.

## Latest correction: QD centred on the two gap midpoints

Use the [updated QD-centred RF proposal](QD_Centred_in_SMP_Gap_Proposed_RF.png) and [dimensioned midpoint view](QD_Gap_Midpoint_Dimensioned.png).

Both central SMP-free gaps span Y=42.85..49.45 mm. Their midpoints are L=(2.75,46.15) and R=(16.75,46.15) mm. Their connecting line therefore has midpoint (9.75,46.15) mm. Translate the cavity and all 38 bond pads from the old QD centre (9.75,42.50) by (0,+3.65) mm. Preserve pad sizes, angles, relative positions and circuit membership; retain the 4.30 x 5.30 mm cavity.

The 16 RF connection guides are regenerated with zero crossings and preserve pad 15's immediate tangent curve. SMPs, mounting holes and the trial outline retain the preceding proposal's positions. Native files and reference CAD remain hash-verified unchanged. See [source-bound audit](qd_gap_midpoint_audit.json). The R/C placement, actual RF/DC/GND/shields, masks, native DRC and matching carrier/device mount remain future implementation work.

The upper-M2 proposal below supplies the retained SMP/mounting geometry, but its former QD centre is superseded by this correction.

## Current corrected proposal

Use [Raised upper M2 and proposed RF connections](Raised_Upper_M2_Proposed_RF_Connections.png). This is an offline planning picture, not a native design or manufacturing release.

- Keep the lower M2 pair exactly at its original X/Y, Y=13.19 mm. Its earlier extra movement was not requested and is rejected.
- Move the large lower mounting locations downward by a trial 0.75 mm to Y=17.34 mm. Their actual 4.00 mm drills and 5.00 mm lands remain unchanged; M2.5 is the user's location label, not a new drill specification.
- Lower SMP row centres are Y=40.10/34.35/28.60/22.85 mm, X=2.75/16.75 mm, retaining 5.75 mm row pitch.
- Extend the trial PCB to 19.50 x 77.50 mm. Raise upper M2 to Y=75.00 mm and all four upper SMP rows by 5.00 mm relative to the first extension sketch. Moving holes alone would not free central placement area.
- QD pad 15 leaves directly into a tangent arc, with no straight lead-out. The illustrative radius is 1.50 mm. [Pad 15 close-up](QD15_Immediate_Curved_Departure.png).
- Preserve all 16 RF circuit assignments and all 38 DC assignments. RF paths are connection guides that collapse the unplaced capacitor and bias resistor junction into one link; they are not fabrication copper.
- Clarification is pending whether the user's 11/12/28/30 identifies QD pad numbers or R/C designators. The image shows a separate R0603/C1206 size reference; it does not claim the four pairs have been placed or verified.

Nominal 2D checks: SMP box gap 0.250 mm; mounting-land gap 0.269061 mm; SMP-box-to-mount-land gap 0.260001 mm. RF guide intersections: zero. Limited projected 0.11 mm guide-to-SMP/foreign-QD-pad gap: 0.275 mm minimum. These checks do not validate fastener heads, plugs, R/C placement, DC/GND/shields, masks or native DRC. The existing copper carrier requires matching changes before this outline/mounting proposal can be assembled. Native PCB, schematic, library, canonical mapping and reference CAD hashes remain unchanged.

[Current audit](raised_upper_M2_rf_audit.json) | [Lower-hole correction before the extra upper extension](Revised_M2p5_Proposed_RF_Connections.png) | [Retained circuit mapping](Revised_SMP_QD_Mapping.csv)

## Rejected earlier movement sketch — historical only

The following original -2 mm large-hole / -2 mm lower-M2 proposal, its images and its clearance results are superseded. Do not use them as the current plan.

This is an offline picture-only concept responding to the requested outline/mounting/SMP movement. It does not modify any native PCB, schematic, library or reference CAD.

## Trial movements

- PCB width stays 19.50 mm; positive-Y end moves from 67.90 to 72.50 mm.
- Upper M2 centres move from Y=65.34 to 70.00 mm; their X coordinates and 2.10 mm drills stay fixed.
- Top inward SMP pair moves outward to X=2.75/16.75, Y=64.45 mm. This also raises it 1.70 mm so the next side row retains 5.75 mm pitch.
- Three lower side rows move up 1.70 mm to Y=28.00, 33.75 and 39.50 mm. The bottom inward pair moves outward to X=2.75/16.75 at unchanged Y=22.25 mm.
- The two large lower openings, called M2.5 locations by the user, move from Y=18.09 to 16.09 mm. Retain their actual 4.00 mm openings and 5.00 mm lands for this sketch.
- Additional dependent proposal, explicitly purple in the image: move the lower M2 pair down 2.00 mm, Y=13.19 to 11.19 mm, preserving its spacing from the large mounting openings.
- All 16 SMP/QD circuit identities, QD midpoint geometry, board width, lower M1 locations and ZIF geometry are retained. No new RF routing is claimed.

## Geometric limits

Nominal 5.5 mm SMP bounding boxes have 0.250 mm minimum row gap. The space between the side-column body projections is 8.50 mm, not a verified component/routing corridor.

The existing copper end lip begins at Y=68.039999 mm. The proposed PCB extends 4.460001 mm past it. Its recess/end lip and the moved mounting axes therefore need a corresponding copper-carrier revision. Existing unchanged copper parts cannot be described as fitting this proposal.

Nominal hole/land and connector-envelope checks are recorded in concept_geometry.json. They are not fastener-head, mating-plug, tolerance or solid-assembly validation. R0603/C1206 placement, RF/DC routing, shielding and native DRC are not performed.

[Movement comparison](PCB_Extension_Mount_SMP_Movement_Plan.png) | [Large proposed view](Proposed_Side_Columns_Overview.png)
