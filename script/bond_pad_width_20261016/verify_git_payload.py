"""Verify the staged native file and source-bound evidence before publishing."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
staged=git('diff','--cached','--name-only','-z').decode().strip('\0').split('\0')
prefixes=('QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/','QSTL_QD4_2SET_38PAD/Compact_Masks_20261016/','QSTL_QD4_2SET_38PAD/RF_Entry_Correction_20261016/','QSTL_QD4_2SET_38PAD/SMP_Rounded_Entries_20261016/','script/bond_pad_width_20261016/','script/compact_masks_20261016/','script/rf_entry_shield_fix_20261016/','script/smp_broad_rounding_20261016/')
exact={'.gitattributes','QSTL_24DC_4MW_PCB/docs/DESIGN_REQUIREMENTS.md','QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD/README.md'}
assert staged and all(p in exact or p.startswith(prefixes) for p in staged),'Unexpected staged scope'
sha=lambda b:hashlib.sha256(b).hexdigest()
path='QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
pcb_sha=sha(git('show',':'+path));assert pcb_sha==sha((ROOT/path).read_bytes())
status=json.loads(git('show',':QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/final_status.json'))
assert status['passed'] and status['PCB_sha256']==pcb_sha and status['DRC_violations']==0
for name,evidence in status['audits'].items():
    data=git('show',':script/bond_pad_width_20261016/'+name)
    assert sha(data)==evidence['sha256'],name
    audit=json.loads(data);assert audit['passed'],name
    audit_source=audit['source_sha256'] if 'source_sha256' in audit else audit['checks']['native_sha256']
    assert audit_source==pcb_sha,name
for name,digest in status['images'].items():
    assert sha(git('show',':QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/'+name))==digest,name
assert sha(git('show',':QSTL_QD4_2SET_38PAD/Bond_Pad_Width_20261017/IMPLEMENTATION_REPORT.md'))==status['report_sha256']
print(json.dumps(dict(passed=True,staged_file_count=len(staged),PCB_sha256=pcb_sha,DRC_violations=0,verified_audits=len(status['audits']),verified_images=len(status['images'])),indent=2))
