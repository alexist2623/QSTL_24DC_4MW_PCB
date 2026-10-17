"""Inspect native resistor model transforms and their actual pad axes."""
from pathlib import Path
import sys,json,math,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/qd38_carrier_20261010')]
from audit_saved_revision_surface import read_snapshot
from audit_source_model_transforms import inspect
pcb=P/(P.name+'.PcbDoc');sch=json.loads((P/'schematic_validation.json').read_text())
b=read_snapshot(pcb,sch);m=inspect(pcb);uid={v:k for k,v in sch['components'].items()}
rows=[]
for q in m['bodies']:
    ref=uid.get(q['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),q['component'])
    if not ref.startswith('R'):continue
    pads=sorted([p for p in b[0] if p['ref']==ref],key=lambda p:p['pin'])
    angle=math.degrees(math.atan2(pads[1]['y']-pads[0]['y'],pads[1]['x']-pads[0]['x']))%180
    rows.append(dict(ref=ref,pad_axis_deg=angle,model_rotation=q['rotation_xyz_deg'],model_origin_mm=q['model_origin_mm'],overall_height_mm=q['overall_height_mm'],component_rotation=q['component_fields'].get('ROTATION'),body_fields=q['body_fields'],embedded_model_records=q['embedded_model_records']))
(H/'inspection.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),resistors=rows,models=m),indent=2))
print(json.dumps([{k:v for k,v in r.items() if k not in ('body_fields','embedded_model_records')} for r in rows],indent=2))
