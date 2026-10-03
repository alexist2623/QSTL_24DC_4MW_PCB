{ Native validation of the new populated adapter. Never opens the carrier. }
Procedure ReviewAdapters;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;N:IPCB_Net;Pad:IPCB_Pad;V:IPCB_Via;L:TStringList;Count,PasteCount:Integer;Path,Folder:String;Good:Boolean;
Begin
 Folder:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_DSUB25\';Path:=Folder+'ZIF_to_DSUB25.PcbDoc';
 D:=Client.GetDocumentByPath(Path);If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
 L:=TStringList.Create;L.Add('REOPENED');
 B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);B.RebuildPadCaches;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;Count:=0;PasteCount:=0;
 While Pad<>Nil Do Begin Inc(Count);If Pad.GetState_PasteMaskEnabled Then Inc(PasteCount);Pad:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('PAD_COUNT='+IntToStr(Count));L.Add('PAD_PASTE_ENABLED='+IntToStr(PasteCount));
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;
 While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('REBUILT_CONNECTION_COUNT='+IntToStr(Count));
 Good:=B.RunBatchDesignRuleCheck(Folder+'Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L.Add('COMPLETE');L.SaveToFile(Folder+'native_validation.txt');L.Free;
End;
