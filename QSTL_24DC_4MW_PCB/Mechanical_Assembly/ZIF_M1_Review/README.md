# ZIF M1 round-head mounting review

Current revision, 2026-09-25. `ZIF_M1_Fit.iam` and its matching STEP use two unmodified Autodesk Inventor Content Center **KS B 1021 - Metric M1 x 4** slotted pan/round-head screws. Thread is **M1 x 0.25 - 6g**, head diameter **2.00 mm**, head height **0.65 mm**. No washers or custom screw geometry. `m1_round_member.json` records the installed library member and original file hash.

## PCB geometry

MH7/MH8 use **1.20 mm plated clearance drills**, **1.60 mm lands**, at **(1.05,1.20)** and **(18.45,1.20) mm**. Center pitch is **17.40 mm**. Each hole moved 0.55 mm outward from the superseded M1.6 arrangement. The board remains 19.5 x 67.9 mm. Drill-to-outline margins are 0.45 mm at the sides and 0.60 mm at the end. Mounts join GND directly, with no thermal relief or paste. Original six mounts, routing, masks and components are preserved.

## Cable and native fit

The centered 15.60 mm cable spans X1.95..17.55 mm. Inward hole edges are X1.65 and X17.85 mm: **0.30 mm positive lateral clearance per side**, and 16.20 mm clear width between holes. `ZIF_Cable_Hole_Clearance.png`/`.svg` expose the drilled holes and dimension these gaps. `ZIF_Holes_Cable_Native_Top.png` shows the native Inventor geometry with screws temporarily hidden and the cable transparent. `ZIF_M1_Round_Oblique.png` shows the actual assembled standard hardware.

Saved/reopened Inventor reports **0.627624 mm minimum screw-to-ZIF-housing distance** on each side, no screw/PCB intersection and no housing intersection. Nominal 0.10 mm radial hole/shank play alone does not consume this gap. The only intersections are the allowed screw-head/cable-envelope contact (approximately 0.00140 and 0.00142 mm3). Head-to-cable lateral overlap is nominally 0.10 mm in top projection; screw shanks remain outside the cable envelope.

The cable model uses a 0.20 mm reinforced thickness, from the [Molex 502598-5193 sales drawing](https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf). Its center height of 0.47 mm above the PCB remains an unverified placement assumption. Cable bending/clamping and a full dimensional tolerance stack are not modeled. Screw length 4 mm is a review assumption; mating threaded support/nut is not specified. The 0.30 mm top-projection hole gap does not depend on the assumed cable height.

## Saved-design and fabrication checks

Altium save/reopen: zero unrouted connections and zero violations across 16 checked DRC rules. Independent saved-copper analysis: all 37 nets connected. Original routing, pin mapping, 480 L5-L6 blind microvias, DC ground clearance, masks, QD ground exclusions and original six mounts are preserved.

Updated Gerbers are in `../../fabrication/JLCPCB_HDI_20260925/QSTL_24DC_6RF_HDI_Gerber_20260925.zip`. The package has 96 plated through holes, including the two 1.20 mm mounts, and 480 separate L5-L6 laser holes. `final_pcb_fit_validation.json` links the saved PCB, standard-member hash, native fit and CAM validation. The neighboring M1.6/M2 review folders are superseded historical reviews. No new supplier upload, order or Git push was made.
