Procedure FinishRF6Silk;
Var B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;Found:Integer;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>'c:\jeonghyunpark\workspace\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb.pcbdoc' Then Exit;
 Found:=0;PCBServer.PreProcess;
 Try
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin If C.Name.Text='R3' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(15.5),MMsToCoord(44.8));Inc(Found);End;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L:=TStringList.Create;L.Add('LABELS_MOVED='+IntToStr(Found));L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_silk.txt');L.Free;
End;
