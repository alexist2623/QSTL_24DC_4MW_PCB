"""Freeze the verified C13 revision and reuse the repository's native toolchain."""
from pathlib import Path
import shutil,hashlib,json
import numpy as np
H=Path(__file__).resolve().parent;ROOT=H.parents[1];OLD=ROOT/'script/rf_entry_shield_fix_20261016';P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
B=H/'baseline';B.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/(N+'.PcbDoc'))=='8b8002cfa465c2b7ff8a1c57299817a78393ef0a3739fe9d5962aed1a692bdd5'
for source in [P/(N+'.PcbDoc'),P/(N+'.SchDoc'),P/'pin_mapping.csv']+[OLD/k for k in ('candidate.json','entry_routes.json','shield_records.json')]:
    dest=B/source.name
    if not dest.exists():shutil.copy2(source,dest)
    assert sha(source)==sha(dest),source
for fn in ('build_revision.py','preflight.py','prepare_native.py','audit_saved.py','audit_support.py','audit_preservation.py','audit_route_identity.py','dispatch.py','RecalculateConnections.pas','RecalculateConnections.PrjScr'):
    path=H/fn
    if not path.exists():path.write_text((OLD/fn).read_text().replace(str(OLD),str(H)))
for fn in ('entry_routes.json',):
    if not (H/fn).exists():shutil.copy2(B/fn,H/fn)
paste=H/'paste_verification';paste.mkdir(exist_ok=True)
outjob='Cap_Paste_Verification.OutJob'
(paste/outjob).write_text((OLD/'paste_verification'/outjob).read_text().replace(str(OLD),str(H)))
groups=json.loads((B/'entry_routes.json').read_text())['groups']
for g in groups:
    pp=np.array(g['smp_to_c1']);u=(pp[1]-pp[0]);u/=np.linalg.norm(u);v=pp[-1]-pp[-2];v/=np.linalg.norm(v)
    a,b=pp[0],pp[-1];mat=np.column_stack((u,v));det=np.linalg.det(mat)
    lens=None if abs(det)<1e-7 else np.linalg.solve(mat,b-a).tolist()
    print(g['row']['smp'], 'C1',a.tolist(),'SMP',b.tolist(),'start/end angle',np.rad2deg(np.arctan2(u[1],u[0])),np.rad2deg(np.arctan2(v[1],v[0])),'intersection legs',lens)
print('Backup complete',B)
