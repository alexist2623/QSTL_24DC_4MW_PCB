Procedure ReopenCheck;
Var B:IPCB_Board;D:IServerDocument;P:String;L:TStringList;Good:Boolean;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;P:=B.FileName;
 If LowerCase(P)<>'c:\jeonghyunpark\workspace\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb.pcbdoc' Then Exit;
 D:=Client.GetDocumentByPath(P);If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB',P);If D<>Nil Then Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 B.GraphicalView_ZoomOnRect(MMsToCoord(-1),MMsToCoord(-1),MMsToCoord(20.5),MMsToCoord(68.9));
 L:=TStringList.Create;
 Good:=B.RunBatchDesignRuleCheck(ExtractFilePath(P)+'docs\DC_direct_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(P)+'work\dc_direct_drc.txt');L.Free;
End;
