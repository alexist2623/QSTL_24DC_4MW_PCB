
Procedure FullDRCSettingsR1;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;
    C:IPCB_Component;R:IPCB_Rule;O:IPCB_DesignRuleCheckerOptions;
    BeforeBatch,BeforeOnline:TRuleSet;
    OldLimit,ComponentCount,ViaRules,ComponentRules,K:Integer;
    Log:TStringList;Failed:Boolean;
Begin
 Log:=TStringList.Create;
 Log.Add('START');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');
 If D=Nil Then Begin Log.Add('STOP_NO_DOCUMENT');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;End;
 Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Begin Log.Add('STOP_NO_BOARD');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;End;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Begin
  Log.Add('STOP_WRONG_BOARD');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;
 End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));
 C:=I.FirstPCBObject;ComponentCount:=0;
 While C<>Nil Do Begin Inc(ComponentCount);C:=I.NextPCBObject;End;
 B.BoardIterator_Destroy(I);
 If ComponentCount<>50 Then Begin Log.Add('STOP_COMPONENT_COUNT');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));
 R:=I.FirstPCBObject;ViaRules:=0;ComponentRules:=0;
 While R<>Nil Do Begin
  If R.DRCEnabled Then Begin
   If R.RuleKind=eRule_RoutingViaStyle Then Inc(ViaRules);
   If R.RuleKind=eRule_ComponentClearance Then Inc(ComponentRules);
  End;
  R:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 Log.Add('ACTIVE_VIA_RULES='+IntToStr(ViaRules));
 Log.Add('ACTIVE_COMPONENT_RULES='+IntToStr(ComponentRules));
 If (ViaRules<>3) Or (ComponentRules<>1) Then Begin
  Log.Add('STOP_RULE_PREFLIGHT');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;
 End;
 Log.Add('GET_OPTIONS');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');
 O:=B.GetState_DesignRuleCheckerOptions;
 If O=Nil Then Begin Log.Add('STOP_NO_OPTIONS');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;End;
 BeforeBatch:=O.RuleSetToCheck;BeforeOnline:=O.OnLineRuleSetToCheck;
 OldLimit:=O.MaxViolationCount;
 Log.Add('MAX_BEFORE='+IntToStr(OldLimit));
 For K:=0 To 255 Do Begin
  If InSet(K,BeforeBatch) Then Log.Add('BATCH_BEFORE='+IntToStr(K));
  If InSet(K,BeforeOnline) Then Log.Add('ONLINE_BEFORE='+IntToStr(K));
 End;
 Log.Add('APPLY_OPTIONS');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');
 O.RuleSetToCheck:=SetUnion(BeforeBatch,MkSet(eRule_RoutingViaStyle,eRule_ComponentClearance));
 If OldLimit<1000000 Then O.MaxViolationCount:=1000000;
 Failed:=False;
 If Not InSet(eRule_RoutingViaStyle,O.RuleSetToCheck) Then Failed:=True;
 If Not InSet(eRule_ComponentClearance,O.RuleSetToCheck) Then Failed:=True;
 If O.MaxViolationCount<1000000 Then Failed:=True;
 If O.OnLineRuleSetToCheck<>BeforeOnline Then Failed:=True;
 For K:=0 To 255 Do Begin
  If InSet(K,BeforeBatch) And Not InSet(K,O.RuleSetToCheck) Then Failed:=True;
 End;
 If Failed Then Begin
  O.RuleSetToCheck:=BeforeBatch;O.OnLineRuleSetToCheck:=BeforeOnline;O.MaxViolationCount:=OldLimit;
  Log.Add('STOP_VERIFICATION_ROLLED_BACK');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;Exit;
 End;
 Log.Add('MAX_AFTER='+IntToStr(O.MaxViolationCount));
 For K:=0 To 255 Do Begin
  If InSet(K,O.RuleSetToCheck) Then Log.Add('BATCH_AFTER='+IntToStr(K));
  If InSet(K,O.OnLineRuleSetToCheck) Then Log.Add('ONLINE_AFTER='+IntToStr(K));
 End;
 B.SetState_DocumentHasChanged;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');
 RunProcess('WorkspaceManager:SaveObject');
 Log.Add('COMPLETE_SETTINGS_ONLY_DRC_STILL_REQUIRED');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_full_drc_settings_r1.txt');Log.Free;
End;
