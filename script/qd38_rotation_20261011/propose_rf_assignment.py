"""Write a mapping-only RF alternative; never overwrite frozen placement."""
import copy,json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
source=H/'placement_candidate.json'
p=json.loads(source.read_text())
mapping={s['q']:s['q'] for s in p['smp']}
for a,b in [(12,13),(31,32)]:mapping[a],mapping[b]=b,a
inverse={q:g for g,q in mapping.items()}
old_end=copy.deepcopy(p['dc_endpoints']);old_pin={r['qd_pad']:copy.deepcopy(r) for r in p['pinmap']}
def newnet(net):
    if net and net.startswith('DC') and int(net[2:]) in mapping:return f'DC{mapping[int(net[2:])]:02}'
    return net
for d in p['physical_pads']:
    if d['ref']=='J1':d['net']=newnet(d['net'])
    elif d['ref'] and d['ref'].startswith(('R','C')):
        g=int(d['ref'][1:]);q=mapping[g]
        if d['ref'].startswith('R'):d['net']=f'MW{q:02}' if d['pin']=='1' else f'DC{q:02}'
        elif d['pin']=='2':d['net']=f'MW{q:02}'
for v in p['vias']:v['net']=newnet(v['net'])
for t in p['tracks']:t['net']=newnet(t['net'])
for job in p['route_jobs']:
    if job['kind']=='DC':job['net']=newnet(job['net'])
    elif job['net'].startswith('MW'):
        g=int(job['net'][2:]);q=mapping[g];job['net']=f'MW{q:02}'
        if job['kind']=='RF_QD':
            pad=p['pads'][q-1];job['a']=[a+.15*u for a,u in zip(pad['absolute_center'],pad['normal'])]
for s in p['smp']:s['q']=mapping[s['q']]
for row in p['pinmap']:
    q=row['qd_pad']
    if q not in inverse:continue
    g=inverse[q];row.update(zif_pin=old_pin[g]['zif_pin'],dc_layer=old_pin[g]['dc_layer'],smp=f'SMP{g:02}',resistor=f'R{g:02}',capacitor=f'C{g:02}')
    p['dc_endpoints'][str(q)]=old_end[str(g)]
p['nets']={}
for d in p['physical_pads']:
    if d['ref'] and d['net']:p['nets'].setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
p['rf_physical_group_to_qd_assignment']={str(g):q for g,q in mapping.items()}
p['status']='MAPPING_ONLY_RF_ALTERNATIVE_NOT_ROUTED_OR_APPROVED'
p.pop('placement_validation',None)
out=H/'placement_rf_assignment_pairs_12_13_31_32.json';out.write_text(json.dumps(p,indent=2))
report=dict(status=p['status'],source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),candidate=str(out),physical_positions_changed=False,group_to_QD_pad=p['rf_physical_group_to_qd_assignment'],required_followup='Route against full resistor-body keepouts; if accepted, rename existing DC copper nets and synchronize copied schematic/J1 pin mapping by physical bias endpoint.')
(H/'rf_assignment_pair_proposal.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
