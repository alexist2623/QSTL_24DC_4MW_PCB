"""Measure all three mounting reversals and create true CAD cross sections."""
from pathlib import Path
import json, math, sys
from OCP.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Vec, gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read, inspect, bounds, volume
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
HOLDER=MECH/'Rod_Holder_Adapter'
OUT=HOLDER/'Orientation_Review'
OUT.mkdir(exist_ok=True)
plan=json.loads((HOLDER/'adapter_plan.json').read_text(encoding='utf-8-sig'))

def place(shape,pos,angle=0,axis=(0,1,0)):
    t=gp_Trsf()
    if angle:t.SetRotation(gp_Ax1(gp_Pnt(),gp_Dir(*axis)),math.radians(angle))
    t.SetTranslationPart(gp_Vec(*pos))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

carrier=place(read(MECH/'Carrier_with_PCB.step'),plan['holder_translation_mm'],180)
plate=place(read(HOLDER/'Rod_Holder_Adapter.step'),plan['adapter_position_mm'])
frame=read(MECH/'Probe_H_Frame'/'Probe_H_Frame.step')
tube=place(read(MECH/'Probe_Tube'/'Probe_Tube.step'),[25.5,0,3],-90,(1,0,0))
side=read(HOLDER/'Device_M3x8_Simplified.step')
rod=read(HOLDER/'Rod_M3x8_Simplified.step')
original_screws=[place(side,p,-90) for p in plan['side_clamp_centres_mm']]
rod_screws=[place(rod,[x,y,10],180) for x in (3,48) for y in plan['rod_fastener_rows_y_mm']]
# A: turn the device in its mounting plane, then use the next lower pair of holes.
reverse_translation=[plan['boss_x_min_mm']+plan['boss_x_max_mm'],2*176.82802366515844,0]
# B: move the complete mounting group to the opposite face of the unchanged rods.
back_translation=[51,0,6]
cases=[('Current',False,False),('Device_reversed',True,False),('Plate_reversed',False,True),('Both_reversed',True,True)]
reports=[]
section_box=BRepPrimAPI_MakeBox(gp_Pnt(-5,181.75,-30),61,.05,65).Shape()
for name,reverse_device,reverse_plate in cases:
    p=plate;c=carrier;side_screws=original_screws;rs=rod_screws
    if reverse_device:
        c=place(c,reverse_translation,180,(0,0,1))
        side_screws=[place(s,reverse_translation,180,(0,0,1)) for s in side_screws]
    if reverse_plate:
        p=place(p,back_translation,180)
        c=place(c,back_translation,180)
        side_screws=[place(s,back_translation,180) for s in side_screws]
        rs=[place(s,back_translation,180) for s in rs]
    checks=[]
    for label,a,b in [('Plate / rods',p,frame),('Plate / device',p,c),('Device / rods',c,frame)]+[(f'Device screw {i+1} / plate',s,p) for i,s in enumerate(side_screws)]+[(f'Device screw {i+1} / device',s,c) for i,s in enumerate(side_screws)]+[(f'Rod screw {i+1} / plate',s,p) for i,s in enumerate(rs)]+[(f'Rod screw {i+1} / frame',s,frame) for i,s in enumerate(rs)]:
        overlap=abs(volume(BRepAlgoAPI_Common(a,b).Shape()))
        distance=BRepExtrema_DistShapeShape(a,b);distance.Perform()
        checks.append(dict(pair=label,overlap_mm3=overlap,minimum_distance_mm=distance.Value()))
        assert overlap<1e-5,checks[-1]
        if label!='Device / rods':assert distance.Value()<1e-5,checks[-1]
    sleeve=[]
    for label,shape in [('Plate',p),('Device',c),('Rods',frame)]+[(f'Rod screw {i+1}',s) for i,s in enumerate(rs)]+[(f'Device screw {i+1}',s) for i,s in enumerate(side_screws)]:
        sleeve.append(dict(component=label,overlap_mm3=abs(volume(BRepAlgoAPI_Common(tube,shape).Shape()))))
    parts={ 'Rods':frame,'Plate':p,'Device':c,'Tube':tube }
    section_dir=OUT/'Sections'/name;section_dir.mkdir(parents=True,exist_ok=True)
    for part,shape in parts.items():
        section=BRepAlgoAPI_Common(shape,section_box).Shape()
        assert volume(section)>0,(name,part)
        w=STEPControl_Writer();w.Transfer(section,STEPControl_AsIs)
        assert int(w.Write(str(section_dir/(part+'.step'))))==1
    cb=bounds(c)
    reports.append(dict(name=name,reverse_device=reverse_device,reverse_plate=reverse_plate,device_bounds_mm=cb,plate_bounds_mm=bounds(p),device_length_mm=cb[4]-cb[1],device_overhang_y_mm=[max(0,135-cb[1]),max(0,cb[4]-215)],interfaces=checks,sleeve_intersections=sleeve,expected_assembly_volume_mm3=sum(volume(s) for s in [p,c,frame,tube,*side_screws,*rs])))
result=dict(plate_length_mm=80,device_length_mm=79.43999922,device_reverse_translation_mm=reverse_translation,plate_reverse_translation_mm=back_translation,device_reverse_axis='Z',plate_reverse_axis='Y',section_y_mm=181.75,cases=reports)
(OUT/'orientation_measurements.json').write_text(json.dumps(result,indent=2))
print(json.dumps([{'case':r['name'],'overhang_mm':r['device_overhang_y_mm'],'sleeve_device_overlap_mm3':r['sleeve_intersections'][1]['overlap_mm3']} for r in reports],indent=2))
