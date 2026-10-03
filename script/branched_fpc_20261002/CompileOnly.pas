Procedure BoardAudit(Path,Folder:String);
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;C:IPCB_Component;N:IPCB_Net;
PD:IPCB_Pad;V:IPCB_Via;PC:TPadCache;L:TStringList;Count,PasteCount,ViaCount,TentCount:Integer;Good:Boolean;
Begin
D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
PCBServer.PreProcess;Try
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin C.SourceDesignator:=C.Name.Text;C.SourceLibReference:=C.Pattern;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
Client.CloseDocument(D);D:=Client.OpenDocument('PCB',Path);Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
L:=TStringList.Create;L.Add('SAVED_AND_REOPENED='+Path);
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;Count:=0;PasteCount:=0;
While PD<>Nil Do Begin Inc(Count);If PD.GetState_PasteMaskEnabled Then Inc(PasteCount);PC:=PD.GetState_Cache;
L.Add('PAD='+PD.Component.Name.Text+'.'+PD.Name+'|MASK='+FloatToStr(CoordToMMs(PC.SolderMaskExpansion))+'|PASTE='+FloatToStr(CoordToMMs(PC.PasteMaskExpansion)));
PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('PAD_COUNT='+IntToStr(Count));L.Add('PAD_PASTE_ENABLED='+IntToStr(PasteCount));
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;ViaCount:=0;TentCount:=0;PasteCount:=0;
While V<>Nil Do Begin Inc(ViaCount);If V.GetState_IsTenting_Top And V.GetState_IsTenting_Bottom Then Inc(TentCount);If V.GetState_PasteMaskEnabled Then Inc(PasteCount);V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
L.Add('VIA_COUNT='+IntToStr(ViaCount));L.Add('VIA_TENTED_BOTH='+IntToStr(TentCount));L.Add('VIA_PASTE_ENABLED='+IntToStr(PasteCount));
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));P:=I.FirstPCBObject;Count:=0;
While P<>Nil Do Begin Inc(Count);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('REBUILT_CONNECTION_COUNT='+IntToStr(Count));
Good:=B.RunBatchDesignRuleCheck(Folder+'Native_DRC.html',eDRC_HTML,False,False);If Good Then L.Add('DRC_RETURNED_TRUE') Else L.Add('DRC_RETURNED_FALSE');
L.Add('COMPLETE');L.SaveToFile(Folder+'native_validation.txt');L.Free;
End;
Procedure CompileProject(Path,Folder:String);
Var WS:IWorkspace;P:IProject;D:IDocument;N:INet;Pin:INetItem;V:IViolation;L:TStringList;Good:Boolean;I,J:Integer;
Begin
L:=TStringList.Create;L.Add('PROJECT='+Path);L.SaveToFile(Folder+'native_compile.txt');WS:=GetWorkspace;P:=WS.DM_GetProjectFromPath(Path);
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
Procedure CompileOnly;
Begin
CompileProject('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_2xZIF\ZIF_to_2xZIF.PrjPcb','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_2xZIF\');
CompileProject('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_DSUB25\ZIF_to_DSUB25.PrjPcb','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_DSUB25\');
End;
