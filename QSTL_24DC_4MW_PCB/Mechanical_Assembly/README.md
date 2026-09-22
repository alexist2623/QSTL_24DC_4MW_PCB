# Current PCB carrier assembly

Prepared 2026-09-21 using the current saved PCB and the read-only `Bottom.SLDPRT` and **`Top_ForFridge.SLDPRT`** from `Carrier_8MW_24DC/Mechanical/Narrow_V3_24DC_8MW`. The upper part in the delivered assemblies is derived from `Top_ForFridge`, superseding the initial `Top` import.

## Open the model

- `Carrier_with_PCB.iam`: assembled Inventor model.
- `Carrier_with_PCB.step`: portable assembled STEP model.
- `Carrier_exploded.iam`: separated review assembly; Bottom is offset by -20 mm and Top_ForFridge by +30 mm from their assembled positions.
- `PCB_simplified.iam` and `PCB_simplified.step`: simplified PCB alone.
- `Assembly_exploded.png`, `Assembly_closed.png`, `PCB_QD_side.png`, and `PCB_SMP_side.png`: Inventor renders.

Keep the native assemblies with `Bottom.ipt`, `Top_ForFridge.ipt`, and the complete `PCB_parts/` folder. The assembly parts contain imported geometry and do not require the original SolidWorks files. Occurrences are grounded at their calculated placements; they are not a parametric mate-constraint model.

## Geometry retained

The PCB outline is 19.5 x 67.9 mm. Thickness from the saved copper/dielectric stack is 1.58839662 mm. All six mounting holes, forty SMP pin drills, eight SMP positions, the ZIF connector, and all twelve R/C positions are retained. The QD-side pocket is 4.3 x 4.3 mm, 1.2 mm deep, with R0.5 internal corners and approximately 0.3884 mm remaining substrate.

Resistors use 1.6 x 0.8 x 0.45 mm rectangular envelopes. Capacitors use 1.0 x 0.5 x 0.553 mm rectangular envelopes. These dimensions are taken from the PCB's embedded models. SMP connectors retain their outer barrel, bore and five pins in simplified form. ZIF uses the source model's 17.4 x 3.8 x 1.15 mm closed-actuator envelope. Twenty-four QD bond pads are shown as separate thin visual solids. Copper routing, solder mask, small vias, solder fillets and tiny component details are omitted.

## Orientation and validation

The SMP/Top PCB face faces Bottom; the QD/R/C/Bottom PCB face faces Top_ForFridge. The PCB uses a proper 180-degree rotation about Y. Eight SMP centres and six mounting centres register to the Bottom hole pattern within 0.000001 mm. Bottom's nominal PCB seat is native Z=2 mm. Top_ForFridge's native seating face is Z=-4.6 mm, translated by +8.18839662 mm to meet the opposite PCB face.

No R/C body intersects either mechanical part. The minimum calculated R/C clearance to either part is approximately 1.667 mm. The following existing geometry overlaps remain uncorrected:

- SMP1/2/3/8 intersect Bottom locally. The user explicitly accepted SMP overlap for this assembly pass. The original embedded connector STEP confirms each overlap, approximately 0.0762 mm3.
- The Top_ForFridge left skirt overlaps the PCB edge by approximately 0.0611 mm laterally, total volume 5.6558 mm3.
- Bottom has a local PCB seating overlap reaching approximately 0.0111 mm, total volume 0.2757 mm3.
- Top_ForFridge and Bottom intersect by approximately 3.5992 mm3 at the adopted nominal seats.

These results document the present fit; no PCB outline or source mechanical geometry was changed to remove the overlaps. Detailed results are in `assembly_validation.json`, with interference STEP files for inspection. `inventor_occurrences.json` records the actual native assembly references and placements. `delivery_verification.json` verifies source-file preservation and exported STEP agreement.

The original PCB and SolidWorks reference files remain unchanged. Helper scripts are in repository-root `script/mechanical_assembly_20260921/`.
