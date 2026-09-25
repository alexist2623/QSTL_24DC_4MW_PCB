Procedure FixPinMarker;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;A:IPCB_Arc;Count:Integer;L:TStringList;
Begin
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;Count:=0;
 PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eArcObject));A:=I.FirstPCBObject;
  While A<>Nil Do Begin
   If (A.Layer=eTopOverlay) And (Abs(CoordToMMs(A.XCenter)-2.25)<0.001) And (Abs(CoordToMMs(A.YCenter)-2.195)<0.001) Then Begin
    A.XCenter:=MMsToCoord(3);A.YCenter:=MMsToCoord(2.1);Inc(Count);
   End;A:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L:=TStringList.Create;L.Add('MOVED_J1_PIN1_MARKER='+IntToStr(Count));L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\marker_native.txt');L.Free;
End;
