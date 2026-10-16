from pathlib import Path
import json,math
h=Path(__file__).resolve().parent;p=json.loads((h.parents[1]/'QSTL_QD4_2SET_38PAD/negotiated_plan.json').read_text())
for j in p['routed_jobs']:
 if j['job']['net'] in ['S02','MW02','S15','MW15','S21','MW21']:print(j)
