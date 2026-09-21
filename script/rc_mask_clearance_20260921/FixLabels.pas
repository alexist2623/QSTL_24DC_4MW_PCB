Procedure FixLabels;
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;
Begin
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 PCBServer.PreProcess;
 Try
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin
 If C.Name.Text='R1' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(16.7),MMsToCoord(30.2));End;
 If C.Name.Text='R5' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(0.5),MMsToCoord(30.5));End;
 If C.Name.Text='R3' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(15.5),MMsToCoord(45.8));End;
 If C.Name.Text='R4' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(5.8),MMsToCoord(45.8));End;
 C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
End;


