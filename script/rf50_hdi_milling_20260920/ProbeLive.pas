Procedure ProbeLive;
Var B:IPCB_Board;I:IPCB_BoardIterator;O:IPCB_Primitive;P:IPCB_Polygon;V:IPCB_Via;L:TStringList;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;L:=TStringList.Create;L.Add(B.FileName);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin L.Add('POLY|'+P.Name+'|'+IntToStr(Ord(P.Layer))+'|'+IntToStr(P.PointCount));P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eArcObject,eTextObject));O:=I.FirstPCBObject;N:=0;
 While O<>Nil Do Begin If (O.Layer=eMechanical2) Or (O.Layer=eMechanical3) Then Begin Inc(N);L.Add('FAB|'+IntToStr(Ord(O.ObjectId))+'|'+IntToStr(Ord(O.Layer)));End;O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;N:=0;
 While V<>Nil Do Begin Inc(N);V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);L.Add('VIAS='+IntToStr(N));
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\rf50_hdi_milling_20260920\live_probe.txt');L.Free;
End;
