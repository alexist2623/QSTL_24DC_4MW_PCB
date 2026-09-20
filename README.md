# QSTL 24DC / 4MW PCB

Open `QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PrjPcb` in Altium Designer.

The existing project now contains the routed ZIF carrier: a 19.5 x 67.9 mm, six-layer board with four RF channels and 20 DC-only QD connections. DC routing uses L2 and RF routing uses L4. ZIF and six SMP connectors are on Top; the 24-pad QD and 0603 bias resistors/capacitors are on Bottom. SMP positions and the six mechanical holes match the reference board.

ZIF signal contacts 1-12 and 15-26 are used. The exact QD-to-ZIF assignments are in [PIN_MAPPING.csv](QSTL_24DC_4MW_PCB/docs/PIN_MAPPING.csv). R/C values are 10 kohm and 1 nF, and all 16 bias component pads use via-in-pad connections. Signal routing avoids the QD interior.

All 218 vias have top and bottom solder-mask tenting enabled. The 16 vias inside component pads retain Bottom exposure through the component solder-mask openings. The requested 436 explicit top/bottom paste apertures remain. All 154 ground stitching vias use solid polygon connections.

The schematic-to-PCB comparison passes for 16 components, 123 component pins, 33 named nets and 31 intentional NC pins. Six additional GND mounting pads are PCB-only. The routed design passed Altium DRC with zero violations before the mask-only change; the subsequent tenting and project-filename updates preserve the copper and placement. [Validation](QSTL_24DC_4MW_PCB/docs/validation.json) records the published file hashes.

RF nominal delays are approximately 353.8014 ps per channel with modelled spread below 1 ps. This is a copper/via propagation calculation using Dk=4.8, not a measured or EM-validated tolerance including components, connectors and manufacturing variation.

[PCB overview](QSTL_24DC_4MW_PCB/docs/layout.png) · [Schematic overview](QSTL_24DC_4MW_PCB/docs/schematic.png)
