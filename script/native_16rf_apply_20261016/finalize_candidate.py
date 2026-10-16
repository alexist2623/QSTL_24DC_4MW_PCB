"""Finalize placeholder port names without changing computed geometry."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
p=json.loads((H/'candidate.json').read_text())
data=json.loads((H.parents[1]/'QSTL_QD4_2SET_38PAD/ZIF10mm_Reference_End_20261016/updated_mechanical_plan.json').read_text())
if not p.get('series_net_names_corrected'):
    rename={'S'+str(r['qd_pad']).zfill(2):'S'+r['smp'][3:] for r in data['rows']}
    for arr in ('physical_pads','tracks','arcs'):
        for d in p[arr]:
            if d['net'] in rename:d['net']=rename[d['net']]
    p['series_net_names_corrected']=True
by={pin:n for n,pins in p['nets'].items() for pin in pins}
for v in p['vias']:
    if v['label'].startswith('J1-'):v['net']=by[v['label']]
assert all(v['net'] in p['nets'] for v in p['vias'])
actual={}
for d in p['physical_pads']:
    if d['ref'] and d['net']:actual.setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
diff={n:{'actual':sorted(actual.get(n,[])),'expected':sorted(p['nets'].get(n,[]))} for n in set(actual)|set(p['nets']) if sorted(actual.get(n,[]))!=sorted(p['nets'].get(n,[]))}
print('Membership differences',json.dumps(diff,indent=2))
assert not diff
(H/'candidate.json').write_text(json.dumps(p,indent=2))
print('All terminal via nets resolved to their routed DC net.')
