"""Promote only the independently reviewed pad-mask metadata delta."""
from pathlib import Path
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
DEST = H.parents[1] / 'QSTL_QD4_2SET_38PAD'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old_path = H / 'pre_mask_repair/full_copper_candidate.json'
new_path = H / 'full_copper_mask_repair_candidate.json'
old = json.loads(old_path.read_text())
new = json.loads(new_path.read_text())
report = json.loads((H / 'mask_sliver_repair_plan_audit.json').read_text())
assert report['passed'] and report['candidate_sha256'] == sha(new_path)
assert report['source_candidate_sha256'] == sha(old_path)
assert {k: v for k, v in new.items() if k not in ('pad_solder_mask_overrides', 'mask_sliver_repair')} == old
assert len(new['pad_solder_mask_overrides']) == 18
assert all(p['expansion_mm'] == .025 and p['ref'][0] in 'RC' for p in new['pad_solder_mask_overrides'])
promotion = json.loads((H / 'source_promotion.json').read_text())
assert promotion['candidate_sha256'] == sha(old_path)
assert promotion['project_unchanged_sha256'] == sha(DEST / (DEST.name + '.PrjPcb'))
for path in (H / 'full_copper_candidate.json', DEST / 'full_copper_candidate.json', DEST / 'circuit_plan.json'):
    assert sha(path) == sha(old_path)
    shutil.copy2(new_path, path)
promotion['candidate_sha256'] = sha(new_path)
promotion['mask_only_delta'] = report
promotion['status'] = 'COMPANION_SOURCES_PROMOTED_MASK_REPAIR_PENDING_NATIVE_AUDIT'
for item in promotion['changed']:
    path = DEST / item['name']
    if item['name'] in ('circuit_plan.json', 'full_copper_candidate.json'):
        item['sha256'] = sha(path)
    else:
        assert item['sha256'] == sha(path)
(H / 'source_promotion.json').write_text(json.dumps(promotion, indent=2))
print('Promoted mask-only candidate', sha(new_path))
