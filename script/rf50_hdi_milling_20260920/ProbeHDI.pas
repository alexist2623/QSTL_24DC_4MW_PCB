Procedure ProbeHDI;
Var B:IPCB_Board;S:IPCB_LayerStack_V7;L:IPCB_LayerObject_V7;D:IPCB_DielectricObject;V:IPCB_Via;Log:TStringList;Params:String;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 Log:=TStringList.Create;
 Try
  S:=B.LayerStack_V7;Log.Add('GOT_STACK');L:=S.FirstLayer;Log.Add('GOT_FIRST');N:=0;
  While L<>Nil Do Begin
   Log.Add('LAYER|'+IntToStr(N)+'|'+IntToStr(Ord(L.LayerId)));Log.Add('NAME='+L.Name);Log.Add('COPPER='+IntToStr(L.CopperThickness));
   D:=L.Dielectric;If D<>Nil Then Log.Add('DIELECTRIC|'+IntToStr(D.DielectricHeight)+'|'+D.DielectricMaterial);
   Inc(N);L:=S.NextLayer(L);
  End;
  Log.Add('STACK_COMPLETE');
 Except Log.Add('STACK_API_FAILED');End;
 Try
  V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);
  V.HighLayer:=eMidLayer4;V.LowLayer:=eBottomLayer;
  V.Size:=MMsToCoord(0.25);V.HoleSize:=MMsToCoord(0.1);
  Log.Add('VIA_LAYER_SET');
 Except Log.Add('VIA_API_FAILED');End;
 Try
  Params:='';B.MasterStack.Export_ToParameters(Params);
  Log.Add('STACK_PARAMS='+Params);
 Except Log.Add('STACK_EXPORT_FAILED');End;
 Log.Add('COMPLETE');Log.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\rf50_hdi_milling_20260920\native_probe.txt');Log.Free;
End;
