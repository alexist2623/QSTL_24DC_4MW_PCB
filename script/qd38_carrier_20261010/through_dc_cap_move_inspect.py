from pathlib import Path
import json,math
h=Path(__file__).resolve().parent;dest=h.parents[1]/'QSTL_QD4_2SET_38PAD';p=json.loads((dest/'negotiated_plan.json').read_text())
for ref in ['C02','R02','C15','R15','C21','R21']:
 c=next(c for c in p['components'] if c['ref']==ref);pads=[d for d in p['physical_pads'] if d['ref']==ref];print(ref,c,pads)
 for pad in pads:
  for j in p['routed_jobs']:
   if j['job']['net']==pad['net'] and any(math.dist(q,[pad['x'],pad['y']])<1e-5 for q in j['points']):print('JOB',j)
