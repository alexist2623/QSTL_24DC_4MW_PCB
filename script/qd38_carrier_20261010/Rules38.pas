Var RuleBoard:IPCB_Board;RuleLog:TStringList;
Function FindRule(Name:String):IPCB_Rule;
Var I:IPCB_BoardIterator;R:IPCB_Rule;
Begin
 Result:=Nil;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
 While R<>Nil Do Begin If R.Name=Name Then Begin Result:=R;Break;End;R:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);
End;
Procedure RegisterRule(R:IPCB_Rule);
Begin RuleBoard.AddPCBObject(R);PCBServer.SendMessageToRobots(RuleBoard.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,R.I_ObjectAddress);End;
Procedure Rules38;
Var R:IPCB_Rule;W:IPCB_MaxMinWidthConstraint;VR,VRDefault:IPCB_RoutingViaStyleRule;CL:IPCB_ClearanceConstraint;
 I:IPCB_BoardIterator;C:IPCB_Component;V:IPCB_Via;NC,NSmall,NRegular,NShield,J:Integer;
 RFScope,DCScope,SmallScope:String;IsSmall:Boolean;
Begin
 RuleBoard:=PCBServer.GetCurrentPCBBoard;If RuleBoard=Nil Then Exit;
 If LowerCase(RuleBoard.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 RuleLog:=TStringList.Create;RuleLog.Add('BOARD|'+RuleBoard.FileName);
 NC:=0;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);C:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);
 If NC<>50 Then Begin RuleLog.Add('STOP_COMPONENT_COUNT');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
 NSmall:=0;NRegular:=0;NShield:=0;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin
  If V.Net=Nil Then Begin RuleLog.Add('STOP_UNNETTED_VIA');Break;End;
  If V.Net.Name='GND' Then Begin
   If (V.LowLayer<>eMidLayer4) Or (V.HighLayer<>eBottomLayer) Then Begin RuleLog.Add('STOP_SHIELD_SPAN');Break;End;
   Inc(NShield);
  End Else Begin
   If (V.LowLayer<>eTopLayer) Or (V.HighLayer<>eBottomLayer) Then Begin RuleLog.Add('STOP_SIGNAL_SPAN');Break;End;
   IsSmall:=(V.X>=MMsToCoord(2.299997440)) And (V.X<=MMsToCoord(17.499998520)) And (V.Y>=MMsToCoord(2.335000080)) And (V.Y<=MMsToCoord(7.000000300));
   If IsSmall Then Inc(NSmall) Else Inc(NRegular);
  End;V:=I.NextPCBObject;
 End;RuleBoard.BoardIterator_Destroy(I);
 If (V<>Nil) Or (NSmall<>38) Or (NRegular<>38) Or (NShield<>702) Then Begin RuleLog.Add('STOP_VIA_COUNTS');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;

