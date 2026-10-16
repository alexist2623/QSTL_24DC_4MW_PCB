"""Extract the exact saved ZIF model and inspect its rotated body bounds."""
from pathlib import Path
import hashlib
import json
import math
import zlib
import olefile
import build_fastening_review as cad
from OCP.gp import gp_Trsf,gp_Ax1,gp_Pnt,gp_Dir
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
native=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
saved=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_models.json').read_text())
record=next(m for m in saved['models'] if m['component']=='J1')
expected=record['embedded_step_sha256'][0]
found=[]
with olefile.OleFileIO(native) as doc:
    for name in doc.listdir():
        if len(name)!=2 or name[0]!='Models' or not name[1].isdigit():continue
        payload=zlib.decompress(doc.openstream(name).read())
        if hashlib.sha256(payload).hexdigest()==expected:
            path=HERE/'Current_ZIF_Embedded.step';path.write_bytes(payload);found.append(name)
assert len(found)==1,found
parts=cad.read_parts(path,'J1')
t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.pi/2)
bounds=[]
for p in parts:
    bounds.append(cad.bounds(BRepBuilderAPI_Transform(p['shape'],t,True).Shape()))
combined=[min(b[i] for b in bounds) if i<3 else max(b[i] for b in bounds) for i in range(6)]
result=dict(native=str(native),native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),model_path=str(path),
            model_sha256=expected,saved_model_record=record,rotated_local_bounds_mm=combined,parts=len(parts))
(HERE/'saved_zif_geometry.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
