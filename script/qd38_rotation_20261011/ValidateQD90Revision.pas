
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
 If Count<>50 Then Begin L.Add('STOP_COMPONENT_COUNT');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_validation.txt');L.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;B.AnalyzeNet(N);B.CleanNet(N);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L.Add('SAVED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_validation.txt');
 Client.CloseDocument(D);D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 L.Add('REOPENED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_validation.txt');
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
 L.Add('DRC_START');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_validation.txt');
 Good:=B.RunBatchDesignRuleCheck('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Native_DRC.html',eDRC_HTML,False,False);
 If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
 { Persist the connectivity cache rebuilt by DRC, then inspect the saved file. }
 B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Client.CloseDocument(D);D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;
 While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('POST_DRC_SAVED_CONNECTION_COUNT='+IntToStr(Count));
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_validation.txt');L.Free;
End;
Procedure CompileProject(Path,Folder:String);
Var WS:IWorkspace;P:IProject;D:IDocument;N:INet;Pin:INetItem;V:IViolation;L:TStringList;Good:Boolean;I,J:Integer;
Begin
L:=TStringList.Create;L.Add('PROJECT='+Path);WS:=GetWorkspace;P:=WS.DM_GetProjectFromPath(Path);
If P=Nil Then Begin L.Add('PROJECT_NOT_OPEN');L.SaveToFile(Folder+'native_compile.txt');L.Free;Exit;End;
L.Add('COMPILE_START');L.SaveToFile(Folder+'native_compile.txt');Good:=P.DM_Compile;If Good Then L.Add('COMPILE_RESULT=True') Else L.Add('COMPILE_RESULT=False');
L.Add('VIOLATION_COUNT='+IntToStr(P.DM_ViolationCount));
For I:=0 To P.DM_ViolationCount-1 Do Begin V:=P.DM_Violations(I);If V<>Nil Then Begin L.Add('VIOLATION='+V.DM_DescriptorString);L.Add('DETAIL='+V.DM_DetailString);End;End;
D:=P.DM_DocumentFlattened;If D=Nil Then D:=P.DM_TopLevelLogicalDocument;
If D=Nil Then L.Add('NO_COMPILED_DOCUMENT') Else Begin L.Add('NET_COUNT='+IntToStr(D.DM_NetCount));
For I:=0 To D.DM_NetCount-1 Do Begin N:=D.DM_Nets(I);If N<>Nil Then Begin
L.Add('NET='+N.DM_NetName+'|PINS='+IntToStr(N.DM_PinCount));
For J:=0 To N.DM_PinCount-1 Do Begin Pin:=N.DM_Pins(J);If Pin<>Nil Then L.Add('PIN='+Pin.DM_LogicalPartDesignator+'.'+Pin.DM_PinNumber);End;
End;End;End;
L.Add('COMPLETE');L.SaveToFile(Folder+'native_compile.txt');L.Free;
End;


Procedure ValidateQD90Revision;
Var D:IServerDocument;
Begin
 SaveAndCheckNative;
 D:=Client.OpenDocument('SCH','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.SchDoc');If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('SCH','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.SchDoc');If D<>Nil Then Client.ShowDocument(D);
 CompileProject('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\');
End;
