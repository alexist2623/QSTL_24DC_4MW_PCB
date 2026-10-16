# RF-first topology on the straight SMP pairs

The user deferred R/C placement and requested RF first. All sixteen SMP centres, QD pad geometry, mounting axes, board outline and circuit assignments are retained from the paired-straight proposal. Existing R/C designators remain associated with their circuits, but the four old trial pairs are omitted in this RF-first picture.

Each guide is one cubic Bezier leaving the QD pad tangentially, followed by a 2.80 mm cardinal straight approach into its SMP signal pad. QD15 curves immediately from its outer end. No RF signal via or layer change is introduced. The dashed pair-alignment guides from the earlier picture are omitted.

[Overview and mapping](Paired_SMP_Proposed_RF_Connections.png) | [Enlarged routing picture](Paired_SMP_RF_Enlarged.png) | [Audit](rf_first_audit.json)

Sampled 0.11 mm guide geometry is checked against other guides, all foreign QD/SMP pads, other SMP body envelopes, mounting lands, cavity and board edges. This is not completed electrical copper: series capacitors and resistor DC-bias junctions will be placed in a subsequent stage. DC, GND fences/reference geometry, masks, impedance and Altium DRC are not verified by this illustration. Native and reference files remain unchanged, and known carrier mounting conflicts remain open.
