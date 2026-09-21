Var ConnLog:TStringList;ConnPath:String;
Procedure MarkConn(S:String);Begin ConnLog.Add(S);ConnLog.SaveToFile(ConnPath+'work\connection_reopen_check.txt');End;
Procedure CountConnections(B:IPCB_Board;Stage:String);
Var I:IPCB_BoardIterator;C:IPCB_Connection;N:Integer;Name:String;
Begin
 N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));I.AddFilter_Method(eProcessAll);C:=I.FirstPCBObject;
 While C<>Nil Do Begin
  Inc(N);Name:='';If C.Net<>Nil Then Name:=C.Net.Name;
  MarkConn(Stage+'|'+Name+'|'+IntToStr(C.X1)+','+IntToStr(C.Y1)+'|'+IntToStr(C.X2)+','+IntToStr(C.Y2));
  C:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkConn(Stage+'_COUNT='+IntToStr(N));
End;

Procedure ReopenAudit;
Var B:IPCB_Board;D:IServerDocument;P:String;Good:Boolean;
Begin
 ConnPath:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\';P:=ConnPath+'QSTL_24DC_4MW_PCB.PcbDoc';
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 D:=Client.GetDocumentByPath(P);If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 ConnLog:=TStringList.Create;MarkConn('REOPENED');CountConnections(B,'AFTER_REOPEN');
 Good:=B.RunBatchDesignRuleCheck(ConnPath+'docs\Connections_DRC.html',eDRC_HTML,False,False);
 If Good Then MarkConn('DRC_RETURNED_TRUE') Else MarkConn('DRC_RETURNED_FALSE');
 CountConnections(B,'AFTER_DRC');B.GraphicalView_ZoomOnRect(MMsToCoord(3),MMsToCoord(25),MMsToCoord(19),MMsToCoord(50));
 MarkConn('COMPLETE');ConnLog.Free;
End;
