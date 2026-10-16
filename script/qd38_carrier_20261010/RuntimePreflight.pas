
Procedure InspectModels;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Primitive;C:IPCB_Component;
    Body:IPCB_ComponentBody;M:IPCB_Model;Pt:TCoordPoint;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('BOARD|'+B.FileName);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  C:=P.Component;
  If C<>Nil Then Begin
   Body:=P;M:=Body.GetModel;
   If M<>Nil Then Begin Pt:=M.GetOrigin;L.Add('MODEL|'+C.Name.Text+'|'+FloatToStr(CoordToMMs(Pt.X))+'|'+FloatToStr(CoordToMMs(Pt.Y)));End;
  End;P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_models.txt');L.Free;
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


Procedure RuntimePreflight;
Var D:IServerDocument;
Begin
 InspectModels;
 D:=Client.OpenDocument('SCH','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.SchDoc');If D<>Nil Then Client.ShowDocument(D);
 CompileProject('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\');
End;
