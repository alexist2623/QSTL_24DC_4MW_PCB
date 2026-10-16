Procedure CloseAlignmentLibrary;
Var D:IServerDocument;L:TStringList;
Begin
D:=Client.OpenDocument('PCBLIB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QD4_2SET_38.PcbLib');If D<>Nil Then Client.CloseDocument(D);
L:=TStringList.Create;L.Add('CLOSED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_pad_alignment_20261011\library_closed.txt');L.Free;
End;
