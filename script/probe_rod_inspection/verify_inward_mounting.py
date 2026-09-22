"""Verify reopened occurrence matrices against independent STEP geometry."""
from pathlib import Path
import json,sys,math
from OCP.gp import gp_Trsf,gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,bounds,volume,inspect
OUT=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Rod_Holder_Adapter'
records=json.loads((OUT/'inward_placements.json').read_text(encoding='utf-8-sig'))

def transformed(shape,m):
    t=gp_Trsf()
    t.SetValues(*[m[i][j]*(10 if j==3 else 1) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

parts={r['name']:transformed(read(Path(r['path']).with_suffix('.step')),r['matrix_cm']) for r in records}
assert len(parts)==14
plate=parts['Solid_Plate_With_Integral_Mounting_Boss'];frame=parts['Existing_Probe_H_Frame']
device=parts['Existing_Carrier_Hung_From_Side_Slots'];tube=parts['Probe_Tube_ID51_OD54']
pb=bounds(plate);db=bounds(device)
assert max(abs(a-b) for a,b in zip(pb,[0,135,-4,51,215,6]))<1e-6,pb
assert bounds(frame)==[0,0,0,51,360,6]
plate_mid=(pb[0]+pb[3])/2;device_mid=(db[0]+db[3])/2
assert abs(plate_mid-device_mid)<1e-6,(plate_mid,device_mid)
info=inspect(plate)
holes=[h for h in info['cylinders'] if abs(h['radius']-1.25)<1e-6 and abs(h['axis'][0])>0.99]
assert len(holes)==10
for x in (19.794248369169,33.294248369169):
    row=sorted([h for h in holes if abs(h['point'][0]-x)<1e-6],key=lambda h:h['point'][1])
    assert len(row)==5
    for i,h in enumerate(row):
        assert abs(h['point'][1]-(144.82802366515844+16*i))<1e-6 and abs(h['point'][2]-3)<1e-6
        assert abs(h['bounds'][3]-h['bounds'][0]-6)<1e-6
checks=[]
def check(label,a,b,touch=True):
    overlap=abs(volume(BRepAlgoAPI_Common(a,b).Shape()))
    d=BRepExtrema_DistShapeShape(a,b);d.Perform()
    checks.append(dict(pair=label,overlap_mm3=overlap,minimum_distance_mm=d.Value()))
    assert overlap<1e-5,checks[-1]
    if touch:assert d.Value()<1e-5,checks[-1]
check('Plate / rods',plate,frame)
check('Plate / device',plate,device)
check('Device / rods',device,frame,False)
for name,shape in parts.items():
    if name.startswith('Device_Clamp_M3_'):
        check(name+' / plate',shape,plate);check(name+' / device',shape,device)
    if name.startswith('Rod_Clamp_M3_'):
        check(name+' / plate',shape,plate);check(name+' / rods',shape,frame)
assembly=read(OUT/'Rod_Holder_Assembly.step')
assert BRepCheck_Analyzer(assembly).IsValid()
assert abs(volume(assembly)-sum(volume(s) for s in parts.values()))<1e-3
intersections=[dict(component=name,overlap_mm3=abs(volume(BRepAlgoAPI_Common(tube,shape).Shape()))) for name,shape in parts.items() if name!='Probe_Tube_ID51_OD54']
result=dict(assembly_step_valid=True,assembly_occurrences=14,actual_reopened_matrices_used=True,plate_bounds_mm=pb,device_bounds_mm=db,plate_midplane_x_mm=plate_mid,device_centre_x_mm=device_mid,centre_offset_mm=device_mid-plate_mid,base_plate_z_mm=[-4,0],rod_z_mm=[0,6],inward_boss_z_mm=[0,6],device_length_mm=db[4]-db[1],device_upper_overhang_mm=max(0,db[4]-215),thread_count=10,threads_per_side=5,interfaces=checks,sleeve_intersections=intersections)
(OUT/'inward_geometry_verification.json').write_text(json.dumps(result,indent=2))

# A real section through the source holder shows its contact with the boss explicitly.
cm=next(r['matrix_cm'] for r in records if r['name']=='Existing_Carrier_Hung_From_Side_Slots')
top_translation=gp_Trsf();top_translation.SetTranslationPart(__import__('OCP.gp',fromlist=['gp_Vec']).gp_Vec(0,0,8.18839662))
top=transformed(BRepBuilderAPI_Transform(read(OUT.parent/'Top_ForFridge_reference.step'),top_translation,True).Shape(),cm)
section_box=BRepPrimAPI_MakeBox(gp_Pnt(-5,175,-30),61,.05,65).Shape()
section_dir=ROOT/'script'/'probe_rod_inspection'/'tmp'/'inward_section';section_dir.mkdir(parents=True,exist_ok=True)
for name,shape in {'Rods':frame,'Plate':plate,'Holder':top,'Tube':tube}.items():
    section=BRepAlgoAPI_Common(shape,section_box).Shape();assert volume(section)>0
    w=STEPControl_Writer();w.Transfer(section,STEPControl_AsIs);w.Write(str(section_dir/(name+'.step')))
print(json.dumps({k:v for k,v in result.items() if k not in ('interfaces','sleeve_intersections')},indent=2))
