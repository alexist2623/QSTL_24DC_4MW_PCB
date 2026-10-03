{ Read the saved cable and run native design-rule checks. }
Procedure BuildFPC;
Var B:IPCB_Board;D:IServerDocument;P,Folder:String;L:TStringList;I:IPCB_BoardIterator;O:IPCB_Primitive;K:Integer;Good:Boolean;
Begin
 Folder:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_15015_0451\';P:=Folder+'FPC_15015_0451.PcbDoc';
 D:=Client.GetDocumentByPath(P);If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 L:=TStringList.Create;L.Add('REOPENED');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));I.AddFilter_Method(eProcessAll);O:=I.FirstPCBObject;K:=0;
 While O<>Nil Do Begin Inc(K);O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('UNROUTED_CONNECTIONS='+IntToStr(K));
 L.Add('SIGNAL_LAYER_COUNT='+IntToStr(B.LayerStack_V7.SignalLayerCount));
 Good:=B.RunBatchDesignRuleCheck(Folder+'Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 B.GraphicalView_ZoomOnRect(MMsToCoord(-2),MMsToCoord(-5),MMsToCoord(104),MMsToCoord(21));
 L.Add('COMPLETE');L.SaveToFile(Folder+'native_validation.txt');L.Free;
End;
