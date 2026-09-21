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
    DraftCompileReport:=ExtractFilePath(DraftSchPath)+'work\dc_direct_schematic_compile.txt';
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