Var Log:TStringList;Root:String;PN:Array[1..24] Of String;OX,OY,NX,NY:Array[1..24] Of Integer;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile(Root+'script\rf50_hdi_milling_20260920\native_change.txt');End;
Procedure RegisterObject(B:IPCB_Board;O:IPCB_Primitive);Begin B.AddPCBObject(O);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,O.I_ObjectAddress);End;
Procedure AddShield(B:IPCB_Board;GN:IPCB_Net;X,Y:Integer);
Var V:IPCB_Via;
Begin
 V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=X;V.Y:=Y;V.Mode:=ePadMode_Simple;
 V.Size:=MMsToCoord(0.25);V.HoleSize:=MMsToCoord(0.1);V.LowLayer:=eMidLayer4;V.HighLayer:=eBottomLayer;V.Net:=GN;
 V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V.SetState_PasteMaskEnabled(False);
 RegisterObject(B,V);
End;
Procedure AddFabTrack(B:IPCB_Board;X1,Y1,X2,Y2:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.Layer:=eMechanical2;
 T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(0.01);RegisterObject(B,T);End;
Procedure AddFabArc(B:IPCB_Board;X,Y,A0,A1:Double);
Var A:IPCB_Arc;
Begin A:=PCBServer.PCBObjectFactory(eArcObject,eNoDimension,eCreate_Default);A.Layer:=eMechanical2;A.XCenter:=MMsToCoord(X);A.YCenter:=MMsToCoord(Y);
 A.Radius:=MMsToCoord(0.5);A.StartAngle:=A0;A.EndAngle:=A1;A.LineWidth:=MMsToCoord(0.01);RegisterObject(B,A);End;
Procedure FinishRF50;
Var B:IPCB_Board;K,J,NP,NC:Integer;I,It,It2:IPCB_BoardIterator;V:IPCB_Via;Pad:IPCB_Pad;Comp:IPCB_Component;Track:IPCB_Track;Rule:IPCB_Rule;
 Poly:IPCB_Polygon;GN,Net:IPCB_Net;Seg:TPolySegment;FabText:IPCB_Text;Polys:Array[0..7] Of IPCB_Polygon;Dead:Array[0..23] Of IPCB_Via;NPoly:Integer;
Begin
 Root:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\';B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(Root+'QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 Log:=TStringList.Create;Mark('CONTINUE_START');GN:=Nil;
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eNetObject));Net:=It.FirstPCBObject;
 While Net<>Nil Do Begin If Net.Name='GND' Then GN:=Net;Net:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);
 NC:=0;It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=It.FirstPCBObject;
 While Pad<>Nil Do Begin Comp:=Pad.Component;If Comp<>Nil Then If Copy(Comp.Name.Text,1,1)='C' Then Begin
  It2:=B.BoardIterator_Create;It2.SetState_FilterAll;It2.AddFilter_ObjectSet(MkSet(eViaObject));V:=It2.FirstPCBObject;
  While V<>Nil Do Begin If (Abs(V.X-Pad.X)<2) And (Abs(V.Y-Pad.Y)<2) Then Begin Dead[NC]:=V;Inc(NC);End;V:=It2.NextPCBObject;End;B.BoardIterator_Destroy(It2);
 End;Pad:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);Mark('CAP_VIAS='+IntToStr(NC));
 PCBServer.PreProcess;
 Try
  For K:=0 To NC-1 Do B.RemovePCBObject(Dead[K]);Mark('CAP_VIAS_REMOVED');

 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eTrackObject));Track:=It.FirstPCBObject;
 While Track<>Nil Do Begin If Track.Net<>Nil Then Begin Track.BeginModify;
