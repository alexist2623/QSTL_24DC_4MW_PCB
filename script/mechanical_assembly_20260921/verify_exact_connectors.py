"""Cross-check simplified-connector clashes against the original embedded STEP."""
from pathlib import Path
import json, math
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax1, gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from inspect_geometry import read, bounds, volume
HERE=Path(__file__).resolve().parent
OUT=HERE.parents[1]/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
data=json.loads((HERE/'pcb_geometry.json').read_text())
fit=json.loads((OUT/'assembly_validation.json').read_text())
mm=lambda s:float(s.removesuffix('mil'))*.0254

def transform(shape,axis=None,angle=0,move=None):
    t=gp_Trsf()
    if axis:t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(*axis)),math.radians(angle))
    if move:t.SetTranslation(gp_Vec(*move))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

bottom=read(OUT/'Bottom_reference.step')
results=[]
for body in data['bodies']:
    if not body['component'].startswith('SMP'):continue
    p=body['props'];source=next(m for m in data['models'] if m['ID']==p['MODELID'])
    shape=read(source['extracted_file'])
    for axis,key in (((1,0,0),'X'),((0,1,0),'Y'),((0,0,1),'Z')):
        shape=transform(shape,axis,float(p['MODEL.3D.ROT'+key]))
    shape=transform(shape,move=[mm(p['MODEL.2D.X']),mm(p['MODEL.2D.Y']),fit['pcb_thickness_mm']+mm(p['MODEL.3D.DZ'])])
    shape=transform(shape,(0,1,0),180)
    shape=transform(shape,move=fit['pcb_transform']['translation_mm'])
    common=BRepAlgoAPI_Common(bottom,shape).Shape()
    overlap=abs(volume(common))
    results.append(dict(component=body['component'],exact_model_overlap_mm3=overlap,overlap_bounds_mm=bounds(common) if overlap>1e-6 else None))
fit['exact_SMP_model_cross_check']=results
(OUT/'assembly_validation.json').write_text(json.dumps(fit,indent=2))
print(json.dumps(results,indent=2))
