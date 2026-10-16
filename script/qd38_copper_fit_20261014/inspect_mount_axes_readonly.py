"""Inspect preserved copper mounting axes against the current PCB proposal."""
import json
from build_review import ROOT, MECH, read, transform, cylinders

old = json.loads((ROOT / 'QSTL_QD4_2SET_38PAD/Mechanical_Review_20261014/mechanical_review.json').read_text())
fit = json.loads((MECH / 'assembly_validation.json').read_text())
proposal = json.loads((ROOT / 'QSTL_QD4_2SET_38PAD/Outline_Mount_Concept_20261014/qd28_left_entry_audit.json').read_text())
t = old['inverse_carrier_transform']['translation_mm']
shapes = {
    'Bottom': transform(read(MECH / 'Bottom_reference.step'), ry=180, move=t),
    'Top': transform(transform(read(MECH / 'Top_ForFridge_reference.step'), move=fit['top_transform']['translation_mm']), ry=180, move=t),
}
for name, shape in shapes.items():
    result = sorted({tuple(round(v, 6) for v in [c['point'][0], c['point'][1], c['radius']])
                     for c in cylinders(shape)
                     if abs(c['axis'][2]) > .999 and (15 < c['point'][1] < 22 or c['point'][1] > 68)})
    print(name, '(X, Y, radius):', result)
print('PCB mounts:', json.dumps(proposal['mounts'], indent=2))
