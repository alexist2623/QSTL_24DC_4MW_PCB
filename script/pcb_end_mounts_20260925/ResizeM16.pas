Procedure ResizeM16;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Pad;Poly:IPCB_Polygon;Path:String;Count:Integer;L:TStringList;
Begin
 Path:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
 Count:=0;PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   If (P.Name='MH7') Or (P.Name='MH8') Then Begin
    P.Y:=MMsToCoord(1.2);P.HoleSize:=MMsToCoord(1.8);
    P.TopXSize:=MMsToCoord(2.2);P.TopYSize:=MMsToCoord(2.2);
    P.MidXSize:=MMsToCoord(2.2);P.MidYSize:=MMsToCoord(2.2);
    P.BotXSize:=MMsToCoord(2.2);P.BotYSize:=MMsToCoord(2.2);Inc(Count);
   End;
   P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  B.RebuildPadCaches;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin Poly.SetState_CopperPourInvalid;Poly.Rebuild;Poly:=I.NextPCBObject;End;
  B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.SetState_DocumentHasChanged;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L:=TStringList.Create;L.Add('M1.6;HOLE=1.8;LAND=2.2;Y=1.2;COUNT='+IntToStr(Count));L.Add('COMPLETE');
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\resize_native.txt');L.Free;
End;
