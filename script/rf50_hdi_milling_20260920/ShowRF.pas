Procedure ShowRF;
Var B:IPCB_Board;
Begin
 B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;
 B.CurrentLayer:=eBottomLayer;
 Client.SendMessage('PCB:Zoom','Action=All',255,Client.CurrentView);
End;
