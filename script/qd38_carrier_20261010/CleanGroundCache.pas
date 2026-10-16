Procedure CleanGroundCache;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;N:IPCB_Net;L:TStringList;
Begin
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin
  If N.Name='GND' Then Begin N.ConnectivelyInValidate;B.AnalyzeNet(N);B.CleanNet(N);L.Add('GND_ANALYZED_AND_CLEANED');End;
  N:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_ground_cache.txt');L.Free;
End;
