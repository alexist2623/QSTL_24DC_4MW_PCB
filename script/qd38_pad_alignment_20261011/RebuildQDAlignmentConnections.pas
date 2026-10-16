Procedure RebuildQDAlignmentConnections;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;N:IPCB_Net;P:IPCB_Primitive;L:TStringList;Count:Integer;
Begin
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('BOUND_SAVED_SHA256=41df921a11093a92c8e40b77fc0b17f458640c8e5a15582b986bbffba9dd1573');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;L.Add('REBUILT='+N.Name);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('CONNECTION_COUNT_AFTER_REBUILD='+IntToStr(Count));
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;L.Add('COMPLETE_NOT_SAVED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_pad_alignment_20261011\native_connectivity_rebuild.txt');L.Free;
End;
