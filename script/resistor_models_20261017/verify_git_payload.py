"""Check the staged native PCB and source-bound correction evidence."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def staged_bytes(path):
    return git('show', ':' + path)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def staged_json(path):
    return json.loads(staged_bytes(path))


board_dir = 'QSTL_QD4_2SET_38PAD/'
revisions = [
    ('RC_Mask_Margin_20261017', 'rc_mask_margin_20261017'),
    ('QD_Via_and_Cap_Models_20261017', 'qd_via_land_20261017'),
    ('Resistor_Models_20261017', 'resistor_models_20261017'),
]
prefixes = tuple(prefix for report, helper in revisions
                 for prefix in (board_dir + report + '/', 'script/' + helper + '/'))
exact = {'.gitattributes', 'QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md',
         board_dir + 'README.md', board_dir + 'QSTL_QD4_2SET_38PAD.PcbDoc'}
paths = git('diff', '--cached', '--name-only', '-z').decode().strip('\0').split('\0')
assert paths and all(p in exact or p.startswith(prefixes) for p in paths)
assert all(len(staged_bytes(p)) < 100 * 1024 * 1024 for p in paths)
for path in paths:
    if path.startswith(prefixes) or path.startswith(board_dir):
        assert sha(staged_bytes(path)) == sha((ROOT / path).read_bytes()), path

for report, helper in revisions:
    report_path = board_dir + report + '/'
    helper_path = 'script/' + helper + '/'
    status = staged_json(report_path + 'final_status.json')
    assert status['passed'] and status['DRC_violations'] == 0
    for name, evidence in status.get('audits', {}).items():
        data = staged_bytes(helper_path + name)
        assert sha(data) == evidence['sha256'], name
        assert json.loads(data)['passed'], name
    for name, digest in status.get('images', {}).items():
        assert sha(staged_bytes(report_path + name)) == digest, name
    if 'report_sha256' in status:
        assert sha(staged_bytes(report_path + 'IMPLEMENTATION_REPORT.md')) == status['report_sha256']

current = staged_json(board_dir + 'Resistor_Models_20261017/final_status.json')
pcb_sha = sha(staged_bytes(board_dir + 'QSTL_QD4_2SET_38PAD.PcbDoc'))
assert current['PCB_sha256'] == pcb_sha
assert current['stored_connections'] == 0 and current['RC_instances_checked'] == 32
audit_data = staged_bytes('script/resistor_models_20261017/audit.json')
assert sha(audit_data) == current['audit_sha256']
audit = json.loads(audit_data)
assert audit['passed'] and audit['source_sha256'] == pcb_sha
assert all(check['passed'] for check in audit['checks'])
assert sha(staged_bytes(board_dir + 'Resistor_Models_20261017/Altium_RC_Models_Corrected.png')) == current['photo_sha256']
print(json.dumps(dict(passed=True, staged_files=len(paths), PCB_sha256=pcb_sha,
                     DRC_violations=0, stored_connections=0,
                     saved_checks=len(audit['checks'])), indent=2))
