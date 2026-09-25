# ZIF M1.6 round-head mounting review

Latest correction, 2026-09-25: the current `ZIF_M1p6_Fit.iam` and matching STEP use two unmodified Autodesk Inventor Content Center **ISO 7045 H M1.6 x 4** cross-recessed pan/round-head screws. Thread is M1.6 x 0.35 - 6g; supplied head diameter 3.2 mm and height 1.3 mm. No washers or custom screw geometry. Prior ISO 4762 conclusions and source assembly are archived under `script/pcb_end_mounts_20260925/superseded_socket_head/`.

The PCB remains unchanged: 1.8 mm plated drills at (1.60,1.20) and (17.90,1.20) mm, pitch 16.30 mm; lands 2.20 mm, direct GND, no thermal relief or paste. Current Gerbers remain valid representations of this unchanged PCB geometry.

## Cable-to-hole dimensions

The centered 51-contact cable envelope is 15.60 mm wide (X1.95 to X17.55 mm). The space between the inward hole edges is 14.50 mm. Signed lateral clearance is therefore **-0.55 mm per side**, i.e. the cable and drilled holes overlap by 0.55 mm on each side in top projection. This is not a positive clearance. The cable is above the PCB, so a top-projection overlap is not itself a 3D collision with the hole void.

`ZIF_Cable_Hole_Clearance.png` / `.svg` show a dimensioned plan and enlarged edge detail with screw heads omitted. `ZIF_Holes_Cable_Native_Top.png` is a native Inventor top view with screws temporarily hidden and the cable temporarily transparent. `ZIF_M1p6_Round_Oblique.png` shows the actual assembled round-head hardware.

## Native interference result

The saved/reopened Inventor assembly has two screw-head/cable-envelope intersections (allowed as cable pressure by the user) **and two screw-head/ZIF-housing intersections** (about 0.00952 mm3 each). The current positions therefore do not provide an interference-free fit with the requested round-head screws. No hole relocation was made in this correction; the collision is reported rather than hidden by changing the hardware or geometry.

The cable is a dimensional envelope, 0.20 mm reinforced thickness. Center height 0.47 mm above PCB is an unverified placement assumption, and flex/deformation is not modeled. Screw length 4 mm is a review assumption; mating threaded support/nut was not specified. `inventor_fit.json` and `inventor_fit_round.json` are the current native results; `final_pcb_fit_validation.json` links them to the unchanged PCB and actual Content Center member hash.
