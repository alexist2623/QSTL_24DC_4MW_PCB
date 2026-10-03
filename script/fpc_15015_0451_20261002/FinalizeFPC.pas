{ Configure the single-copper flex stack, save, reopen and audit natively. }
Procedure BuildFPC;
Var B:IPCB_Board;Doc:IServerDocument;Path,Folder:String;L:TStringList;
 S:IPCB_LayerStack_V7;V,VB:IPCB_LayerObject_V7;D:IPCB_DielectricObject;
 MS:IPCB_MasterLayerStack;SS:IPCB_LayerStack;LO,LN:IPCB_LayerObject;DL:IPCB_DielectricLayer;
 I:IPCB_BoardIterator;P:IPCB_Primitive;N:IPCB_Net;J,K:Integer;Good:Boolean;
Begin
 Folder:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_15015_0451\';
 Path:=Folder+'FPC_15015_0451.PcbDoc';
 Doc:=Client.OpenDocument('PCB',Path);If Doc=Nil Then Exit;Client.ShowDocument(Doc);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
 L:=TStringList.Create;L.Add('START');L.SaveToFile(Folder+'native_validation.txt');
 PCBServer.PreProcess;
 Try
  S:=B.LayerStack_V7;V:=S.FirstLayer;V.CopperThickness:=MMsToCoord(0.018);
  D:=V.Dielectric;D.DielectricHeight:=MMsToCoord(0.045);D.DielectricMaterial:='Polyimide + adhesive';
  VB:=S.NextLayer(V);If VB<>Nil Then S.RemoveFromStack(VB);
  L.Add('COPPER_AND_BASE');L.SaveToFile(Folder+'native_validation.txt');
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Doc:=Client.GetDocumentByPath(Path);Client.CloseDocument(Doc);Doc:=Client.OpenDocument('PCB',Path);Client.ShowDocument(Doc);B:=PCBServer.GetCurrentPCBBoard;
 L.Add('REOPENED');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));I.AddFilter_Method(eProcessAll);P:=I.FirstPCBObject;K:=0;
 While P<>Nil Do Begin Inc(K);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('UNROUTED_CONNECTIONS='+IntToStr(K));L.SaveToFile(Folder+'native_validation.txt');
 Good:=B.RunBatchDesignRuleCheck(Folder+'Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 B.GraphicalView_ZoomOnRect(MMsToCoord(-2),MMsToCoord(-5),MMsToCoord(104),MMsToCoord(21));
 L.Add('COMPLETE');L.SaveToFile(Folder+'native_validation.txt');L.Free;
End;


