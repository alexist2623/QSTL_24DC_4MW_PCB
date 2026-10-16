"""Reroute joint-selected layer banks without inactive-layer stub keepouts.

Every physical plated land remains an obstacle on both planes. Only the
selected source/contact escape stubs occupy a particular plane. This second
pass retains the joint solution's complete-net layer assignments and contact
banks, but can remap source-to-contact correspondence within each bank.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.argv=[sys.argv[0],'.23','.115','.115','--pooled','--central']
import route_dc_rotated as route

H=Path(__file__).resolve().parent
SOURCE=H/'dc_staggered_candidate.json'
EXPECTED='2fc778d0f2b04e225715bb9f45fdcd696f2d97e8b69f7511c8bb0e6b8fcfe613'


def main():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
    plan=json.loads(SOURCE.read_text())
    assert plan['dc_routing_validation']['passed']
    assert len(plan['vias'])==76
    assert all(v['low']==1 and v['high']==32 for v in plan['vias'])
    plan['dc_selected_layer_second_pass']=dict(
        source=str(SOURCE),source_sha256=EXPECTED,
        physical_via_lands_on_both_layers=True,
        inactive_layer_escape_stubs_blocked=False,
        source_layer_assignment_preserved=True,
        selected_contact_layer_banks_preserved=True,
        within_layer_contact_remapping_permitted=True,
    )
    plan['dc_endpoint_bank_policy']='Joint-selected source/contact layer banks; second pass reserves only selected-layer escape stubs'
    results=[]
    for layer in (2,4):
        sources=[v for v in plan['vias'] if not v['label'].startswith('J1-') and v['assigned_dc_layer']==layer]
        ports=[v for v in plan['vias'] if v['label'].startswith('J1-') and v['assigned_dc_layer']==layer]
        assert len(sources)==len(ports)
        print('SELECTED_LAYER_BANK',layer,len(sources),[v['label'] for v in ports],flush=True)
        result=route.run_layer(plan,layer)
        results.append(result)
        (H/f'dc_selected_layer_stagger_L{layer}_flow.json').write_text(json.dumps(result,indent=2))
    passed=all(not r.get('failure') and not r.get('clearance_failures') for r in results)
    report=dict(passed=passed,source_candidate_sha256=EXPECTED,layers=results)
    (H/'dc_selected_layer_stagger_flow.json').write_text(json.dumps(report,indent=2))
    print('SELECTED_LAYER_FLOW_PASSED',passed,flush=True)
    if not passed:
        return
    route.finalize(plan,results)


if __name__=='__main__':
    main()
