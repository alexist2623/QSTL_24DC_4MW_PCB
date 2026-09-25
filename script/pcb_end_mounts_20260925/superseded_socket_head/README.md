# ZIF M1.6 mounting review

The original PCB now has two M1.6 clearance mounts: plated drill 1.8 mm, copper land 2.2 mm, centers (1.60, 1.20) and (17.90, 1.20) mm. Pitch is 16.30 mm. The 19.5 x 67.9 mm outline is unchanged. Minimum nominal drill-to-edge web is 0.30 mm at the end and 0.70 mm at the sides. Mounts connect directly to GND, without thermal relief or paste.

`ZIF_M1p6_Fit.iam` contains the saved PCB end, the actual J1 embedded Molex 502598-5193 model, a dimensional FPC envelope, and two unmodified Inventor Content Center ISO 4762 M1.6 x 4 screws, M1.6 x 0.35 - 6g. Head diameter is 3.0 mm and head height is 1.6 mm. No washers. Screw length is a review assumption; the mating support/nut was not specified.

Native Inventor interference analysis finds no screw/housing or screw/PCB intersection at centered nominal placement. Minimum screw/housing distance is 0.024999 mm. However, 1.8 mm holes around 1.6 mm shanks allow 0.10 mm nominal radial shift, greater than that gap. Housing contact is possible with screw displacement, even before manufacturing tolerances. This is not a tolerance-safe fit approval.

The two screw heads intersect the undeformed cable envelope, which the user explicitly permits as cable pressure. Cable width is 15.6 mm and reinforced thickness is 0.20 mm; its center at 0.47 mm above the PCB is an unverified placement assumption. This is not a detailed production cable or a flex/clamping simulation. No screw-head footprint overlaps non-GND Top copper; see `final_pcb_fit_validation.json` for measured conservative plan-view distances.

The connector and hardware are native imported/supplied CAD. The PCB end is simplified to substrate and relevant holes. Pictures are native Inventor view exports. `inventor_fit.json` records saved/reopened assembly checks; `final_pcb_fit_validation.json` verifies that its physical inputs still match the final PCB after the silkscreen-only marker correction.

The final PCB passes 16 native DRC rules, has zero stored unrouted connections, and passes independent connectivity for all 37 nets. Fresh Gerber/through-drill/blind-drill files are in `../../fabrication/JLCPCB_HDI_20260925/`. There are 96 through holes, including the two 1.8 mm mounts, and 480 L5-L6-only laser blind holes.
