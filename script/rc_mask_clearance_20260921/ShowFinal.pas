Procedure ShowFinal;
Var D:IServerDocument;B:IPCB_Board;
Begin
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 B.GraphicalView_ZoomOnRect(MMsToCoord(0.1),MMsToCoord(25),MMsToCoord(19.4),MMsToCoord(54));B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
End;
