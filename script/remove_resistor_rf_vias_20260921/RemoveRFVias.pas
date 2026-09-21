Var Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\remove_resistor_rf_vias_20260921\native_change.txt');End;
Procedure RemoveRFVias;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;Poly:IPCB_Polygon;Net:IPCB_Net;
Dead:Array[1..6] Of IPCB_Via;Found:Array[1..6] Of Boolean;VX,VY:Array[1..6] Of Integer;VN:Array[1..6] Of String;Polys:Array[0..7] Of IPCB_Polygon;Nets:Array[0..63] Of IPCB_Net;N,NV,NP,NN,J:Integer;
Begin
 Log:=TStringList.Create;Mark('START');D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 VX[1]:=5295276;VY[1]:=12204725;VN[1]:='MW1';
VX[2]:=6220472;VY[2]:=16318898;VN[2]:='MW2';
VX[3]:=4330709;VY[3]:=19055119;VN[3]:='MW3';
VX[4]:=3346457;VY[4]:=19055119;VN[4]:='MW4';
VX[5]:=2244094;VY[5]:=12204725;VN[5]:='MW5';
VX[6]:=1456693;VY[6]:=16043307;VN[6]:='MW6';
 For J:=1 To 6 Do Found[J]:=False;N:=0;NV:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin Inc(NV);If V.Net<>Nil Then For J:=1 To 6 Do If V.Net.Name=VN[J] Then If (Abs(V.X-VX[J])<4) And (Abs(V.Y-VY[J])<4) Then Begin If Found[J] Then Begin Mark('DUPLICATE_TARGET');Exit;End;Found[J]:=True;Dead[J]:=V;Inc(N);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('TOTAL_VIAS='+IntToStr(NV));Mark('RF_RESISTOR_TARGETS='+IntToStr(N));If (NV<>530) Or (N<>6) Then Begin Mark('GUARD_STOP');Exit;End;
 PCBServer.PreProcess;Try
 For J:=1 To 6 Do Begin B.RemovePCBObject(Dead[J]);Mark('REMOVED='+VN[J]);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;NP:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NP]:=Poly;Inc(NP);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NP-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;Mark('REPOURED='+Polys[J].Name);End;
 NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));Net:=I.FirstPCBObject;While Net<>Nil Do Begin Nets[NN]:=Net;Inc(NN);Net:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin Nets[J].ConnectivelyInValidate;Nets[J].Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED');Mark('COMPLETE');Log.Free;
End;
Procedure RunSafely;Begin Try RemoveRFVias;Except Mark('CAUGHT_NATIVE_FAILURE');End;End;
