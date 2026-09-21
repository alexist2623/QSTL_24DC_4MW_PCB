Procedure ShowOriginal;
Var D:IServerDocument;B:IPCB_Board;P:String;
Begin
 P:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 B.GraphicalView_ZoomOnRect(MMsToCoord(0),MMsToCoord(22),MMsToCoord(19.5),MMsToCoord(50));
End;
