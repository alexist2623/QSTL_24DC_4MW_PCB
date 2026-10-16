"""Resolve this checkout, repair copied-project references, and prepare a fresh probe."""
from pathlib import Path, PureWindowsPath
from datetime import datetime,timezone
import hashlib
import json
import re
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
NAME='QSTL_QD4_2SET_38PAD'
project=DEST/(NAME+'.PrjPcb')
gitroot=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ROOT,text=True).strip()).resolve()
assert gitroot==ROOT
provenance=json.loads((DEST/'copy_provenance.json').read_text())
def source_hashes():
    return {name:hashlib.sha256((Path(provenance['source'])/name).read_bytes()).hexdigest()
            for name in provenance['source_sha256']}
before=source_hashes()
text=project.read_text()
backup=HERE/'before_path_repair.PrjPcb'
if not backup.exists():shutil.copy2(project,backup)
changes=[]
def fix(match):
    value=match.group(1)
    if not PureWindowsPath(value).is_absolute():return match.group(0)
    filename=PureWindowsPath(value).name
    for suffix in ('.PcbDoc','.SchDoc','.PrjPcb'):
        if filename=='QSTL_24DC_4MW_PCB'+suffix:filename=NAME+suffix
    destination=DEST/filename
    if not destination.is_file():return match.group(0)
    new=str(destination)
    if new!=value:changes.append(dict(before=value,after=new))
    return 'DocumentPath='+new
text=re.sub(r'DocumentPath=([^|\r\n]+)',fix,text)
if changes:project.write_text(text)
documents=[]
for value in re.findall(r'^DocumentPath=(.+)$',text,re.M):
    path=Path(value.strip())
    resolved=path if path.is_absolute() else DEST/path
    documents.append(dict(path=value.strip(),exists=resolved.is_file(),resolved=str(resolved.resolve())))
assert all(d['exists'] for d in documents),documents
stale=[s for s in text.splitlines() if re.search(r'DocumentPath=C:\\(?:JeonghyunPark|Users\\)',s,re.I)]
assert not stale,stale
log=str(HERE/'probe_native_fixed.txt')
pcb=str(DEST/(NAME+'.PcbDoc'))
code=f'''Var L:TStringList;
Procedure Mark(S:String);Begin L.Add(S);L.SaveToFile('{log}');End;
Procedure ProbeNativeFixed;
Var W:IWorkspace;P:IProject;D:IServerDocument;B:IPCB_Board;
    I:IPCB_BoardIterator;O:IPCB_Primitive;N:Integer;
Begin
 L:=TStringList.Create;Mark('START_FIXED_TWO_ARGUMENTS');
 W:=GetWorkspace;If W=Nil Then Begin Mark('NO_WORKSPACE');Exit;End;
 Mark('WORKSPACE_OK');
 P:=W.DM_OpenProject('{project}',True);
 If P=Nil Then Begin Mark('NO_PROJECT');Exit;End;
 Mark('PROJECT_OPEN_OK');
 D:=Client.OpenDocument('PCB','{pcb}');
 If D=Nil Then Begin Mark('NO_PCB_DOCUMENT');Exit;End;
 Mark('PCB_OPEN_OK');Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Begin Mark('NO_BOARD');Exit;End;
 Mark('BOARD='+B.FileName);N:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin Inc(N);O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('COMPONENTS='+IntToStr(N));Mark('COMPLETE');L.Free;
End;
'''
(HERE/'ProbeNativeFixed.pas').write_text(code,encoding='ascii')
(HERE/'ProbeNativeFixed.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=ProbeNativeFixed.pas\n[Generic_ScriptingSystem]\nStartProcName=ProbeNativeFixed.pas>ProbeNativeFixed\n')
assert source_hashes()==before==provenance['source_sha256']
result=dict(checked_at_utc=datetime.now(timezone.utc).isoformat(),git_root=str(gitroot),helper_root=str(HERE),
            project=str(project),documents=documents,changed_absolute_document_references=changes,
            source_files_preserved=True,api_repair='DM_OpenProject(ProjectPath, True)',
            api_documentation='https://www.altium.com/documentation/altium-dxp-developer/workspace-manager-api',
            native_runtime_retest='PENDING')
(HERE/'path_and_api_diagnostic.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(git_root=str(gitroot),project=str(project),documents_checked=len(documents),
                     repaired_references=len(changes),source_files_preserved=True,
                     api_repair=result['api_repair']),indent=2))
