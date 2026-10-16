# Rounded SMP placement proposal

On the retained 32.60 x 77.50 mm proposal, move the sixteen SMP connectors onto two symmetric elliptical side arcs. Keep every existing SMP Y coordinate, QD/ZIF/mount position, circuit assignment and the four trial central R/C pairs. The ellipse is a planning choice, not a required manufacturing dimension.

Retain an 8.50 mm longitudinal strip without SMP bodies and a 6.60 mm SMP-free lateral band around the QD. The previously fixed corner SMPs also retain X; the middle connectors move outward.

[Comparison](Rounded_SMP_Comparison.png) | [Full plan](Rounded_SMP_Plan.png) | [Coordinates](SMP_placement_plan.csv) | [Audit](rounded_smp_audit.json)

The audit checks nominal 5.50 mm square body envelopes against one another, board edges, existing mount lands, QD pads, ZIF pads and the eight shown R/C bodies/pads. It does not validate actual plugs or screw heads. Old RF guides are invalid after endpoint movement and are not reused or shown; no final RF/DC routing or DRC is claimed. The other twelve R/C pairs remain outside this placement study.

Native PCB/schematic/library/mapping and reference CAD hashes are unchanged. The known copper-carrier mounting conflicts remain unresolved.
