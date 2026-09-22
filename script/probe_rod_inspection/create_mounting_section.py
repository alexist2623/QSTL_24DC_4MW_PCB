"""Create a true thin CAD section through the corrected plate, boss and holder."""
from pathlib import Path
import json, math, sys
from OCP.gp import gp_Pnt,gp_Dir,gp_Ax1,gp_Vec,gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,volume
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
OUT=MECH/'Rod_Holder_Adapter'
TEMP=Path(__file__).resolve().parent/'tmp'/'mounting_section'
TEMP.mkdir(parents=True,exist_ok=True)
plan=json.loads((OUT/'adapter_plan.json').read_text(encoding='utf-8-sig'))

def place(shape,pos,angle=0):
    t=gp_Trsf()
    if angle:t.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(0,1,0)),math.radians(angle))
    t.SetTranslationPart(gp_Vec(*pos))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

section_box=BRepPrimAPI_MakeBox(gp_Pnt(-5,181.75,-5),61,.05,50).Shape()
top_position=list(plan['holder_translation_mm']);top_position[2]-=8.18839662
shapes={
    'Rods':read(MECH/'Probe_H_Frame'/'Probe_H_Frame.step'),
    'Plate_and_boss':place(read(OUT/'Rod_Holder_Adapter.step'),plan['adapter_position_mm']),
    'Original_holder':place(read(MECH/'Top_ForFridge_reference.step'),top_position,180),
}
for name,shape in shapes.items():
    section=BRepAlgoAPI_Common(shape,section_box).Shape()
    assert volume(section)>0
    writer=STEPControl_Writer();writer.Transfer(section,STEPControl_AsIs)
    assert int(writer.Write(str(TEMP/(name+'.step'))))==1
print('Created true XZ sections at Y=181.75..181.80 mm from the saved CAD solids.')
