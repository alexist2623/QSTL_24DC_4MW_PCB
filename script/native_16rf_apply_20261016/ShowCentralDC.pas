Procedure ShowCentralDC;
Var D:IServerDocument;B:IPCB_Board;
Begin
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 B.CurrentLayer:=eMidLayer1;
 B.GraphicalView_ZoomOnRect(MMsToCoord(-8),MMsToCoord(-13),MMsToCoord(28),MMsToCoord(89));
End;
