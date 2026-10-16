Procedure FixQD38Models;
Var B:IPCB_Board;I:IPCB_BoardIterator;Body:IPCB_ComponentBody;C:IPCB_Component;
    M:IPCB_Model;Pt:TCoordPoint;L:TStringList;Count:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;Count:=0;PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
  While Body<>Nil Do Begin
   C:=Body.Component;
   If C<>Nil Then If Copy(C.Name.Text,1,3)='SMP' Then Begin
    M:=Body.GetModel;M:=M.I_Replicate;Pt:=M.GetOrigin;Pt.X:=C.X;Pt.Y:=C.Y;M.SetOrigin(Pt);
    { Preserve the source SMP STEP basis and vertical datum in native units. }
    M.SetState(90,0,C.Rotation,236220);M.SetEmbed(True);Body.SetModel(M);Body.SetState_FromModel;
    Body.SetBodyProjection(eBoardSide_Top);Body.SetStandoffHeight(-1263780);Body.SetOverallHeight(2125984);Body.ValidateMesh;
    L.Add('FIXED|'+C.Name.Text);Inc(Count);
   End;Body:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 L.Add('COUNT='+IntToStr(Count));L.Add('COMPLETE_NOT_SAVED');
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_model_fix.txt');L.Free;
End;
