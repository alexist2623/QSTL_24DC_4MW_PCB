Procedure ReloadFrozenRevision;
Var D:IServerDocument; L:TStringList;
Begin
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');
 If D=Nil Then Exit;
 Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');
 If D=Nil Then Exit;
 Client.ShowDocument(D);
 L:=TStringList.Create;
 L.Add('FROZEN_NATIVE_REOPENED_NO_SAVE_REQUESTED');
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\reload_frozen_log.txt');
 L.Free;
End;
