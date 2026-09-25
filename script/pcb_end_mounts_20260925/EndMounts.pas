Var MountLog:TStringList;
Procedure MountMark(S:String);
Begin
 MountLog.Add(S);
 MountLog.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\pcb_end_mounts_20260925\mount_native.txt');
End;

Procedure AddMount(B:IPCB_Board;G:IPCB_Net;XMM:Double;N:String);
Var P:IPCB_Pad;
Begin
 P:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);
 P.Layer:=eMultiLayer;P.Mode:=ePadMode_Simple;
 P.X:=MMsToCoord(XMM);P.Y:=MMsToCoord(1.4);
 P.TopXSize:=MMsToCoord(2.6);P.TopYSize:=MMsToCoord(2.6);
 P.MidXSize:=MMsToCoord(2.6);P.MidYSize:=MMsToCoord(2.6);
 P.BotXSize:=MMsToCoord(2.6);P.BotYSize:=MMsToCoord(2.6);
 P.TopShape:=eRounded;P.MidShape:=eRounded;P.BotShape:=eRounded;
 P.HoleSize:=MMsToCoord(2.2);P.Plated:=True;P.Name:=N;P.Net:=G;
 P.SetState_IsTopPasteEnabled(False);P.SetState_IsBottomPasteEnabled(False);
 P.SetState_PasteMaskEnabled(False);
 B.AddPCBObject(P);
 PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);
 MountMark('ADDED='+N+';X='+FloatToStr(XMM)+';Y=1.4;HOLE=2.2;LAND=2.6;GND');
End;

Procedure AddEndMounts;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;
 P:IPCB_Pad;G:IPCB_Net;N:IPCB_Net;Poly:IPCB_Polygon;Path:String;Count:Integer;
Begin
 Path:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 MountLog:=TStringList.Create;MountMark('START');
 D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));
 Count:=0;P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  If (P.Name='MH7') Or (P.Name='MH8') Then Begin MountMark('ALREADY_PRESENT');Exit;End;
  Inc(Count);P:=I.NextPCBObject;
 End;
 B.BoardIterator_Destroy(I);If Count<>147 Then Begin MountMark('WRONG_PAD_COUNT');Exit;End;
 G:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));
 N:=I.FirstPCBObject;While N<>Nil Do Begin If N.Name='GND' Then G:=N;N:=I.NextPCBObject;End;
 B.BoardIterator_Destroy(I);If G=Nil Then Exit;
 PCBServer.PreProcess;
 Try
  AddMount(B,G,1.6,'MH7');AddMount(B,G,17.9,'MH8');
  B.RebuildPadCaches;B.InvalidateScopeTester;B.ValidateScopeTester;
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));
  Poly:=I.FirstPCBObject;Count:=0;
  While Poly<>Nil Do Begin
   Poly.SetState_CopperPourInvalid;Poly.Rebuild;Inc(Count);
   MountMark('REPOURED='+Poly.Name);Poly:=I.NextPCBObject;
  End;
  B.BoardIterator_Destroy(I);MountMark('POUR_COUNT='+IntToStr(Count));
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');
 RunProcess('WorkspaceManager:SaveObject');MountMark('SAVED');MountMark('COMPLETE');MountLog.Free;
End;
