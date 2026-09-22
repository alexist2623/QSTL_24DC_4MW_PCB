# H-frame cylindrical sleeve

An open-ended tube is added to the existing rod/holder assembly. Inner diameter is 51 mm, outer diameter is 54 mm, and radial wall thickness is 1.5 mm. Length is assumed to be 360 mm, matching the rods; it remains an editable Inventor parameter.

The two rod centre lines have frame (X,Z) coordinates (3,3) and (48,3) mm. The tube axis passes through their midpoint (25.5,3) mm and runs parallel to frame Y from 0 to 360 mm. The centre of the full cylinder is therefore (25.5,180,3) mm. The standalone part uses local Z as its axis; its assembly occurrence is rotated -90 degrees about X and translated by (25.5,0,3) mm.

## Files

- `Probe_Tube.ipt`: editable native part with InnerDiameter, OuterDiameter, TubeLength and derived WallThickness parameters.
- `Probe_Tube.step`: standalone tube geometry.
- `../Rod_Holder_Adapter/Rod_Holder_Assembly.iam` and `.step`: updated full assembly with one tube occurrence.
- `Tube_isometric.png`, `Tube_end.png`: standalone tube views.
- `Assembly_with_tube.png`, `Assembly_tube_end.png`: assembly views. Transparency is an occurrence appearance override for inspection, not a physical opening or cutaway.

## Dimensional and placement checks

The saved STEP is one valid annular solid with radii 25.5 and 27 mm, 360 mm axial length and volume 89064.151729 mm³. Its placed bounds are X=-1.5..52.5, Y=0..360, Z=-24..30 mm. Native dimensions and occurrence transformation were checked after save/reopen. Changing the outer diameter to 55 mm updated wall thickness to 2 mm; the requested 54 mm diameter and 1.5 mm wall were then restored.

## Actual intersections at the requested dimensions

The tube is a dimensional envelope model and does not currently clear every existing part. Requested diameters and all earlier geometry were preserved.

| Existing component group | Tube intersection volume |
|---|---:|
| H frame | 254.648 mm³ |
| Short 80 mm mounting plate and raised boss | 334.566 mm³ |
| Carrier and PCB group, centered and mounted inward | 0 mm³ |
| Each rod screw | Approximately 11.903 mm³, 8 screws |
| Two device-clamping screws | None |

The square rod outer corners extend 0.176 mm radially beyond the 25.5 mm inner radius. The plate's outer upper corners extend 0.943 mm beyond it. These values describe geometric intersections, not manufacturing tolerances. No source part was trimmed, moved or resized to hide them. Material and fits are unspecified.

See `tube_plan.json`, `geometry_verification.json` and `native_verification.json`. Scripts are in repository-root `script/probe_rod_inspection/`: `build_probe_tube.ps1`, `verify_probe_tube.py` and `finalize_probe_tube.ps1`.