If FindRule('RF_50OHM_WIDTH')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|RF_50OHM_WIDTH');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('Width')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|Width');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('RoutingVias')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|RoutingVias');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('RF_SHIELD_L5_L6')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|RF_SHIELD_L5_L6');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('Clearance')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|Clearance');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('RF_CPW_GND_GAP_0P2')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|RF_CPW_GND_GAP_0P2');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
If FindRule('DC_GND_GAP_0P2')=Nil Then Begin RuleLog.Add('STOP_MISSING_RULE|DC_GND_GAP_0P2');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;Exit;End;
RFScope:='OnLayer(''L6_RF_QD'') And (InNet(''MW02'') Or InNet(''MW05'') Or InNet(''MW09'') Or InNet(''MW11'') Or InNet(''MW12'') Or InNet(''MW13'') Or InNet(''MW15'') Or InNet(''MW16'') Or InNet(''MW21'') Or InNet(''MW24'') Or InNet(''MW28'') Or InNet(''MW30'') Or InNet(''MW31'') Or InNet(''MW32'') Or InNet(''MW34'') Or InNet(''MW35'') Or InNet(''S02'') Or InNet(''S05'') Or InNet(''S09'') Or InNet(''S11'') Or InNet(''S12'') Or InNet(''S13'') Or InNet(''S15'') Or InNet(''S16'') Or InNet(''S21'') Or InNet(''S24'') Or InNet(''S28'') Or InNet(''S30'') Or InNet(''S31'') Or InNet(''S32'') Or InNet(''S34'') Or InNet(''S35''))';DCScope:='(InNet(''DC01'') Or InNet(''DC02'') Or InNet(''DC03'') Or InNet(''DC04'') Or InNet(''DC05'') Or InNet(''DC06'') Or InNet(''DC07'') Or InNet(''DC08'') Or InNet(''DC09'') Or InNet(''DC10'') Or InNet(''DC11'') Or InNet(''DC12'') Or InNet(''DC13'') Or InNet(''DC14'') Or InNet(''DC15'') Or InNet(''DC16'') Or InNet(''DC17'') Or InNet(''DC18'') Or InNet(''DC19'') Or InNet(''DC20'') Or InNet(''DC21'') Or InNet(''DC22'') Or InNet(''DC23'') Or InNet(''DC24'') Or InNet(''DC25'') Or InNet(''DC26'') Or InNet(''DC27'') Or InNet(''DC28'') Or InNet(''DC29'') Or InNet(''DC30'') Or InNet(''DC31'') Or InNet(''DC32'') Or InNet(''DC33'') Or InNet(''DC34'') Or InNet(''DC35'') Or InNet(''DC36'') Or InNet(''DC37'') Or InNet(''DC38''))';SmallScope:='IsVia And (InNet(''DC01'') Or InNet(''DC02'') Or InNet(''DC03'') Or InNet(''DC04'') Or InNet(''DC05'') Or InNet(''DC06'') Or InNet(''DC07'') Or InNet(''DC08'') Or InNet(''DC09'') Or InNet(''DC10'') Or InNet(''DC11'') Or InNet(''DC12'') Or InNet(''DC13'') Or InNet(''DC14'') Or InNet(''DC15'') Or InNet(''DC16'') Or InNet(''DC17'') Or InNet(''DC18'') Or InNet(''DC19'') Or InNet(''DC20'') Or InNet(''DC21'') Or InNet(''DC22'') Or InNet(''DC23'') Or InNet(''DC24'') Or InNet(''DC25'') Or InNet(''DC26'') Or InNet(''DC27'') Or InNet(''DC28'') Or InNet(''DC29'') Or InNet(''DC30'') Or InNet(''DC31'') Or InNet(''DC32'') Or InNet(''DC33'') Or InNet(''DC34'') Or InNet(''DC35'') Or InNet(''DC36'') Or InNet(''DC37'') Or InNet(''DC38'')) And InRegionAbsolute(90.551080315,91.929137008,688.976319685,275.590562992)';
PCBServer.PreProcess;Try
R:=FindRule('RF_50OHM_WIDTH');R.Scope1Expression:=RFScope;W:=R;W.MinWidth[eBottomLayer]:=MMsToCoord(0.11);W.MaxWidth[eBottomLayer]:=MMsToCoord(0.11);W.FavoredWidth[eBottomLayer]:=MMsToCoord(0.11);R.DRCEnabled:=True;
R:=FindRule('QD38_DC_WIDTH');If R=Nil Then Begin R:=PCBServer.PCBRuleFactory(eRule_MaxMinWidth);R.Name:='QD38_DC_WIDTH';RegisterRule(R);End;R.Scope1Expression:=DCScope;R.Scope2Expression:='All';R.DRCEnabled:=True;W:=R;
W.MinWidth[eTopLayer]:=MMsToCoord(0.15);W.MaxWidth[eTopLayer]:=MMsToCoord(0.15);W.FavoredWidth[eTopLayer]:=MMsToCoord(0.15);
W.MinWidth[eMidLayer1]:=MMsToCoord(0.125);W.MaxWidth[eMidLayer1]:=MMsToCoord(0.125);W.FavoredWidth[eMidLayer1]:=MMsToCoord(0.125);
W.MinWidth[eMidLayer3]:=MMsToCoord(0.125);W.MaxWidth[eMidLayer3]:=MMsToCoord(0.125);W.FavoredWidth[eMidLayer3]:=MMsToCoord(0.125);
W.MinWidth[eBottomLayer]:=MMsToCoord(0.125);W.MaxWidth[eBottomLayer]:=MMsToCoord(0.125);W.FavoredWidth[eBottomLayer]:=MMsToCoord(0.125);
R:=FindRule('Width');R.Scope1Expression:='Not ('+RFScope+') And Not ('+DCScope+')';
R:=FindRule('RoutingVias');R.Scope1Expression:='Not (IsVia And InNet(''GND'')) And Not (IsVia And (InNet(''DC01'') Or InNet(''DC02'') Or InNet(''DC03'') Or InNet(''DC04'') Or InNet(''DC05'') Or InNet(''DC06'') Or InNet(''DC07'') Or InNet(''DC08'') Or InNet(''DC09'') Or InNet(''DC10'') Or InNet(''DC11'') Or InNet(''DC12'') Or InNet(''DC13'') Or InNet(''DC14'') Or InNet(''DC15'') Or InNet(''DC16'') Or InNet(''DC17'') Or InNet(''DC18'') Or InNet(''DC19'') Or InNet(''DC20'') Or InNet(''DC21'') Or InNet(''DC22'') Or InNet(''DC23'') Or InNet(''DC24'') Or InNet(''DC25'') Or InNet(''DC26'') Or InNet(''DC27'') Or InNet(''DC28'') Or InNet(''DC29'') Or InNet(''DC30'') Or InNet(''DC31'') Or InNet(''DC32'') Or InNet(''DC33'') Or InNet(''DC34'') Or InNet(''DC35'') Or InNet(''DC36'') Or InNet(''DC37'') Or InNet(''DC38'')) And InRegionAbsolute(90.551080315,91.929137008,688.976319685,275.590562992))';
R:=FindRule('QD38_ZIF_VIA_0P4_0P2');If R=Nil Then Begin R:=PCBServer.PCBRuleFactory(eRule_RoutingViaStyle);R.Name:='QD38_ZIF_VIA_0P4_0P2';RegisterRule(R);End;R.Scope1Expression:=SmallScope;R.Scope2Expression:='All';R.DRCEnabled:=True;VR:=R;VR.MinWidth:=MMsToCoord(0.4);VR.MaxWidth:=MMsToCoord(0.4);VR.PreferedWidth:=MMsToCoord(0.4);VR.MinHoleWidth:=MMsToCoord(0.2);VR.MaxHoleWidth:=MMsToCoord(0.2);VR.PreferedHoleWidth:=MMsToCoord(0.2);
R:=FindRule('RoutingVias');VRDefault:=R;VR.ViaStyle:=VRDefault.ViaStyle;
R:=FindRule('RF_SHIELD_L5_L6');VR:=R;VR.ViaStyle:=eViaBlindBuriedPair;VR.MinWidth:=MMsToCoord(0.25);VR.MaxWidth:=MMsToCoord(0.25);VR.PreferedWidth:=MMsToCoord(0.25);VR.MinHoleWidth:=MMsToCoord(0.1);VR.MaxHoleWidth:=MMsToCoord(0.1);VR.PreferedHoleWidth:=MMsToCoord(0.1);R.DRCEnabled:=True;
R:=FindRule('Clearance');CL:=R;CL.Gap:=MMsToCoord(0.15);
R:=FindRule('RF_CPW_GND_GAP_0P2');CL:=R;CL.Gap:=MMsToCoord(0.2);
R:=FindRule('DC_GND_GAP_0P2');CL:=R;CL.Gap:=MMsToCoord(0.2);
Finally PCBServer.PostProcess;End;
I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;While R<>Nil Do Begin RuleLog.Add('RULE|'+R.Name+'|'+R.Scope1Expression+'|'+R.Scope2Expression);R:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);
RuleBoard.RebuildPadCaches;RuleBoard.SetState_DocumentHasChanged;RuleBoard.ViewManager_FullUpdate;RuleBoard.GraphicallyInvalidate;RuleLog.Add('COMPLETE_NOT_SAVED');RuleLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_rules_log.txt');RuleLog.Free;End;