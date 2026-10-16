Procedure InspectNativeBaseline;
Var B:IPCB_Board; I:IPCB_BoardIterator; V:IPCB_Via; T:IPCB_Text;
    R:IPCB_Rule; C:IPCB_Component; L:TStringList; N:String;
Begin
 B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;
 L.Add('BOARD|'+B.FileName);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin
  N:='';If V.Net<>Nil Then N:=V.Net.Name;
  L.Add('VIA|'+N+'|'+FloatToStr(CoordToMMs(V.X))+'|'+FloatToStr(CoordToMMs(V.Y))+'|'+IntToStr(V.LowLayer)+'|'+IntToStr(V.HighLayer)+'|'+FloatToStr(CoordToMMs(V.Size))+'|'+FloatToStr(CoordToMMs(V.HoleSize)));
  V:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_baseline.txt');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTextObject));T:=I.FirstPCBObject;
 While T<>Nil Do Begin
  L.Add('TEXT|'+IntToStr(T.Layer)+'|'+T.Text);T:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
 While R<>Nil Do Begin
  L.Add('RULE|'+R.Name+'|'+R.Scope1Expression+'|'+R.Scope2Expression);R:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_baseline.txt');L.Free;
End;
