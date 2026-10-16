"""Record completed native validation without changing copper or schematic data."""
from pathlib import Path
import sys,json,hashlib,shutil
H=Path(__file__).resolve().parent;ROOT=H.parents[1];D=ROOT/'QSTL_QD4_2SET_38PAD';N='QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from prepare_native_revision_rules import read_rules
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=sha(D/(N+'.PcbDoc'));reports={}
for name in ('saved_native_audit','support_audit','route_identity_audit','central_saved_audit'):
    r=json.loads((H/(name+'.json')).read_text());assert r['passed'],name;reports[name]=sha(H/(name+'.json'))
    if 'source_sha256' in r:assert r['source_sha256']==digest
assert json.loads((H/'saved_native_audit.json').read_text())['checks']['native_sha256']==digest
drc=json.loads((H/'drc_rows.json').read_text());assert any(r[0]=='Rule Violations:' and r[-1]=='0' for r in drc)
rules=read_rules(D/(N+'.PcbDoc'));oldrules=read_rules(H/'before_dc_centralization'/(N+'.PcbDoc'))
assert rules==oldrules,'Rules changed during DC centralization'
enabled={n:r.get('DRCENABLED') for n,r in rules.items()}
status=dict(status='Native centralization complete; saved/reopened and verified',PCB_sha256=digest,schematic_sha256=sha(D/(N+'.SchDoc')),pin_map_sha256=sha(D/'pin_mapping.csv'),audit_sha256=reports,native_DRC_violations=0,rule_count=len(rules),rules_unchanged_during_centralization=True,rule_enabled_states=enabled,production_Gerbers_issued=False)
sch=json.loads((D/'schematic_validation.json').read_text());assert sch['schematic_sha256']==status['schematic_sha256']
sch['status']='Saved synchronized schematic; native compiled membership and zero enumerated violations verified.'
(D/'schematic_validation.json').write_text(json.dumps(sch,indent=2))
(H/'final_status.json').write_text(json.dumps(status,indent=2));shutil.copy2(H/'final_status.json',D/'Native_Applied_20261016/final_status.json')
print(json.dumps({k:v for k,v in status.items() if k not in ('rule_enabled_states','audit_sha256')},indent=2))
