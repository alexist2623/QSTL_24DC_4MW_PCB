"""Freeze and document the limited J1-via stagger without changing other geometry."""
import hashlib
import json
import sys
from pathlib import Path

H=Path(__file__).resolve().parent
output_name=sys.argv[1] if len(sys.argv)>1 else 'dc_staggered_candidate.json'
assert Path(output_name).name==output_name and output_name.endswith('_candidate.json')
assert not (H/output_name).exists(), 'Preserve previously frozen candidates'
source=H/'placement_lower_over_smp_candidate.json'
baseline=H/'dc_final_candidate.json'
source_hash='99a7cc8fef9c21e235f47fbdc24733121a37e6ddc4a939d6d92f4fbdb1d70c0e'
baseline_hash='eefbfe8ff5a56f85c61db86a75646cf87397af0d012d526a2af8694ae3d064ca'
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==baseline_hash
original=json.loads(source.read_text())
plan=json.loads((H/'dc_routed_candidate.json').read_text())
assert plan['dc_routing_validation']['passed']
assert plan['j1_stagger_revision']['static_passed']
assert len(plan['vias'])==len(original['vias'])==76
for key,fields,identity in [
    ('physical_pads',('x','y','sx','sy','rotation','hole','layer'),lambda d:(d['ref'],d['pin'],d['x'],d['y'])),
    ('components',('x','y','rotation'),lambda d:d['ref']),
]:
    lookup={identity(d):d for d in original[key]}
    assert len(plan[key])==len(original[key])
    for d in plan[key]:
        old=lookup[identity(d)]
        assert all(d.get(f)==old.get(f) for f in fields),(key,identity(d))
lookup={v['label']:v for v in original['vias']}
changed=[]
for v in plan['vias']:
    old=lookup[v['label']]
    assert all(v[f]==old[f] for f in ['x','diameter','hole','low','high'])
    expected_move=v['label'].startswith('J1-') and int(v['label'].split('-')[1])%4==0
    delta=v['y']-old['y']
    assert abs(delta-(.7 if expected_move else 0))<1e-8,v['label']
    if expected_move:changed.append(v['label'])
assert len(changed)==12
plan['dc_source_input_file']=str(H/'dc_joint_stagger_input_candidate.json')
plan['dc_source_input_file_sha256']=hashlib.sha256((H/'dc_joint_stagger_input_candidate.json').read_bytes()).hexdigest()
plan['dc_base_placement_file_sha256']=source_hash
plan['dc_fallback_candidate_sha256']=baseline_hash
plan['dc_candidate_scope']='OFFLINE_J1_STAGGER_DC_ROUTING_VERIFIED_PENDING_RF_MERGE_AND_NATIVE_VALIDATION'
plan['dc_body_exclusion_scope']='Full SMP five-pad hulls and resistor two-pad hulls on both internal routing layers; own resistor pad 2 entry only'
plan['dc_routing_selection']='One authorized joint-layer solve using twelve alternating even J1 endpoint vias shifted +0.70 mm Y'
if plan.get('dc_selected_layer_second_pass'):
    plan['dc_routing_selection']='Joint-selected source/contact layer banks; second pass reserves only selected-layer escape stubs while preserving all actual via lands on both internal layers'
output=json.dumps(plan,indent=2)
(H/output_name).write_text(output)
(H/'dc_routed_candidate.json').write_text(output)
print(hashlib.sha256((H/output_name).read_bytes()).hexdigest())
