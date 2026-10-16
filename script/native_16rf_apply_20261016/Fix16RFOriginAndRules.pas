Procedure Fix16RFOriginAndRules;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;C,J:IPCB_Component;
 R:IPCB_Rule;W:IPCB_MaxMinWidthConstraint;RR:IPCB_RoutingLayersRule;
 L:TStringList;NC,NR:Integer;
Begin
 L:=TStringList.Create;
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 NC:=0;J:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);If C.Name.Text='J1' Then J:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If (NC<>50) Or (J=Nil) Then Exit;
 L.Add('J1_BEFORE|'+FloatToStr(CoordToMMs(J.X))+'|'+FloatToStr(CoordToMMs(J.Y)));
 If Abs(CoordToMMs(J.Y)-(-7.125001280))>0.00001 Then Begin L.Add('GUARD_FAILED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\native_16rf_apply_20261016\origin_rule_fix.txt');L.Free;Exit;End;
 PCBServer.PreProcess;
 Try
  J.MoveToXY(MMsToCoord(9.750000820),MMsToCoord(-6.724999540));
  NR:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
  While R<>Nil Do Begin
   If R.Name='QD38_DC_WIDTH' Then Begin W:=R;
    W.MinWidth[eMidLayer2]:=MMsToCoord(0.125);W.MaxWidth[eMidLayer2]:=MMsToCoord(0.125);W.FavoredWidth[eMidLayer2]:=MMsToCoord(0.125);Inc(NR);End;
   If R.RuleKind=eRule_RoutingLayers Then Begin RR:=R;
    RR.SetState_RoutingLayers(eMidLayer2,True);RR.SetState_RoutingLayers(eMidLayer3,False);
    R.Comment:='RF on Bottom; DC on L2/L3 with short Top ZIF pad escapes. L1/L4/L5 GND.';
    L.Add('ROUTING_LAYERS|'+R.Name);End;
   R:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.InvalidateScopeTester;B.ValidateScopeTester;B.RebuildPadCaches;B.SetState_DocumentHasChanged;
 B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 L.Add('WIDTH_RULES_UPDATED='+IntToStr(NR));L.Add('J1_AFTER|'+FloatToStr(CoordToMMs(J.X))+'|'+FloatToStr(CoordToMMs(J.Y)));
 L.Add('COMPLETE_NOT_SAVED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\native_16rf_apply_20261016\origin_rule_fix.txt');L.Free;
End;
