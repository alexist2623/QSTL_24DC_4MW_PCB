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
 L.Add('COMPLETE');L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\rc_mask_clearance_20260921\native_paste_audit.txt');L.Free;
End;
