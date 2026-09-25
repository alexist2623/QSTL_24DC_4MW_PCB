Procedure ResizeM16;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Pad;Poly:IPCB_Polygon;Path:String;Count:Integer;L:TStringList;
Begin
 Path:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
 Count:=0;PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   If (P.Name='MH7') Or (P.Name='MH8') Then Begin
    P.Y:=MMsToCoord(1.2);P.HoleSize:=MMsToCoord(1.8);
    P.TopXSize:=MMsToCoord(2.2);P.TopYSize:=MMsToCoord(2.2);
    P.MidXSize:=MMsToCoord(2.2);P.MidYSize:=MMsToCoord(2.2);
    P.BotXSize:=MMsToCoord(2.2);P.BotYSize:=MMsToCoord(2.2);Inc(Count);
   End;
   P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  B.RebuildPadCaches;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin Poly.SetState_CopperPourInvalid;Poly.Rebuild;Poly:=I.NextPCBObject;End;
  B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L:=TStringList.Create;L.Add('M1.6;HOLE=1.8;LAND=2.2;Y=1.2;COUNT='+IntToStr(Count));L.Add('COMPLETE');
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\resize_native.txt');L.Free;
End;

Var ConnLog:TStringList;ConnPath:String;
Procedure MarkConn(S:String);Begin ConnLog.Add(S);ConnLog.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\reopen_check.txt');End;
Procedure CountConnections(B:IPCB_Board;Stage:String);
Var I:IPCB_BoardIterator;C:IPCB_Connection;N:Integer;Name:String;
Begin
 N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));I.AddFilter_Method(eProcessAll);C:=I.FirstPCBObject;
 While C<>Nil Do Begin
  Inc(N);Name:='';If C.Net<>Nil Then Name:=C.Net.Name;
  MarkConn(Stage+'|'+Name+'|'+IntToStr(C.X1)+','+IntToStr(C.Y1)+'|'+IntToStr(C.X2)+','+IntToStr(C.Y2));
  C:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkConn(Stage+'_COUNT='+IntToStr(N));
End;

Procedure ReopenAudit;
Var B:IPCB_Board;D:IServerDocument;P:String;Good:Boolean;
Begin
 ConnPath:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\';P:=ConnPath+'QSTL_24DC_4MW_PCB.PcbDoc';
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 D:=Client.GetDocumentByPath(P);If D<>Nil Then Client.CloseDocument(D);
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 ConnLog:=TStringList.Create;MarkConn('REOPENED');CountConnections(B,'AFTER_REOPEN');
 Good:=B.RunBatchDesignRuleCheck(ConnPath+'fabrication\JLCPCB_HDI_20260925\Native_DRC.html',eDRC_HTML,False,False);
 If Good Then MarkConn('DRC_RETURNED_TRUE') Else MarkConn('DRC_RETURNED_FALSE');
 CountConnections(B,'AFTER_DRC');B.GraphicalView_ZoomOnRect(MMsToCoord(3),MMsToCoord(25),MMsToCoord(19),MMsToCoord(50));
 MarkConn('COMPLETE');ConnLog.Free;
End;

Function BoolText(V:Boolean):String;
Begin If V Then Result:='1' Else Result:='0';End;
Procedure AuditPaste;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Pad;V:IPCB_Via;C:IPCB_Component;PC:TPadCache;L:TStringList;S:String;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('PAD_FIELDS=TYPE|COMPONENT|PIN|EXPANSION|EXPANSION_MODE|TOP_SOLDER|BOTTOM_SOLDER|PASTE_ENABLED|TOP_PASTE_ENABLED|BOTTOM_PASTE_ENABLED');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin C:=P.Component;If C=Nil Then S:='MOUNT' Else S:=C.Name.Text;
  PC:=P.GetState_Cache;L.Add('PAD|'+S+'|'+P.Name+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+IntToStr(PC.SolderMaskExpansion)+'|'+IntToStr(PC.SolderMaskBottomExpansion)+'|'+BoolText(P.GetState_PasteMaskEnabled)+'|'+BoolText(P.GetState_IsTopPasteEnabled)+'|'+BoolText(P.GetState_IsBottomPasteEnabled));P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin PC:=V.GetState_Cache;L.Add('VIA|'+IntToStr(N)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BoolText(V.GetState_PasteMaskEnabled));Inc(N);V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\native_paste_audit.txt');L.Free;
