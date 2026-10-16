"""Freeze the selected offline DC candidate with exact placement provenance."""
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
source=H/'placement_lower_over_smp_candidate.json'
expected='99a7cc8fef9c21e235f47fbdc24733121a37e6ddc4a939d6d92f4fbdb1d70c0e'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
original=json.loads(source.read_text())
plan=json.loads((H/'dc_routed_candidate.json').read_text())
assert plan['dc_routing_validation']['passed']
assert plan['dc_endpoint_bank_policy']=='Joint two-layer integral flow; one complete layer per net'
for key,fields,identity in [
    ('physical_pads',('x','y','sx','sy','rotation','hole','layer'),lambda d:(d['ref'],d['pin'],d['x'],d['y'])),
    ('vias',('x','y','diameter','hole','low','high'),lambda d:d['label']),
    ('components',('x','y','rotation'),lambda d:d['ref']),
]:
    lookup={identity(d):d for d in original[key]}
    assert len(plan[key])==len(original[key])
    for d in plan[key]:
        old=lookup[identity(d)]
        assert all(d.get(f)==old.get(f) for f in fields),(key,identity(d))
plan['dc_source_input_file']=str(source)
plan['dc_source_input_file_sha256']=expected
plan['dc_candidate_scope']='OFFLINE_DC_ROUTING_VERIFIED_PENDING_RF_MERGE_AND_NATIVE_VALIDATION'
plan['dc_body_exclusion_scope']='Full SMP five-pad hulls and resistor two-pad hulls on both internal routing layers; own resistor pad 2 entry only'
plan['dc_routing_selection']='Joint source-layer/contact-layer assignment selected after two fixed-bank comparisons'
output=json.dumps(plan,indent=2)
(H/'dc_routed_candidate.json').write_text(output)
(H/'dc_final_candidate.json').write_text(output)
print(hashlib.sha256((H/'dc_final_candidate.json').read_bytes()).hexdigest())
