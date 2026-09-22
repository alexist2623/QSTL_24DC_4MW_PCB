"""Verify the adapter against the actual holder and rod solids and hole axes."""
from pathlib import Path
import hashlib
import json
import math
import sys
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1,gp_Vec,gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,bounds,volume
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
OUT=MECH/'Rod_Holder_Adapter'
plan=json.loads((OUT/'adapter_plan.json').read_text(encoding='utf-8-sig'))

def transform(shape,position,angle=0):
    t=gp_Trsf()
    if angle:t.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(0,1,0)),math.radians(angle))
    t.SetTranslationPart(gp_Vec(*position))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

local=read(OUT/'Rod_Holder_Adapter.step')
local_info=inspect(local)
assert local_info['valid']
assert max(abs(a-b) for a,b in zip(bounds(local),[0,0,0,51,66,10.5]))<1e-5
e=TopExp_Explorer(local,TopAbs_SOLID);count=0
while e.More():count+=1;e.Next()
assert count==1
adapter=transform(local,plan['adapter_position_mm'])
frame=read(MECH/'Probe_H_Frame'/'Probe_H_Frame.step')
carrier=transform(read(MECH/'Carrier_with_PCB.step'),plan['holder_translation_mm'],180)
checks=[]
for label,a,b in [('Adapter / frame',adapter,frame),('Adapter / existing carrier',adapter,carrier),('Frame / existing carrier',frame,carrier)]:
    overlap=abs(volume(BRepAlgoAPI_Common(a,b).Shape()))
    distance=BRepExtrema_DistShapeShape(a,b);distance.Perform()
    checks.append(dict(pair=label,overlap_mm3=overlap,minimum_distance_mm=distance.Value()))
    assert overlap<1e-5,(label,overlap)

placed_holes=inspect(adapter)['cylinders']
frame_holes=inspect(frame)['cylinders']
rod_alignment=[]
for hole in placed_holes:
    if abs(hole['radius']-1.7)<1e-5:
        error=min(math.dist(hole['point'][:2],h['point'][:2]) for h in frame_holes)
        rod_alignment.append(error)
assert len(rod_alignment)==4 and max(rod_alignment)<1e-5

# Top_ForFridge's existing native holes are translated within the carrier first.
top_source=read(MECH/'Top_ForFridge_reference.step')
fit=json.loads((MECH/'assembly_validation.json').read_text())
top=transform(transform(top_source,fit['top_transform']['translation_mm']),plan['holder_translation_mm'],180)
holder_holes=[h for h in inspect(top)['cylinders'] if abs(h['radius']-1.25)<1e-5 and abs(h['axis'][2])>.99]
holder_alignment=[]
for hole in placed_holes:
    if abs(hole['radius']-1.4)<1e-5:
        holder_alignment.append(min(math.dist(hole['point'][:2],h['point'][:2]) for h in holder_holes))
assert len(holder_alignment)==4 and max(holder_alignment)<1e-5

assembly=read(OUT/'Rod_Holder_Assembly.step')
assert inspect(assembly)['valid']
assert abs(volume(assembly)-sum(volume(s) for s in [adapter,frame,carrier]))<1e-3
pcb=ROOT/'QSTL_24DC_4MW_PCB'/'QSTL_24DC_4MW_PCB.PcbDoc'
assert hashlib.sha256(pcb.read_bytes()).hexdigest()=='84feed018fbaf5cbfa3203201c8771711b00ffec18aa0aadaf20fdeadb99ca63'
result=dict(adapter_valid=True,adapter_solid_count=1,adapter_bounds_mm=bounds(local),adapter_volume_mm3=volume(local),interfaces=checks,rod_hole_axis_errors_mm=rod_alignment,holder_hole_axis_errors_mm=holder_alignment,rail_pocket_nominal_clearance_mm=.25,assembly_step_valid=True,pcb_unchanged=True,existing_carrier_internal_interferences='Retained unchanged; see parent assembly_validation.json')
(OUT/'geometry_verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
