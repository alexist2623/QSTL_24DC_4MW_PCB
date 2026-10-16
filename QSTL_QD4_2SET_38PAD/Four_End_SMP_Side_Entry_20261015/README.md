# Four end SMPs: horizontal entry

SMP34 (QD2) and SMP15 (QD16) now enter from the right; SMP32 (QD35) and SMP13 (QD21) enter from the left. These directions point from the board-centre side toward each signal pad. Only four conceptual guides change. Other twelve sampled paths, all component/pad/mount coordinates and electrical membership are retained.

[Review with before/after details](Four_End_SMP_Side_Entry_Review.png) | [Enlarged plan](RF_Side_Entry_Enlarged.png) | [Audit](side_entry_audit.json)

Each new path retains a tangent cubic QD departure and finishes with a 2.80 mm horizontal approach. All sixteen guides are checked together at 0.11 mm width against foreign pad copper, other SMP envelopes, mounting lands, cavity and board edges. A sampled minimum 1.00 mm bend radius is enforced for the proposed curves. This does not establish electrical or manufacturing superiority over the previous entry.

R/C placement is deferred. No native PCB/CAD changes or RF signal vias are introduced. Final bias tees, DC/GND/fences/masks, impedance, Altium DRC, plugs and fasteners remain unvalidated; existing carrier mounting conflicts remain open.
