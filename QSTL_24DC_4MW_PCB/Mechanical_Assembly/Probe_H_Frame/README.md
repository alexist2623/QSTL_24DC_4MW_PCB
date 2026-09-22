# Simplified probe H frame

`Probe_H_Frame.ipt` is an editable Inventor 2027 part containing four separate solid bodies: two rods and two crossbars. `Probe_H_Frame.step` is the neutral-format export. The upper anchor, lower mechanism and enclosing tube are excluded. The existing PCB and carrier assembly are unchanged.

The source is the user-supplied `SO01373.10-Probe-R01.pdf`, drawing A00424 R01, section X2-X2. This is an envelope/placement model, not a complete manufacturing definition.

## Dimensions

| Parameter | Value | Basis |
|---|---:|---|
| RodLength | 360 mm | Drawing dimension |
| RodWidth | 6 mm | Derived from overall width 51 mm and inner gap 39 mm |
| ClearGap | 39 mm | Drawing dimension |
| OverallWidth | 51 mm | Derived, consistent with drawing |
| RodCentreSpacing | 45 mm | Derived, consistent with drawing |
| ASSUMED_RodDepth | 6 mm | Not dimensioned; provisional |
| ASSUMED_CrossbarDepth | 6 mm | Not dimensioned; provisional |
| EST_CrossbarHeight | 8 mm | Estimated from drawing geometry |
| EST_UpperCrossbarFromTop | 110 mm | Estimated centre position |
| EST_LowerCrossbarFromTop | 270 mm | Estimated centre position |
| HolePitch | 10 mm | Drawing dimension |
| FirstHoleFromTop | 30 mm | Drawing dimension |
| HoleCount | 33 per rod | Drawing annotation |
| HoleNominalDiameter | 3 mm | Simplified nominal envelope of M3 threads |

The rods are marked copper in the drawing, but the grade is unspecified. The model uses a copper-colored appearance; material density and strength are not certified. M3 thread helices, axial end fastening holes, and undimensioned crossbar holes/fasteners are omitted. The 3 mm cylindrical holes represent the nominal thread envelope and are not a tap-drill prescription.

## Coordinates and editing

Origin is the lower outside corner of the left rod. X spans the 51 mm overall width, Y runs from the bottom to the top (360 mm), and Z is the provisional front-to-back depth. Crossbars occupy the clear space between rods and meet them at their end faces without positive-volume overlap. This is a simplified interface, not a detailed fastener joint.

Open the Inventor Parameters dialog to edit the named user parameters. `ASSUMED_` and `EST_` prefixes identify provisional values. Dimensions, four extrusion features, and the repeated hole pattern are driven by these parameters. OverallWidth and RodCentreSpacing are derived expressions. Keep parameter changes physically consistent with the hole field and crossbar envelope.

## Verification

The native model was saved and reopened. Changing rod depth to 7 mm and the upper crossbar offset to 115 mm correctly updated the solids; the values were then restored to 6 mm and 110 mm. Independent STEP checks confirm four valid solids, 51 x 360 x 6 mm bounds, 33 holes per rod, 10 mm hole pitch, and no positive-volume intersections. See `native_verification.json` and `geometry_verification.json`.

Builder and verification scripts are under repository-root `script/probe_rod_inspection/`. Screenshots are rendered by Inventor directly from the saved model.
