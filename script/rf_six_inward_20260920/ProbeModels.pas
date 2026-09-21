Procedure ProbeModels;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;Body:IPCB_ComponentBody;C:IPCB_Component;M:IPCB_Model;P:TCoordPoint;RX,RY,RZ:Double;DZ:Integer;L:TStringList;
Begin
 D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;L:=TStringList.Create;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
 While Body<>Nil Do Begin C:=Body.Component;If C<>Nil Then If (Copy(C.Name.Text,1,1)='R') Or (Copy(C.Name.Text,1,1)='C') Then Begin
  M:=Body.GetModel;M.GetState(RX,RY,RZ,DZ);P:=M.GetOrigin;L.Add(C.Name.Text+'|'+FloatToStr(RX)+','+FloatToStr(RY)+','+FloatToStr(RZ)+'|'+IntToStr(P.X)+','+IntToStr(P.Y)+'|'+M.GetFileName);
 End;Body:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_model_probe.txt');L.Free;
End;
