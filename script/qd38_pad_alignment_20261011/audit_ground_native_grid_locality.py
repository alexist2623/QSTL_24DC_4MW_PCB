"""Prove local GND edits on the exact saved/native integer coordinate grid."""
from pathlib import Path
import hashlib
import json
import sys

import shapely
from shapely.geometry import shape, box
from shapely.ops import unary_union

H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent/"qd38_rotation_20261011"))
from audit_saved_revision_surface import read_snapshot

UNIT=2.54e-6
LOCAL=box(5.5,36,14,49)
candidate=H/"alignment_full_candidate.json"
native=H/"before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc"
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(candidate)=="4e4264afef78d39bbc27740630d56468f2d3029b03f5019c05e0e3c32f80f28c"
assert digest(native)=="1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c"
plan=json.loads(candidate.read_text())
schem=json.loads((H.parents[1]/"QSTL_QD4_2SET_38PAD/schematic_validation.json").read_text())
_,regions,_,_,_=read_snapshot(native,schem)
rows=[]
for layer in (1,2,3,4,5,32):
    previous=unary_union([r["geometry"] for r in regions if r["layer"]==layer and r["net"]=="GND"])
    current=shape(plan["ground_regions"][str(layer)])
    previous_grid=shapely.set_precision(previous,UNIT)
    current_grid=shapely.set_precision(current,UNIT)
    delta=previous_grid.symmetric_difference(current_grid)
    outside=delta.difference(LOCAL)
    added=current_grid.difference(previous_grid)
    rows.append(dict(layer=layer,passed=outside.is_empty and added.is_empty,
                     outside_local_box_grid_area_mm2=outside.area,
                     added_ground_grid_area_mm2=added.area,
                     removed_ground_grid_area_mm2=delta.area,
                     actual_grid_change_bounds_mm=list(delta.bounds),
                     raw_floating_outside_area_mm2=previous.symmetric_difference(current).difference(LOCAL).area,
                     baseline_grid_roundoff_hausdorff_mm=previous.hausdorff_distance(previous_grid)))
report=dict(passed=all(r["passed"] for r in rows),candidate_sha256=digest(candidate),
            native_sha256=digest(native),native_grid_mm=UNIT,local_box_mm=list(LOCAL.bounds),layers=rows,
            interpretation="Input and output contours are compared on the same exact native integer grid. Floating differences of approximately 1e-13 square millimetres do not change stored native coordinates. No remote ground edits or ground additions are allowed.")
(H/"alignment_native_grid_locality.json").write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report["passed"] else 2)
