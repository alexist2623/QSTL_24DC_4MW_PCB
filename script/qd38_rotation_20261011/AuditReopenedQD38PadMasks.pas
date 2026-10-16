Var B:IPCB_Board;L:TStringList;P:IPCB_Pad;C:TPadCache;I:IPCB_BoardIterator;N:Integer;Good:Boolean;
 Targets:Array[0..17] Of IPCB_Pad;

Procedure DumpPads(S:String;Path:String);
Var I:IPCB_BoardIterator;P:IPCB_Pad;C:TPadCache;RefName,Enabled:String;L:TStringList;Count:Integer;
Begin
 L:=TStringList.Create;L.Add('STAGE='+S);L.Add('BOARD='+B.FileName);L.Add('CANDIDATE_SHA256=835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495');Count:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  Inc(Count);RefName:='MOUNT';If P.Component<>Nil Then RefName:=P.Component.Name.Text;
  C:=P.GetState_Cache;Enabled:='0';If P.GetState_PasteMaskEnabled Then Enabled:='1';
  L.Add('PAD='+RefName+'|'+P.Name+'|'+IntToStr(P.X)+'|'+IntToStr(P.Y)+'|'+IntToStr(C.SolderMaskExpansion)+'|'+IntToStr(C.SolderMaskBottomExpansion)+'|'+IntToStr(C.PasteMaskExpansion)+'|'+Enabled);
  P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);L.Add('PAD_COUNT='+IntToStr(Count));L.Add('COMPLETE');L.SaveToFile(Path);L.Free;
End;

Function FindPad(RefName,Pin:String;X,Y:Double):IPCB_Pad;
Var J:IPCB_BoardIterator;P:IPCB_Pad;Count:Integer;
Begin Result:=Nil;Count:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(ePadObject));P:=J.FirstPCBObject;
 While P<>Nil Do Begin
  If P.Component<>Nil Then If (P.Component.Name.Text=RefName) And (P.Name=Pin) Then Begin
   Inc(Count);If (Abs(CoordToMMs(P.X)-X)<0.00001) And (Abs(CoordToMMs(P.Y)-Y)<0.00001) And (P.Layer=eBottomLayer) Then Result:=P;
  End;P:=J.NextPCBObject;
 End;B.BoardIterator_Destroy(J);If Count<>1 Then Result:=Nil;
End;

Procedure AuditReopenedQD38PadMasks;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 DumpPads('AFTER_REOPEN','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_mask_after_reopen.txt');
End;
