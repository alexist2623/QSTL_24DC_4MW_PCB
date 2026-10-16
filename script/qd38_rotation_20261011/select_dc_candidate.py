"""Record the practical DC selection while preserving all audited trials."""
import hashlib
import json
from pathlib import Path

H = Path(__file__).resolve().parent
choices = [
    ('dc_final_candidate.json', 'dc_fallback_rechecked_independent_audit.json'),
    ('dc_staggered_candidate.json', 'dc_staggered_independent_audit.json'),
    ('dc_two_pass_staggered_candidate.json', 'dc_two_pass_staggered_independent_audit.json'),
]
metrics = ['total_bends', 'maximum_bends', 'total_dc_length_mm',
           'length_weighted_mean_absolute_x_offset_mm', 'actual_minimum_dc_to_dc_mm',
           'actual_minimum_dc_to_ground_mm', 'minimum_rc_body_envelope_clearance_mm',
           'minimum_smp_full_hull_clearance_mm', 'top_fanout_minimum_clearance_mm']
comparison = []
for filename, auditname in choices:
    path = H / filename
    audit = json.loads((H / auditname).read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert audit['passed'] and audit['candidate_sha256'] == digest
    comparison.append(dict(file=filename, sha256=digest, passed=True,
                           metrics={key: audit[key] for key in metrics}))
chosen = H / 'dc_final_candidate.json'
plan = json.loads(chosen.read_text())
assert plan['dc_routing_validation']['passed']
assert comparison[0]['sha256'] == 'eefbfe8ff5a56f85c61db86a75646cf87397af0d012d526a2af8694ae3d064ca'
report = dict(
    selected_file=str(chosen), selected_sha256=comparison[0]['sha256'],
    reason='Retain the simpler 345-bend route (maximum 15 per net). The corrected selected-layer-stub stagger trial improves mean centreline distance by only 0.124 mm and total length by 19.951 mm, while adding 36 bends and raising the maximum to 20. Both pass exact geometry audits; the modest centrality gain does not justify the additional route complexity.',
    inactive_layer_stubs_investigated=True,
    selected_layer_only_second_pass_passed=True,
    selection_is_global_optimum_claim=False,
    candidates=comparison,
    native_design_modified=False,
)
(H / 'dc_routed_candidate.json').write_bytes(chosen.read_bytes())
(H / 'dc_audit.json').write_text(json.dumps(plan['dc_routing_validation'], indent=2))
(H / 'dc_selection_report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