If Track.Net.Name='ZIF23' Then Begin If (Abs(Track.X1-5118110)<2) And (Abs(Track.Y1-18149607)<2) Then Begin Track.X1:=5157480;Track.Y1:=18110237;End;If (Abs(Track.X2-5118110)<2) And (Abs(Track.Y2-18149607)<2) Then Begin Track.X2:=5157480;Track.Y2:=18110237;End;End;
If Track.Net.Name='ZIF23' Then Begin If (Abs(Track.X1-5118110)<2) And (Abs(Track.Y1-13248031)<2) Then Begin Track.X1:=5157480;Track.Y1:=13287401;End;If (Abs(Track.X2-5118110)<2) And (Abs(Track.Y2-13248031)<2) Then Begin Track.X2:=5157480;Track.Y2:=13287401;End;End;
If Track.Net.Name='ZIF26' Then Begin If (Abs(Track.X1-2539370)<2) And (Abs(Track.Y1-18129921)<2) Then Begin Track.X1:=2519685;Track.Y1:=18110236;End;If (Abs(Track.X2-2539370)<2) And (Abs(Track.Y2-18129921)<2) Then Begin Track.X2:=2519685;Track.Y2:=18110236;End;End;
If Track.Net.Name='ZIF26' Then Begin If (Abs(Track.X1-2539370)<2) And (Abs(Track.Y1-14015748)<2) Then Begin Track.X1:=2519685;Track.Y1:=14035433;End;If (Abs(Track.X2-2539370)<2) And (Abs(Track.Y2-14015748)<2) Then Begin Track.X2:=2519685;Track.Y2:=14035433;End;End;
 Track.EndModify;End;Track:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);Mark('DC_CLEARANCE_ADJUSTED');
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=It.FirstPCBObject;
 While Rule<>Nil Do Begin If Rule.Name='RF_CPW_GND_GAP_0P2' Then Rule.NetScope:=eNetScope_DifferentNetsOnly;Rule:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);
  Poly:=PCBServer.PCBObjectFactory(ePolyObject,eNoDimension,eCreate_Default);Mark('POLY_STEP_1');Poly.Layer:=eBottomLayer;Mark('POLY_STEP_2');Poly.Net:=GN;Mark('POLY_STEP_3');Poly.Name:='L6_RF_COPLANAR_GND';Mark('POLY_STEP_4');Poly.PolygonType:=eSignalLayerPolygon;Mark('POLY_STEP_5');Poly.PolyHatchStyle:=ePolySolid;Mark('POLY_STEP_6');Poly.PourOver:=ePolygonPourOver_SameNet;Mark('POLY_STEP_7');Poly.RemoveDead:=True;Mark('POLY_STEP_8');Poly.RemoveNarrowNecks:=True;Mark('POLY_STEP_9');Poly.NeckWidthThreshold:=MMsToCoord(0.1);Mark('POLY_STEP_10');Poly.RemoveIslandsByArea:=False;Mark('POLY_STEP_11');Poly.TrackSize:=MMsToCoord(0.1);Mark('POLY_STEP_12');Poly.Grid:=MMsToCoord(0.1);Mark('POLY_STEP_13');Poly.PointCount:=4;
  Seg:=Poly.Segments[0];Seg.Kind:=ePolySegmentLine;Seg.vx:=MMsToCoord(0.25);Seg.vy:=MMsToCoord(0.25);Mark('POLY_STEP_14');Poly.Segments[0]:=Seg;
  Seg.vx:=MMsToCoord(19.25);Mark('POLY_STEP_15');Poly.Segments[1]:=Seg;Seg.vy:=MMsToCoord(67.65);Mark('POLY_STEP_16');Poly.Segments[2]:=Seg;Seg.vx:=MMsToCoord(0.25);Mark('POLY_STEP_17');Poly.Segments[3]:=Seg;RegisterObject(B,Poly);
 AddFabTrack(B,8.1,40.35,11.4,40.35);
 AddFabTrack(B,11.9,40.85,11.9,44.15);
 AddFabTrack(B,11.4,44.65,8.1,44.65);
 AddFabTrack(B,7.6,44.15,7.6,40.85);
 AddFabArc(B,11.4,40.85,270,360);
 AddFabArc(B,11.4,44.15,0,90);
 AddFabArc(B,8.1,44.15,90,180);
 AddFabArc(B,8.1,40.85,180,270);
  FabText:=PCBServer.PCBObjectFactory(eTextObject,eNoDimension,eCreate_Default);FabText.Layer:=eMechanical3;FabText.X:=MMsToCoord(21);FabText.Y:=MMsToCoord(43);FabText.Size:=MMsToCoord(0.8);FabText.Width:=MMsToCoord(0.12);FabText.Text:='BOTTOM BLIND SLOT: 4.3 x 4.3, R0.5, DEPTH 1.2 mm; NON-PLATED';RegisterObject(B,FabText);
  Mark('CAVITY_ANNOTATED');
  NPoly:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin Polys[NPoly]:=Poly;Inc(NPoly);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For J:=0 To NPoly-1 Do Begin Poly:=Polys[J];Mark('POLY_STEP_18');Poly.SetState_CopperPourInvalid;Mark('POLY_STEP_19');Poly.Rebuild;Mark('REPOURED='+Poly.Name);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Mark('SAVED');Mark('COMPLETE');Log.Free;
End;

Procedure RunSafely;
Begin
 Try FinishRF50; Except Mark('CAUGHT_NATIVE_FAILURE');End;
End;
