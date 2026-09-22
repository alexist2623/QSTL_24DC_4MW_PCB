"""Verify the exact sleeve dimensions, axis and intersections without resizing parts."""
from pathlib import Path
import json,math,sys
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1,gp_Vec,gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,bounds,volume
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
OUT=MECH/'Probe_Tube'
HOLDER=MECH/'Rod_Holder_Adapter'

def place(shape,position,angle=0,axis=(0,1,0)):
    tr=gp_Trsf()
    if angle:tr.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(*axis)),math.radians(angle))
    tr.SetTranslationPart(gp_Vec(*position))
    return BRepBuilderAPI_Transform(shape,tr,True).Shape()

part=read(OUT/'Probe_Tube.step');info=inspect(part)
assert info['valid']
assert max(abs(a-b) for a,b in zip(bounds(part),[-27,-27,0,27,27,360]))<1e-6
assert sorted(round(c['radius'],6) for c in info['cylinders'])==[25.5,27]
expected_volume=math.pi*(27**2-25.5**2)*360
assert abs(volume(part)-expected_volume)<1e-4
explorer=TopExp_Explorer(part,TopAbs_SOLID);count=0
while explorer.More():count+=1;explorer.Next()
assert count==1
tube=place(part,[25.5,0,3],-90,(1,0,0))
assert max(abs(a-b) for a,b in zip(bounds(tube),[-1.5,0,-24,52.5,360,30]))<1e-5
records=json.loads((HOLDER/'inward_placements.json').read_text(encoding='utf-8-sig'))
def actual_shape(record):
    source=read(Path(record['path']).with_suffix('.step'))
    m=record['matrix_cm'];t=gp_Trsf()
    t.SetValues(*[m[i][j]*(10 if j==3 else 1) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(source,t,True).Shape()
parts=[(r['name'],actual_shape(r)) for r in records if r['name']!='Probe_Tube_ID51_OD54']
intersections=[]
for name,shape in parts:
    overlap=abs(volume(BRepAlgoAPI_Common(tube,shape).Shape()))
    intersections.append(dict(component=name,overlap_mm3=overlap,intersects=overlap>1e-5))
assembly=read(HOLDER/'Rod_Holder_Assembly.step')
assert BRepCheck_Analyzer(assembly).IsValid()
assert abs(volume(assembly)-volume(part)-sum(volume(s) for _,s in parts))<1e-3
result=dict(valid=True,solid_count=1,inner_diameter_mm=51,outer_diameter_mm=54,wall_thickness_mm=1.5,length_mm=360,local_bounds_mm=bounds(part),placed_bounds_mm=bounds(tube),volume_mm3=volume(part),rod_centre_midpoint_xz_mm=[25.5,3],axis_point_mm=[25.5,0,3],axis_direction=[0,1,0],intersections=intersections,rod_outer_corner_radial_overrun_mm=math.hypot(25.5,3)-25.5,plate_outer_corner_radial_overrun_mm=math.hypot(25.5,7)-25.5,dimensions_preserved=True,assembly_step_valid=True)
(OUT/'geometry_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
