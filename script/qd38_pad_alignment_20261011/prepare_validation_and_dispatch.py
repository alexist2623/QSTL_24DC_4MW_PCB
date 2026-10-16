"""Stage validation in this namespace and dispatch only explicit guarded steps."""
from pathlib import Path
import hashlib,json,subprocess,sys
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OLD=ROOT/'script/qd38_rotation_20261011'
PCB=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
BASE='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    action=sys.argv[1]
    if action=='prepare':
        code=(OLD/'prepare_native_revision_validation.py').read_text()
        code=code.replace('ValidateQD90Revision','ValidateQDAlignment')
        exec(compile(code,str(H/'prepare_validation_isolated.py'),'exec'),{'__name__':'isolated_validation','__file__':str(H/'prepare_validation_isolated.py')})
        text=f'''Procedure ReopenQDAlignmentBaseline;
Var D:IServerDocument;
Begin
 D:=Client.OpenDocument('PCB','{PCB}');If D=Nil Then Exit;Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB','{PCB}');If D<>Nil Then Client.ShowDocument(D);
End;
'''
        (H/'ReopenQDAlignmentBaseline.pas').write_text(text,encoding='ascii')
        (H/'ReopenQDAlignmentBaseline.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=ReopenQDAlignmentBaseline.pas\n[Generic_ScriptingSystem]\nStartProcName=ReopenQDAlignmentBaseline.pas>ReopenQDAlignmentBaseline\n',encoding='ascii')
        stem='CloseAlignmentLibrary'
        lib=ROOT/'QSTL_QD4_2SET_38PAD/QD4_2SET_38.PcbLib'
        (H/f'{stem}.pas').write_text(f"Procedure {stem};\nVar D:IServerDocument;L:TStringList;\nBegin\nD:=Client.OpenDocument('PCBLIB','{lib}');If D<>Nil Then Client.CloseDocument(D);\nL:=TStringList.Create;L.Add('CLOSED');L.SaveToFile('{H/'library_closed.txt'}');L.Free;\nEnd;\n",encoding='ascii')
        (H/f'{stem}.PrjScr').write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
        return
    if action in ('ApplyQDPadAlignmentR1','ReopenQDAlignmentBaseline'):
        assert sha(PCB)==BASE,'Saved native baseline changed'
    if action=='ApplyQDPadAlignmentR1':
        m=json.loads((H/'native_alignment_preparation.json').read_text())
        assert action==m['script_stem'] and sha(H/f'{action}.pas')==m['script_sha256']
        assert sha(H/'alignment_full_candidate.json')==m['candidate_sha256']
        a=json.loads((H/'alignment_full_audit.json').read_text())
        assert a['passed'] and a['candidate_sha256']==m['candidate_sha256']
    if action=='ValidateQDAlignment':
        assert 'COMPLETE_NOT_SAVED' in (H/'native_alignment_delta.txt').read_text()
    allowed={'ApplyQDPadAlignmentR1','ReopenQDAlignmentBaseline','ValidateQDAlignment','ExportQD38PasteAlignment','CloseAlignmentLibrary'}
    assert action in allowed,action
    project=H/f'{action}.PrjScr';assert project.is_file()
    process=subprocess.Popen([r'F:\Altium\AD26\X2.EXE',f'-RScriptingSystem:RunScript(ProjectName={project}|ProcName={action}.pas>{action})'])
    print('DISPATCHED',action,'PID',process.pid,flush=True)
if __name__=='__main__':main()
