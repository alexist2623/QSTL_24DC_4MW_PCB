Procedure ProbeMaskPresence;
Var B:IPCB_Board;I:IPCB_BoardIterator;V:IPCB_Via;T:IPCB_Track;L:TStringList;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 L:=TStringList.Create;N:=0;
 T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 Try
  While V<>Nil Do Begin
   T.Layer:=eTopPaste;
   If V.HasMaskExpansion(T.V7Layer) Then L.Add('TOP|'+IntToStr(N)+'|1') Else L.Add('TOP|'+IntToStr(N)+'|0');
   T.Layer:=eBottomPaste;
   If V.HasMaskExpansion(T.V7Layer) Then L.Add('BOTTOM|'+IntToStr(N)+'|1') Else L.Add('BOTTOM|'+IntToStr(N)+'|0');
   Inc(N);V:=I.NextPCBObject;
  End;
  L.Add('COMPLETE');
 Except L.Add('API_FAILED');End;
 B.BoardIterator_Destroy(I);
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\mask_ground_20260920\native_via_paste_presence.txt');L.Free;
End;
