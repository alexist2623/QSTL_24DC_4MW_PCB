Function BT(V:Boolean):String;Begin If V Then Result:='1' Else Result:='0';End;
Procedure DumpText(Path,OutputPath:String;CloseAfter:Boolean);
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;T:IPCB_Text;L:TStringList;
Begin
 D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 L:=TStringList.Create;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTextObject));T:=I.FirstPCBObject;
 While T<>Nil Do Begin
 L.Add(T.GetState_Text+'|SIZE='+IntToStr(T.GetState_Size)+'|WIDTH='+IntToStr(T.GetState_Width)+'|FONTID='+IntToStr(T.GetState_FontID)+'|TT='+BT(T.GetState_UseTTFonts)+'|FONT='+T.GetState_FontName+'|BARCODEFONT='+T.GetState_BarCodeFontName+'|MIRROR='+BT(T.GetState_Mirror)+'|BOLD='+BT(T.GetState_Bold)+'|ITALIC='+BT(T.GetState_Italic)+'|INVERTED='+BT(T.GetState_Inverted));
 T:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Sort;L.Add('COMPLETE');L.SaveToFile(OutputPath);L.Free;If CloseAfter Then Client.CloseDocument(D);
End;
Procedure AuditText;
Begin
 DumpText('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\remove_resistor_rf_vias_20260921\before.PcbDoc','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\remove_resistor_rf_vias_20260921\text_before.txt',True);
 DumpText('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\remove_resistor_rf_vias_20260921\text_after.txt',False);
End;
