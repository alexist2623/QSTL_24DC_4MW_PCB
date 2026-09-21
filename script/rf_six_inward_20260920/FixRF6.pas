Function GetNet(B:IPCB_Board;S:String):IPCB_Net;
Var I:IPCB_BoardIterator;N:IPCB_Net;
Begin Result:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin If N.Name=S Then Result:=N;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);End;
Procedure FixRF6;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Pad;C:IPCB_Component;N:IPCB_Net;Poly:IPCB_Polygon;Ns:Array[0..63] Of IPCB_Net;Polys:Array[0..7] Of IPCB_Polygon;NC,NP,J,Found:Integer;S,NetName:String;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>'c:\jeonghyunpark\workspace\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb.pcbdoc' Then Exit;
 L:=TStringList.Create;Found:=0;PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   C:=P.Component;NetName:='';S:='';If C<>Nil Then S:=C.Name.Text;
   If (S='R5') Or (S='R6') Then Begin If P.Name='1' Then NetName:='MW'+Copy(S,2,1) Else If S='R5' Then NetName:='ZIF02' Else NetName:='ZIF04';End;
   If (S='C5') Or (S='C6') Then Begin If P.Name='1' Then NetName:='S'+Copy(S,2,1) Else NetName:='MW'+Copy(S,2,1);End;
   If (S='SMP5') Or (S='SMP6') Then If P.Name='1' Then NetName:='S'+Copy(S,4,1);
   If NetName<>'' Then Begin
    N:=GetNet(B,NetName);If N=Nil Then Begin L.Add('NET_MISSING='+NetName);End Else Begin
     P.Net:=N;P.SetState_InNet(True);Inc(Found);S:=S+'-'+P.Name+'=';If P.Net<>Nil Then S:=S+P.Net.Name Else S:=S+'NONE';L.Add(S);
    End;
   End;
   P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
  While C<>Nil Do Begin
   S:=C.Name.Text;
   If (Copy(S,1,1)='R') Or (Copy(S,1,1)='C') Then Begin
    C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.Size:=MMsToCoord(0.6);C.Name.Width:=MMsToCoord(0.1);C.Name.Rotation:=0;
    If S='R1' Then C.Name.MoveToXY(MMsToCoord(16.8),MMsToCoord(31.7));
    If S='R5' Then C.Name.MoveToXY(MMsToCoord(2.5),MMsToCoord(31.7));
    If S='R2' Then C.Name.MoveToXY(MMsToCoord(18.5),MMsToCoord(43.1));
    If S='R6' Then C.Name.MoveToXY(MMsToCoord(0.6),MMsToCoord(42.4));
    If S='R3' Then C.Name.MoveToXY(MMsToCoord(13.5),MMsToCoord(44.8));
    If S='R4' Then C.Name.MoveToXY(MMsToCoord(5.8),MMsToCoord(45.0));
    If S='C1' Then C.Name.MoveToXY(MMsToCoord(11.2),MMsToCoord(28.0));
    If S='C5' Then C.Name.MoveToXY(MMsToCoord(7.3),MMsToCoord(28.0));
    If S='C2' Then C.Name.MoveToXY(MMsToCoord(17.5),MMsToCoord(38.3));
    If S='C6' Then C.Name.MoveToXY(MMsToCoord(1.0),MMsToCoord(38.0));
    If S='C3' Then C.Name.MoveToXY(MMsToCoord(11.6),MMsToCoord(50.7));
    If S='C4' Then C.Name.MoveToXY(MMsToCoord(7.1),MMsToCoord(50.7));
   End;
   C:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;NP:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NP]:=Poly;Inc(NP);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NP-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 NC:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin Ns[NC]:=N;Inc(NC);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NC-1 Do Begin N:=Ns[J];N.ConnectivelyInValidate;N.Rebuild;End;
 B.ConnectivelyValidateNets;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L.Add('ASSIGNED='+IntToStr(Found));L.Add('NETS_REBUILT='+IntToStr(NC));L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_fix.txt');L.Free;
End;
