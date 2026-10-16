"""Independently verify both copper M2 axes and bind final review images."""
from pathlib import Path
import json
import math
from build_review import ROOT,HERE,OUT,MECH,read,transform,cylinders,sha,compose
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS

r=json.loads((OUT/'mechanical_review.json').read_text())
t=r['inverse_carrier_transform']['translation_mm']
fit=json.loads((MECH/'assembly_validation.json').read_text())
top=transform(transform(read(MECH/'Top_ForFridge_reference.step'),move=fit['top_transform']['translation_mm']),ry=180,move=t)
bottom=transform(read(MECH/'Bottom_reference.step'),ry=180,move=t)
axes=[c for c in cylinders(top) if abs(c['axis'][2])>.999 and abs(c['radius']-2.1)<1e-5]
assert len(axes)==4
for m in r['m2_registration']:
    c=min(axes,key=lambda c:math.dist(c['point'][:2],m['pcb_xy_mm']))
    m['Top_ForFridge_counterbore_axis_error_mm']=math.dist(c['point'][:2],m['pcb_xy_mm'])
    m['Top_ForFridge_counterbore_diameter_mm']=2*c['radius']
    assert m['Top_ForFridge_counterbore_axis_error_mm']<1e-5

def planes(s,axis):
    result=[];e=TopExp_Explorer(s,TopAbs_FACE)
    while e.More():
        a=BRepAdaptor_Surface(TopoDS.Face(e.Current()))
        if a.GetType()==GeomAbs_Plane:
            p=a.Plane();normal=p.Axis().Direction()
            if abs(normal.Coord(axis+1))>.999999:
                result.append(p.Location().Coord(axis+1))
        e.Next()
    return result

xp=planes(top,0);yp=planes(bottom,1)
assert all(min(abs(x-v) for v in xp)<1e-7 for x in r['QD_side_skirt_inner_X_mm'])
assert min(abs(r['SMP_side_end_lip_Y_mm']-y) for y in yp)<1e-7
assert all(sha(Path(p))==h for p,h in r['source_hashes'].items())
r['both_copper_M2_axes_verified']=True
r['dimension_planes_verified_from_actual_STEP']=True
compose(r)
r['images']={name:dict(path=str(OUT/name),sha256=sha(OUT/name)) for name in
             ('SMP16_Copper_M2_Assembly.png','PCB_Copper_Growth_Envelope.png')}
(OUT/'mechanical_review.json').write_text(json.dumps(r,indent=2)+'\n')
(OUT/'README.md').write_text('''# 16-SMP carrier with existing copper parts

Mechanical size review prepared 2026-10-14. The two named STEP assemblies use the original `Bottom_reference.step` and `Top_ForFridge_reference.step` copper geometry, the actual saved 16-SMP source model, and a 19.50 x 67.90 x 1.58839662 mm PCB envelope with the original mounting axes. Four M2 clearance holes in the PCB are registered with the Bottom tap axes and Top_ForFridge counterbore axes within 0.00001 mm. No screws or mating cables are modeled.

- `Saved_7Rows_Copper_M2_Review.step`: the last saved native 3/2/2/2/2/2/3 SMP placement.
- `Relocation_Horizontal_End_Pairs_Copper_M2_Review.step`: the later corrected review with a horizontal inward end pair and three outboard side pairs on each half, leaving the QD sides empty. This is a mechanical candidate, not an applied electrical PCB revision. It supersedes the rejected six-row 3/3/2 review interpretation for this illustration.
- `SMP16_Copper_M2_Assembly.png`: saved placement, latest relocation and exploded copper comparison. Transparency and exploded displacement are display choices only.
- `PCB_Copper_Growth_Envelope.png`: M2-registered top view and a dimensioned width-envelope schematic based on actual planar CAD faces.

With the M2 axes fixed, the Top_ForFridge skirt spans X=-0.172824..19.438891 mm around the PCB X=0..19.5 mm: 0.172824 mm free on the left and an inherited 0.061109 mm overlap on the right. Its 19.611716 mm total inner width is therefore not a symmetric width-growth allowance. The Bottom end lip starts at Y=68.039999 mm, only 0.139999 mm beyond the current Y=67.9 mm board end. There is no finite negative-Y/ZIF-end limit from these two parts alone; rod, cable and adapter constraints are absent. A full-width 20 mm board increases the Top_ForFridge overlap volume by approximately 30.282 mm3 relative to the current rectangular envelope.

The existing side-wall and nominal-seat overlaps remain documented in `mechanical_review.json`. SMP-to-legacy-copper-opening mismatches are intentionally ignored at the user's instruction. R0603/C1206 placement, routing, shields, masks, screw heads and connector plugs are not validated by this model. This is a nominal geometry study, not a tolerance-qualified fit or a manufacturing maximum size. Source PCB, schematic and copper STEP files are hash-verified unchanged; both exported assemblies reopen with valid BRep geometry and matching solid counts, bounds and volume.
''',encoding='utf-8')
print(json.dumps(dict(passed=True,both_copper_M2_axes_verified=True,
    maximum_axis_error_mm=max(max(m['axis_error_mm'],m['Top_ForFridge_counterbore_axis_error_mm']) for m in r['m2_registration']),
    images=list(r['images']),source_files_unchanged=True),indent=2))
