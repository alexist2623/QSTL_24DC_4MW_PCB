"""Promote audited companion sources into the existing authorized copy only.

The native PCB is changed separately through Altium, after guarded generation.
The project file and its existing source membership are preserved.
"""
import csv
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
NAME = DEST.name
STAGE = HERE / 'schematic_staging'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    candidate = HERE / 'full_copper_candidate.json'
    plan = json.loads(candidate.read_text())
    audit = json.loads((HERE / 'full_copper_audit.json').read_text())
    sch = json.loads((STAGE / 'schematic_validation.json').read_text())
    lib = json.loads((HERE / 'canonical_library_audit.json').read_text())
    assert plan['routing_complete'] and audit['passed'] and audit['candidate_sha256'] == sha(candidate)
    assert sch['nets'] == plan['nets'] and sch['schematic_sha256'] == sha(STAGE / (NAME + '.SchDoc'))
    assert lib['passed'] and lib['library_sha256'] == sha(STAGE / 'QD4_2SET_38.PcbLib') and lib['candidate_sha256'] == sha(candidate)
    assert sha(DEST / (NAME + '.PcbDoc')) == 'f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632'
    project = DEST / (NAME + '.PrjPcb')
    assert 'DocumentPath=QD4_2SET_38.PcbLib' in project.read_text()
    project_hash = sha(project)
    names = [NAME + '.SchDoc', NAME + '.SchLib', 'QD4_2SET_38.PcbLib', 'schematic_validation.json']
    changed = []
    for name in names:
        assert (HERE / 'before_rotation' / name).is_file(), ('Missing pre-revision backup', name)
        shutil.copy2(STAGE / name, DEST / name)
        changed.append(dict(name=name, sha256=sha(DEST / name)))
    for name in ('circuit_plan.json', 'full_copper_candidate.json'):
        shutil.copy2(candidate, DEST / name)
        changed.append(dict(name=name, sha256=sha(DEST / name)))
    rows = plan['pinmap']
    columns = list(dict.fromkeys(k for row in rows for k in row))
    with (DEST / 'pin_mapping.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    assert sha(project) == project_hash
    report = dict(status='COMPANION_SOURCES_PROMOTED_NATIVE_PCB_PENDING', candidate_sha256=sha(candidate), changed=changed,
                  project_unchanged_sha256=project_hash, native_PCB_changed=False)
    (HERE / 'source_promotion.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