End;

{ Compile/report only. No document save, ECO, property update, or source write. }
Var DraftCompileProject,DraftCompileReport,DraftSchPath : String;
    DraftSchDoc : ISch_Document;

Function GuardZIF24V2Part(RefName,UID : String) : Boolean;
Var It : ISch_Iterator; C : ISch_Component; Found : Integer;
Begin
    Found:=0;
    It:=DraftSchDoc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    Try
        C:=It.FirstSchObject;
        While C<>Nil Do Begin
            If (C.Designator.Text=RefName) And (C.GetState_UniqueId=UID) Then Inc(Found);
            C:=It.NextSchObject;
        End;
    Finally DraftSchDoc.SchIterator_Destroy(It); End;
    Result:=Found=1;
End;

Function GuardZIF24V2ComponentCount : Boolean;
Var It : ISch_Iterator; C : ISch_Component; Count : Integer;
Begin
    Count:=0;
    It:=DraftSchDoc.SchIterator_Create;
    It.AddFilter_ObjectSet(MkSet(eSchComponent));
    Try
        C:=It.FirstSchObject;
        While C<>Nil Do Begin Inc(Count); C:=It.NextSchObject; End;
    Finally DraftSchDoc.SchIterator_Destroy(It); End;
    Result:=Count=22;
End;

Procedure ValidateZIF24V2CircuitV1;
Var
    WS : IWorkspace;
    P : IProject;
    D : IDocument;
    N : INet;
    Pin : INetItem;
    V : IViolation;
    Report : TStringList;
    Good : Boolean;
    I, J : Integer;
