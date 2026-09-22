"""Preflight the user's bridge/boss/holder end-view arrangement without new holes."""
from pathlib import Path
import sys, json, math
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Vec, gp_Trsf

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read, inspect, volume, bounds
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
OUT=Path(__file__).resolve().parent/'tmp'
OUT.mkdir(exist_ok=True)

def placed(shape,position):
    tr=gp_Trsf();tr.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(0,1,0)),math.pi)
    tr.SetTranslationPart(gp_Vec(*position))
    return BRepBuilderAPI_Transform(shape,tr,True).Shape()

# Preserve the prior carrier longitudinal direction and SMP side; recenter X.
carrier_x=25.5+(6.247898311436018+26.68035571238836)/2
flange_inner=carrier_x-10.758375381081185
flange_outer=carrier_x-7.718534764180674
finger_width=13.5
bridge=BRepPrimAPI_MakeBox(gp_Pnt(0,95,6),51,150,4).Shape()
boss=BRepPrimAPI_MakeBox(gp_Pnt(flange_inner-finger_width,99,10),finger_width,142,6).Shape()
adapter=BRepAlgoAPI_Fuse(bridge,boss).Shape()
carrier_translation=[carrier_x,130.70466430122147,24.18839662]
carrier=placed(read(MECH/'Carrier_with_PCB.step'),carrier_translation)
frame=read(MECH/'Probe_H_Frame'/'Probe_H_Frame.step')
overlap=volume(BRepAlgoAPI_Common(adapter,carrier).Shape())
assert abs(overlap)<1e-5,overlap
assert abs(volume(BRepAlgoAPI_Common(adapter,frame).Shape()))<1e-5
report=dict(holder_translation_mm=carrier_translation,boss_x_min_mm=flange_inner-finger_width,boss_x_max_mm=flange_inner,boss_width_mm=finger_width,flange_outer_x_mm=flange_outer,bridge_z_mm=[6,10],boss_z_mm=[10,16],holder_exterior_face_z_mm=16,holder_body_x_mm=[carrier_x-26.68035571238836,carrier_x-6.247898311436018],unintended_overlap_mm3=overlap,holes='Not changed by this geometry preflight; screw direction awaits clarification.')
(OUT/'top_view_adapter_plan.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
