"""Preserve the verified native revision before any QD pad alignment change."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT/'QSTL_QD4_2SET_38PAD'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
pcb = DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
assert sha(pcb) == '1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
completion = ROOT/'script/qd38_rotation_20261011/revision_completion_audit.json'
assert json.loads(completion.read_text())['completion']
names = ['QSTL_QD4_2SET_38PAD.PcbDoc', 'QSTL_QD4_2SET_38PAD.SchDoc',
         'QSTL_QD4_2SET_38PAD.PrjPcb', 'QD4_2SET_38.PcbLib',
         'QSTL_QD4_2SET_38PAD.SchLib', 'circuit_plan.json',
         'full_copper_candidate.json', 'pin_mapping.csv', 'README.md']
out = HERE/'before_alignment'
out.mkdir(exist_ok=True)
entries = []
for name in names:
    source, backup = DEST/name, out/name
    if backup.exists():
        assert sha(source) == sha(backup), f'Backup differs: {name}'
    else:
        shutil.copy2(source, backup)
    entries.append(dict(source=str(source), backup=str(backup), sha256=sha(source)))
manifest = dict(status='VERIFIED_BASELINE_PRESERVED_NO_DESIGN_EDIT', files=entries,
                completion_evidence=str(completion), completion_sha256=sha(completion))
(out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
print(manifest['status'], len(entries))
