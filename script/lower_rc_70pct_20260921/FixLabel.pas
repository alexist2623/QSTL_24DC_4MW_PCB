Procedure FixLabel;
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;L:TStringList;
Begin
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 PCBServer.PreProcess;
 Try
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin
 If C.Name.Text='C1' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(9.485),MMsToCoord(27.8));End;
 C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L:=TStringList.Create;L.Add('C1 label moved downward by 1.2 mm to remove silk collision.');L.Add('COMPLETE');L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\lower_rc_70pct_20260921\label_native.txt');L.Free;
End;
