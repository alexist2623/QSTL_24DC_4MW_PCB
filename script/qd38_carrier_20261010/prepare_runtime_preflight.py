"""Prepare read-only native model inspection and schematic compilation."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
source = (ROOT/'script/branch_linear_proposal_20261006/VerifyLinearOutline.pas').read_text()
compile_code = source.split('Procedure CompileProject(', 1)[1].split('Procedure VerifyLinearOutline;', 1)[0]
compile_code = 'Procedure CompileProject(' + compile_code
code = r'''
Procedure InspectModels;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Primitive;C:IPCB_Component;
    Body:IPCB_ComponentBody;M:IPCB_Model;Pt:TCoordPoint;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Exit;
 L:=TStringList.Create;L.Add('BOARD|'+B.FileName);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  C:=P.Component;
  If C<>Nil Then Begin
   Body:=P;M:=Body.GetModel;
   If M<>Nil Then Begin Pt:=M.GetOrigin;L.Add('MODEL|'+C.Name.Text+'|'+FloatToStr(CoordToMMs(Pt.X))+'|'+FloatToStr(CoordToMMs(Pt.Y)));End;
  End;P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile('__HERE__\native_models.txt');L.Free;
End;
'''
code += compile_code
code += r'''
Procedure RuntimePreflight;
Var D:IServerDocument;
Begin
 InspectModels;
 D:=Client.OpenDocument('SCH','__SCH__');If D<>Nil Then Client.ShowDocument(D);
 CompileProject('__PROJECT__','__HERE__\');
End;
'''
for old,new in {'__HERE__':HERE,'__PCB__':DEST/'QSTL_QD4_2SET_38PAD.PcbDoc',
                '__SCH__':DEST/'QSTL_QD4_2SET_38PAD.SchDoc',
                '__PROJECT__':DEST/'QSTL_QD4_2SET_38PAD.PrjPcb'}.items():
    code=code.replace(old,str(new))
(HERE/'RuntimePreflight.pas').write_text(code,encoding='ascii')
(HERE/'RuntimePreflight.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=RuntimePreflight.pas\n[Generic_ScriptingSystem]\nStartProcName=RuntimePreflight.pas>RuntimePreflight\n')
print('Prepared read-only model and schematic checks.')
