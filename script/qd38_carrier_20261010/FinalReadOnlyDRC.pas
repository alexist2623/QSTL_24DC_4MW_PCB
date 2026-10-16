Procedure FinalReadOnlyDRC;
Var D:IServerDocument;B:IPCB_Board;L:TStringList;Good:Boolean;
Begin
 L:=TStringList.Create;
 L.Add('START');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\final_readonly_drc.txt');
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');
 If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 Good:=B.RunBatchDesignRuleCheck('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 L.Add('NO_SAVE_PERFORMED');L.Add('COMPLETE');
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\final_readonly_drc.txt');L.Free;
End;
