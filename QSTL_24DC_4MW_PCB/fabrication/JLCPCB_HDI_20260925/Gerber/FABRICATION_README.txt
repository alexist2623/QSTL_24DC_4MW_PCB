QSTL 24DC 6RF - JLCPCB HDI FABRICATION PACKAGE
Exported from the original saved Altium PCB on 2026-09-25.
Bare PCB only, no assembly or stencil.

LAYER MAP (all files use the same origin; no mirror)
GTL: L1 Top GND
G1: L2 DC A with GND copper pour
G2: L3 GND
G3: L4 DC B with GND copper pour
G4: L5 GND
GBL: L6 Bottom RF / QD
GTS / GBS: Top / Bottom solder mask
GTO / GBO: Top / Bottom silkscreen
GKO: 19.5 x 67.9 mm closed board outline only

L2/L4 GND-pour clearance to signal copper: nominal 0.20 mm.
DC traces, pin mapping and RF geometry are unchanged.
Two M1 mounts: 1.2 mm plated drill, 1.6 mm land, solid GND.
Centers X1.05 / X18.45, Y1.20 mm; 17.40 mm pitch.
No mounting-hole thermal relief or solder paste.

L1-L6_PTH.drl: 96 through plated holes (48 x 0.25 mm,
40 x 0.75 mm, 2 x 1.2 mm, 4 x 2.1 mm, 2 x 4.0 mm).
L5-L6_Blind_Laser_0.1mm.drl: 480 x 0.10 mm blind laser holes,
L6 to L5 ONLY, 0.25 mm copper lands. Filled and planarized.
Do NOT interpret these as through holes. No buried holes.
Excellon: metric, 4:4, leading zeros suppressed.

bottom blind slots layer.gbr: NON-PLATED blind pocket from Bottom,
4.3 x 4.3 mm, internal R0.50, depth 1.20 mm, centered X9.75 Y42.50.
Contour centerline defines finished pocket; 0.01 mm drawing stroke
is not a tool diameter. This is NOT a through-board cutout.
Keep Top copper and approximately 0.3884 mm remaining material.
See QD_cavity_drawing.png for machining side/location/depth.

50 ohm coplanar RF on L6 referenced to L5, W=0.110 mm, gap=0.200 mm.
Requested stack JLCH06161HN1-1078: 1 oz outer / 0.5 oz inner,
nominal 1.6 mm board; see stackup.csv and impedance requirement JPG.
The HDI order-page stack/inner-copper options require engineering
review if they differ from this requested dielectric/copper stack.
Confirm final stack, impedance compensation and production files.
Exposed QD pads are used for wire bonding; confirm surface-finish
suitability before production release. Quote interface finish is
a quotation assumption and does not approve bondability.
