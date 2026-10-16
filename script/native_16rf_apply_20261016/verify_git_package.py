"""Validate the staged native project, evidence hashes and publication scope."""
from pathlib import Path
import subprocess,json,hashlib,configparser,re,collections
H=Path(__file__).resolve().parent;R=H.parents[1];D='QSTL_QD4_2SET_38PAD'
def git(*args):return subprocess.check_output(['git',*args],cwd=R)
names=[p.decode('utf-8') for p in git('diff','--cached','--name-only','-z').split(b'\0') if p]
rows=[];issues=[];size_total=0
for p in names:
    path=R/p;size=path.stat().st_size;size_total+=size
    if size>95*1024**2:issues.append(['oversized',p,size])
    if any(x in Path(p).parts for x in ('.venv','__pycache__','.codex-remote-attachments','History')):issues.append(['unexpected_local_data',p])
    rows.append((size,p))
status=json.loads((R/D/'Native_Applied_20261016/final_status.json').read_text())
for name,key in ((D+'.PcbDoc','PCB_sha256'),(D+'.SchDoc','schematic_sha256'),('pin_mapping.csv','pin_map_sha256')):
    content=git('show',':'+D+'/'+name)
    if hashlib.sha256(content).hexdigest()!=status[key]:issues.append(['staged_native_hash',name])
cfg=configparser.ConfigParser(interpolation=None,strict=False);cfg.read_string(git('show',':'+D+'/'+D+'.PrjPcb').decode('utf-8-sig'))
docs=[]
for sec in cfg.sections():
    if not sec.startswith('Document'):continue
    name=cfg.get(sec,'DocumentPath',fallback='')
    if not name:continue
    path=D+'/'+name.replace('\\','/');git('cat-file','-e',':'+path);docs.append(path)
for filename,expected in status['audit_sha256'].items():
    data=git('show',':script/native_16rf_apply_20261016/'+filename+'.json')
    if hashlib.sha256(data).hexdigest()!=expected:issues.append(['staged_evidence_hash',filename])
# Report paths only for possible embedded credentials; never print matched text.
patterns=[rb'gh[pousr]_[A-Za-z0-9]{30,}',rb'github_pat_[A-Za-z0-9_]{40,}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
for _,p in rows:
    if Path(p).suffix.lower() not in ('.py','.ps1','.md','.txt','.json','.pas','.csv','.prjpcb'):continue
    raw=(R/p).read_bytes()
    if any(re.search(pat,raw) for pat in patterns):issues.append(['possible_credential',p])
report=dict(passed=not issues,issues=issues,files=len(names),MB=round(size_total/1024**2,2),largest=[dict(MB=round(n/1024**2,2),path=p) for n,p in sorted(rows,reverse=True)[:12]],project_document_count=len(docs),verified_PCB_sha256=status['PCB_sha256'])
(H/'git_package_verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert not issues
