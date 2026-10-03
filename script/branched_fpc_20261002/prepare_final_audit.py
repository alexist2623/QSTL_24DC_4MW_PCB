"""Prepare save/reopen, PCB audit and schematic compile of the final projects."""
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002'
code=[r'''Procedure BoardAudit(Path,Folder:String);
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
L:=TStringList.Create;L.Add('PROJECT='+Path);WS:=GetWorkspace;P:=WS.DM_GetProjectFromPath(Path);
If P=Nil Then Begin L.Add('PROJECT_NOT_OPEN');L.SaveToFile(Folder+'native_compile.txt');L.Free;Exit;End;
Good:=P.DM_Compile;If Good Then L.Add('COMPILE_RESULT=True') Else L.Add('COMPILE_RESULT=False');
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
Procedure FinalAudit;
Begin
''']
for name in ('ZIF_to_2xZIF','ZIF_to_DSUB25'):
 folder=str(OUT/name)+'\\'
 code += [f"BoardAudit('{folder+name}.PcbDoc','{folder}');",f"CompileProject('{folder+name}.PrjPcb','{folder}');"]
code+=['End;']
(H/'FinalAudit.pas').write_text('\n'.join(code),encoding='ascii')
(H/'FinalAudit.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=FinalAudit.pas\n[Generic_ScriptingSystem]\nStartProcName=FinalAudit.pas>FinalAudit\n')
# Isolate native compile from PCB reopen and flush checkpoints before API calls.
text='\n'.join(code)
text=text.replace("L:=TStringList.Create;L.Add('PROJECT='+Path);WS", "L:=TStringList.Create;L.Add('PROJECT='+Path);L.SaveToFile(Folder+'native_compile.txt');WS")
text=text.replace("Good:=P.DM_Compile;", "L.Add('COMPILE_START');L.SaveToFile(Folder+'native_compile.txt');Good:=P.DM_Compile;")
text=text[:text.index('Procedure FinalAudit;')]
text+='Procedure CompileOnly;\nBegin\n'
for name in ('ZIF_to_2xZIF','ZIF_to_DSUB25'):
 folder=str(OUT/name)+'\\'
 text+=f"CompileProject('{folder+name}.PrjPcb','{folder}');\n"
text+='End;\n'
(H/'CompileOnly.pas').write_text(text,encoding='ascii')
(H/'CompileOnly.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=CompileOnly.pas\n[Generic_ScriptingSystem]\nStartProcName=CompileOnly.pas>CompileOnly\n')
text='\n'.join(code)
start=text.index('PCBServer.PreProcess;Try')
end=text.index("L:=TStringList.Create;L.Add('SAVED_AND_REOPENED='+Path);")
text=text[:start]+text[end:]
text=text.replace("SAVED_AND_REOPENED=", "COLD_OPENED_SAVED_DOCUMENT=")
text=text.replace("L:=TStringList.Create;L.Add('COLD_OPENED_SAVED_DOCUMENT='+Path);", "L:=TStringList.Create;L.Add('COLD_OPENED_SAVED_DOCUMENT='+Path);L.SaveToFile(Folder+'native_validation.txt');")
text=text.replace('B.ConnectivelyValidateNets;', "B.ConnectivelyValidateNets;L.Add('NETS_REBUILT');L.SaveToFile(Folder+'native_validation.txt');")
text=text.replace("L.Add('PAD_PASTE_ENABLED='+IntToStr(PasteCount));", "L.Add('PAD_PASTE_ENABLED='+IntToStr(PasteCount));L.SaveToFile(Folder+'native_validation.txt');")
text=text.replace("Good:=B.RunBatchDesignRuleCheck", "L.Add('DRC_START');L.SaveToFile(Folder+'native_validation.txt');Good:=B.RunBatchDesignRuleCheck")
text=text.replace('Procedure FinalAudit;', 'Procedure ColdAudit;')
text=text.replace("Good:=P.DM_Compile;", "L.Add('COMPILE_START');L.SaveToFile(Folder+'native_compile.txt');Good:=P.DM_Compile;")
(H/'ColdAudit.pas').write_text(text,encoding='ascii')
(H/'ColdAudit.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=ColdAudit.pas\n[Generic_ScriptingSystem]\nStartProcName=ColdAudit.pas>ColdAudit\n')
print('Prepared final native audit.')
