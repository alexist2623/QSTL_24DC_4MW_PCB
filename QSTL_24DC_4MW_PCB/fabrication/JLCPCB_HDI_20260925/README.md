# Current PCB CAM export — 2026-09-25, M1 revision

`QSTL_24DC_6RF_HDI_Gerber_20260925.zip` contains the current native Altium Gerbers and separate through/blind drills. M1 mounts use 1.20 mm plated drills and 1.60 mm lands at (1.05,1.20) and (18.45,1.20) mm, pitch 17.40 mm, direct GND with no thermal relief or paste. Board size stays 19.5 x 67.9 mm.

Saved/reopened DRC: 16 checked rules, zero violations; zero unrouted connections. Independent saved-copper graph: all 37 nets connected. CAM has 96 through holes, including two 1.20 mm mounts, and 480 blind laser holes restricted to L5-L6. Bottom non-through milling remains 4.3 x 4.3 mm, R0.5, depth 1.2 mm; DC ground clearance remains 0.20 mm.

The native Inventor review uses real KS B 1021 M1 x 4 slotted pan/round-head screws. Nominal housing clearance is 0.627624 mm; cable-to-hole clearance is 0.30 mm per side in top projection. Only the permitted head/cable-envelope contact remains. Cable height and deformation are assumptions; see `../../Mechanical_Assembly/ZIF_M1_Review/README.md`. The previous M1.6 ZIP is archived in `script/pcb_end_mounts_20260925/superseded_m1p6_cam/`. No new supplier upload or order was made.
