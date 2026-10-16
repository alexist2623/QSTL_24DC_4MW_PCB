Procedure FixSMPBodySide;
Var B:IPCB_Board;I:IPCB_BoardIterator;Body:IPCB_ComponentBody;L:TStringList;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;N:=0;
 PCBServer.PreProcess;Try
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
 While Body<>Nil Do Begin
  If Body.Component<>Nil Then If Copy(Body.Component.Name.Text,1,3)='SMP' Then Begin
   Body.SetBodyProjection(eBoardSide_Top);Body.ValidateMesh;Inc(N);L.Add(Body.Component.Name.Text);
  End;Body:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 L.Add('MODEL_COUNT='+IntToStr(N));L.Add('COMPLETE_NOT_SAVED');
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\native_16rf_apply_20261016\smp_body_fix.txt');L.Free;
End;