Begin
    If SchServer=Nil Then Exit;
    DraftSchDoc:=SchServer.GetCurrentSchDocument;
    If DraftSchDoc=Nil Then Exit;
    DraftSchPath:=DraftSchDoc.GetState_DocumentName;
    If UpperCase(ExtractFileName(DraftSchPath))<>'QSTL_24DC_4MW_PCB.SCHDOC' Then Exit;
    If Pos('\WORKSPACE\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\',UpperCase(DraftSchPath))=0 Then Exit;
    If Not GuardZIF24V2ComponentCount Then Exit;
    If Not GuardZIF24V2Part('J1','GPQWNHID') Then Exit;
    If Not GuardZIF24V2Part('Q1','UMIRGJFR') Then Exit;
    If Not GuardZIF24V2Part('SMP1','ZSMPCNAA') Then Exit;
    If Not GuardZIF24V2Part('SMP2','ZSMPCNAB') Then Exit;
    If Not GuardZIF24V2Part('SMP3','ZSMPCNAC') Then Exit;
    If Not GuardZIF24V2Part('SMP4','ZSMPCNAD') Then Exit;
    If Not GuardZIF24V2Part('R1','ZRESCHAA') Then Exit;
    If Not GuardZIF24V2Part('R2','ZRESCHAB') Then Exit;
    If Not GuardZIF24V2Part('R3','ZRESCHAC') Then Exit;
    If Not GuardZIF24V2Part('R4','ZRESCHAD') Then Exit;
    If Not GuardZIF24V2Part('C1','ZCAPCHAA') Then Exit;
    If Not GuardZIF24V2Part('C2','ZCAPCHAB') Then Exit;
    If Not GuardZIF24V2Part('C3','ZCAPCHAC') Then Exit;
    If Not GuardZIF24V2Part('C4','ZCAPCHAD') Then Exit;
    If Not GuardZIF24V2Part('SMP7','VTSMPSEV') Then Exit;
    If Not GuardZIF24V2Part('SMP8','VTSMPEIG') Then Exit;
    If Not GuardZIF24V2Part('SMP5','EHYNHWUZ') Then Exit;
    If Not GuardZIF24V2Part('R5','PDGWTIKC') Then Exit;
    If Not GuardZIF24V2Part('C5','HLYWDMCQ') Then Exit;
    If Not GuardZIF24V2Part('SMP6','VLTJYUPC') Then Exit;
    If Not GuardZIF24V2Part('R6','FHQTZXVJ') Then Exit;
    If Not GuardZIF24V2Part('C6','BIZXXOAG') Then Exit;
    DraftCompileProject:=ChangeFileExt(DraftSchPath,'.PrjPcb');
    DraftCompileReport:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\schematic_compile.txt';
    WS := GetWorkspace;
    If WS = Nil Then Exit;
    P := WS.DM_GetProjectFromPath(DraftCompileProject);
    If P = Nil Then
    Begin

        Exit;
    End;
    If UpperCase(P.DM_ProjectFullPath)<>UpperCase(DraftCompileProject) Then Exit;
    Report := TStringList.Create;
    Try
        Report.Add('PROJECT=' + P.DM_ProjectFullPath);
        Report.Add('COMPILE_START');
        Report.SaveToFile(DraftCompileReport);
        Good := P.DM_Compile;
        If Good Then Report.Add('COMPILE_RESULT=True')
        Else Report.Add('COMPILE_RESULT=False');
        Report.SaveToFile(DraftCompileReport);
        Report.Add('VIOLATION_COUNT=' + IntToStr(P.DM_ViolationCount));
        Report.SaveToFile(DraftCompileReport);
        For I := 0 To P.DM_ViolationCount - 1 Do
        Begin
            V := P.DM_Violations(I);
            If V <> Nil Then
            Begin
                Report.Add('VIOLATION=' + IntToStr(I) + '|' + V.DM_DescriptorString);
                Report.Add('DETAIL=' + V.DM_DetailString);
                Report.SaveToFile(DraftCompileReport);
            End;
        End;
        D := P.DM_DocumentFlattened;
        If D = Nil Then D := P.DM_TopLevelLogicalDocument;
        If D = Nil Then Report.Add('NO_COMPILED_DOCUMENT')
        Else
        Begin
            Report.Add('NET_COUNT=' + IntToStr(D.DM_NetCount));
            Report.SaveToFile(DraftCompileReport);
            For I := 0 To D.DM_NetCount - 1 Do
            Begin
                N := D.DM_Nets(I);
                If N <> Nil Then
                Begin
                    Report.Add('NET=' + N.DM_NetName + '|PINS=' + IntToStr(N.DM_PinCount));
                    Report.SaveToFile(DraftCompileReport);
                    For J := 0 To N.DM_PinCount - 1 Do
                    Begin
                        Pin := N.DM_Pins(J);
                        If Pin <> Nil Then
                        Begin
                            Report.Add('PIN=' + Pin.DM_LogicalPartDesignator + '-' + Pin.DM_PinNumber);
                            Report.SaveToFile(DraftCompileReport);
                        End;
                    End;
                End;
            End;
        End;
        Report.Add('COMPLETE');
        Report.SaveToFile(DraftCompileReport);
    Finally
        Report.Free;
    End;

End;


Procedure OpenAndValidate;
Var D:IServerDocument;P:String;
Begin
 P:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.SchDoc';
 D:=Client.OpenDocument('SCH',P);If D=Nil Then Exit;Client.ShowDocument(D);
 ValidateZIF24V2CircuitV1;
End;
Procedure AuditAll;
Var D:IServerDocument;
Begin
 ReopenAudit;
 AuditPaste;
 OpenAndValidate;
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If D<>Nil Then Client.ShowDocument(D);
End;


Procedure ApplyM16AndAudit;
Begin ResizeM16;AuditAll;End;
