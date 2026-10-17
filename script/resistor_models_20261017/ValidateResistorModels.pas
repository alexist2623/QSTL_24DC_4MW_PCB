
Procedure SaveAndCheckNative;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;
    C:IPCB_Component;PD:IPCB_Pad;V:IPCB_Via;N:IPCB_Net;PC:TPadCache;
    L:TStringList;Count,QCount,PasteCount,ViaCount,ShieldCount:Integer;Good:Boolean;RefName:String;
Begin
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('BOARD='+B.FileName);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;Count:=0;
 While C<>Nil Do Begin Inc(Count);C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('COMPONENTS='+IntToStr(Count));
 If Count<>50 Then Begin L.Add('STOP_COMPONENT_COUNT');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\native_validation.txt');L.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;B.AnalyzeNet(N);B.CleanNet(N);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L.Add('SAVED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\native_validation.txt');
 Client.CloseDocument(D);D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 L.Add('REOPENED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\native_validation.txt');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;Count:=0;QCount:=0;
 While PD<>Nil Do Begin
  Inc(Count);RefName:='MOUNT';If PD.Component<>Nil Then RefName:=PD.Component.Name.Text;
  If RefName='Q1' Then Inc(QCount);PC:=PD.GetState_Cache;
  If PD.GetState_PasteMaskEnabled Then L.Add('PAD='+RefName+'.'+PD.Name+'|PASTE=True') Else L.Add('PAD='+RefName+'.'+PD.Name+'|PASTE=False');
  PD:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);L.Add('PAD_COUNT='+IntToStr(Count));L.Add('QD_PAD_COUNT='+IntToStr(QCount));
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;ViaCount:=0;ShieldCount:=0;PasteCount:=0;
 While V<>Nil Do Begin
  Inc(ViaCount);If V.GetState_PasteMaskEnabled Then Inc(PasteCount);
  If V.Net<>Nil Then Begin
   If V.Net.Name='GND' Then Inc(ShieldCount);
   L.Add('VIA='+V.Net.Name+'|LOW='+IntToStr(V.LowLayer)+'|HIGH='+IntToStr(V.HighLayer));
  End;V:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('VIA_COUNT='+IntToStr(ViaCount));L.Add('SHIELD_VIA_COUNT='+IntToStr(ShieldCount));L.Add('VIA_PASTE_ENABLED='+IntToStr(PasteCount));
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;
 While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('STORED_CONNECTION_COUNT='+IntToStr(Count));
 L.Add('DRC_START');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\native_validation.txt');
 Good:=B.RunBatchDesignRuleCheck('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 { Persist the connectivity cache rebuilt by DRC, then inspect the saved file. }
 B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Client.CloseDocument(D);D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;
 While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('POST_DRC_SAVED_CONNECTION_COUNT='+IntToStr(Count));
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\resistor_models_20261017\native_validation.txt');L.Free;
End;

Procedure ValidateResistorModels;
Begin SaveAndCheckNative;End;
