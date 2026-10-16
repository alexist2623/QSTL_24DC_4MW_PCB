"""Rebuild native net connectivity, preserving the first-save discrepancy."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
PCB=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
EXPECTED='41df921a11093a92c8e40b77fc0b17f458640c8e5a15582b986bbffba9dd1573'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert sys.argv[1]=='run' and sha(PCB)==EXPECTED
    dest=H/'first_save_connection_cache';dest.mkdir(exist_ok=True)
    paths=[PCB]+[H/n for n in ('native_validation.txt','native_compile.txt','Native_DRC.html','saved_revision_audit.json','saved_revision_snapshot.json','alignment_audit_copper.txt')]
    records=[]
    for src in paths:
        if not src.exists():continue
        target=dest/src.name
        if target.exists():assert sha(src)==sha(target)
        else:shutil.copy2(src,target)
        records.append(dict(path=str(target),sha256=sha(target)))
    (dest/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
    stem='RebuildQDAlignmentConnections'
    code=f'''Procedure {stem};
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;N:IPCB_Net;P:IPCB_Primitive;L:TStringList;Count:Integer;
Begin
 D:=Client.OpenDocument('PCB','{PCB}');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{PCB}') Then Exit;
 L:=TStringList.Create;L.Add('BOUND_SAVED_SHA256={EXPECTED}');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;L.Add('REBUILT='+N.Name);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('CONNECTION_COUNT_AFTER_REBUILD='+IntToStr(Count));
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;L.Add('COMPLETE_NOT_SAVED');L.SaveToFile('{H/'native_connectivity_rebuild.txt'}');L.Free;
End;
'''
    (H/f'{stem}.pas').write_text(code,encoding='ascii')
    prj=H/f'{stem}.PrjScr';prj.write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
    proc=subprocess.Popen([r'F:\Altium\AD26\X2.EXE',f'-RScriptingSystem:RunScript(ProjectName={prj}|ProcName={stem}.pas>{stem})'])
    print('Dispatched net rebuild only:',proc.pid)
if __name__=='__main__':main()
