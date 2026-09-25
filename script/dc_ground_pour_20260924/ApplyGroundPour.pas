Var PourLog:TStringList;
Procedure PourMark(S:String);
Begin
 PourLog.Add(S);
 PourLog.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\dc_ground_pour_20260924\apply_native.txt');
End;

Function GroundNet(B:IPCB_Board):IPCB_Net;
Var I:IPCB_BoardIterator;N:IPCB_Net;
Begin
 Result:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;
 I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin If N.Name='GND' Then Result:=N;N:=I.NextPCBObject;End;
 B.BoardIterator_Destroy(I);
End;

Procedure AddGround(B:IPCB_Board;GN:IPCB_Net;L:TLayer;S:String);
Var I:IPCB_BoardIterator;Poly:IPCB_Polygon;Seg:TPolySegment;
Begin
 I:=B.BoardIterator_Create;I.SetState_FilterAll;
 I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
 While Poly<>Nil Do Begin
  If Poly.Layer=L Then Begin
   B.BoardIterator_Destroy(I);PourMark('STOP_EXISTING_POLYGON_ON_'+S);Exit;
  End;
  Poly:=I.NextPCBObject;
 End;
 B.BoardIterator_Destroy(I);
 Poly:=PCBServer.PCBObjectFactory(ePolyObject,eNoDimension,eCreate_Default);
 Poly.Layer:=L;Poly.Net:=GN;Poly.Name:=S;
 Poly.PolygonType:=eSignalLayerPolygon;Poly.PolyHatchStyle:=ePolySolid;
 Poly.PourOver:=ePolygonPourOver_SameNet;
 Poly.RemoveDead:=True;Poly.RemoveNarrowNecks:=True;
 Poly.NeckWidthThreshold:=MMsToCoord(0.127);
 Poly.RemoveIslandsByArea:=True;
 Poly.TrackSize:=MMsToCoord(0.15);Poly.Grid:=MMsToCoord(0.05);
 Poly.PointCount:=4;
 Seg:=Poly.Segments[0];Seg.Kind:=ePolySegmentLine;
 Seg.vx:=MMsToCoord(0.25);Seg.vy:=MMsToCoord(0.25);Poly.Segments[0]:=Seg;
 Seg.vx:=MMsToCoord(19.25);Poly.Segments[1]:=Seg;
 Seg.vy:=MMsToCoord(67.65);Poly.Segments[2]:=Seg;
 Seg.vx:=MMsToCoord(0.25);Poly.Segments[3]:=Seg;
 B.AddPCBObject(Poly);
 PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,Poly.I_ObjectAddress);
 Poly.SetState_CopperPourInvalid;Poly.Rebuild;PourMark('REPOURED='+S);
End;

Procedure ApplyGroundPour;
Var B:IPCB_Board;D:IServerDocument;GN:IPCB_Net;P:String;
Begin
 P:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 PourLog:=TStringList.Create;PourMark('START');
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 GN:=GroundNet(B);If GN=Nil Then Exit;
 PCBServer.PreProcess;
 Try
  AddGround(B,GN,eMidLayer1,'L2_DC_GND');
  AddGround(B,GN,eMidLayer3,'L4_DC_GND');
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;
 B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');
 AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 PourMark('SAVED');PourMark('COMPLETE');PourLog.Free;
End;
