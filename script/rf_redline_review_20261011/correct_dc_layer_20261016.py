"""Apply the user's L3/L4 exchange to the saved offline DC proposal."""
import hashlib
import json
from collections import Counter
import dc_shielded_plan_20261016 as dc

def geometry_digest(routes):
    value=[{k:v for k,v in r.items() if k!='layer'} for r in routes]
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def main():
    folder=dc.OUT
    path=folder/'dc_routed_plan.json'
    before=json.loads(path.read_text())
    digest=geometry_digest(before['routes'])
    original_counts=dict(Counter(str(r['layer']) for r in before['routes']))
    names=['dc_input.json','dc_routed_plan.json','raw_dc_routes.json','raw_L2.json','simplified_checkpoint.json']
    if (folder/'raw_L4.json').exists():names.append('raw_L4.json')
    elif (folder/'raw_L3.json').exists():names.append('raw_L3.json')
    for name in names:
        p=folder/name
        if not p.exists():continue
        obj=json.loads(p.read_text())
        routes=obj if isinstance(obj,list) else obj.get('routes',[])
        for r in routes:
            assert r['layer'] in (2,3,4)
            if r['layer']==4:r['layer']=3
        if isinstance(obj,dict):
            obj['planned_layer_roles']=dc.LAYER_ROLES
            obj['layer_assignment_note']='User L3/L4 exchange: L2/L3 DC, L4 GND. Native source mapping remains historical.'
        p.write_text(json.dumps(obj,indent=2),encoding='utf-8')
        if name=='raw_L4.json':
            target=folder/'raw_L3.json'
            assert not target.exists(),target
            p.rename(target)
    after=json.loads(path.read_text())
    assert geometry_digest(after['routes'])==digest
    assert Counter(r['layer'] for r in after['routes'])=={2:19,3:19}
    assert before['mapping']==after['mapping']
    assert before['vias']==after['vias']
    assert before['top_fanout']==after['top_fanout']
    report=dict(passed=True,before_layer_counts=original_counts,after_layer_counts={'2':19,'3':19},
        planned_layer_roles=dc.LAYER_ROLES,route_geometry_and_contacts_SHA256=digest,
        route_XY_width_endpoints_contacts_unchanged=True,terminal_vias_unchanged=True,
        Top_ZIF_fanout_unchanged=True,native_PCB_and_schematic_updated=False)
    dc.save('layer_correction_audit.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
