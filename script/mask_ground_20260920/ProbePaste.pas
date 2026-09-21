Procedure ProbePaste;
Var P:IPCB_Pad;V:IPCB_Via;L:TStringList;
Begin
 L:=TStringList.Create;
 P:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);
 V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);
 Try
  P.SetState_IsTopPasteEnabled(False);L.Add('PAD_TOP_DISABLED');
  P.SetState_IsBottomPasteEnabled(False);L.Add('PAD_BOTTOM_DISABLED');
  P.SetState_PasteMaskEnabled(False);L.Add('PAD_GLOBAL_DISABLED');
  P.SetState_PasteMaskUsePercent(False);
  P.SetState_PasteMaskExpansion(0);
  If P.GetState_IsTopPasteEnabled Then L.Add('PAD_TOP_TRUE') Else L.Add('PAD_TOP_FALSE');
  If P.GetState_IsBottomPasteEnabled Then L.Add('PAD_BOTTOM_TRUE') Else L.Add('PAD_BOTTOM_FALSE');
  If P.GetState_PasteMaskEnabled Then L.Add('PAD_GLOBAL_TRUE') Else L.Add('PAD_GLOBAL_FALSE');
  V.SetState_PasteMaskEnabled(False);L.Add('VIA_GLOBAL_DISABLED');
  V.SetState_PasteMaskUsePercent(False);V.SetState_PasteMaskExpansion(0);
  If V.GetState_PasteMaskEnabled Then L.Add('VIA_GLOBAL_TRUE') Else L.Add('VIA_GLOBAL_FALSE');
  L.Add('COMPLETE');
 Except
  L.Add('API_FAILED');
 End;
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\mask_ground_20260920\paste_probe.txt');
 L.Free;
End;
