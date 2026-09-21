{ PREPARATION ONLY: not executed. Use only on the guarded original target board.
  AD26 SDK Interfaces.dll confirms IPCB_Arc setters and legacy layer interfaces.
  Official CreatePCBObjects.PAS and CopyBoardOutlineForm.pas confirm XCenter,
  YCenter, LineWidth, Radius, StartAngle, EndAngle DelphiScript property names.
  Caller supplies validated geometry, existing net objects and a Pre/PostProcess
  transaction. Physical L2=eMidLayer1; physical L4=eMidLayer3.
  A circular arc is counter-clockwise from StartAngle to EndAngle in PCB XY.
  For a clockwise requested segment, swap its endpoints/angles; copper geometry
  has no electrical direction. Verify generated arc endpoints before applying. }

Function AddRFArc(Board : IPCB_Board; NetObj : IPCB_Net; LayerId : TLayer;
                  CXMM, CYMM, RMM, WidthMM, A0Deg, A1Deg : Double) : IPCB_Arc;
Var A : IPCB_Arc;
Begin
    Result := Nil;
    If (Board = Nil) Or (NetObj = Nil) Or (RMM <= 0) Or (WidthMM <= 0) Then Exit;
    A := PCBServer.PCBObjectFactory(eArcObject, eNoDimension, eCreate_Default);
    A.XCenter := MMsToCoord(CXMM);
    A.YCenter := MMsToCoord(CYMM);
    A.Radius := MMsToCoord(RMM);
    A.LineWidth := MMsToCoord(WidthMM);
    A.StartAngle := A0Deg;
    A.EndAngle := A1Deg;
    A.Layer := LayerId;
    A.Net := NetObj;
    Board.AddPCBObject(A);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                 PCBM_BoardRegisteration, A.I_ObjectAddress);
    Result := A;
End;

Function AddRFTrack(Board : IPCB_Board; NetObj : IPCB_Net; LayerId : TLayer;
                    X1MM, Y1MM, X2MM, Y2MM, WidthMM : Double) : IPCB_Track;
Var T : IPCB_Track;
Begin
    T := PCBServer.PCBObjectFactory(eTrackObject, eNoDimension, eCreate_Default);
    T.X1 := MMsToCoord(X1MM); T.Y1 := MMsToCoord(Y1MM);
    T.X2 := MMsToCoord(X2MM); T.Y2 := MMsToCoord(Y2MM);
    T.Width := MMsToCoord(WidthMM); T.Layer := LayerId; T.Net := NetObj;
    Board.AddPCBObject(T);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                 PCBM_BoardRegisteration, T.I_ObjectAddress);
    Result := T;
End;

Function AddShieldVia(Board : IPCB_Board; GroundNet : IPCB_Net;
                      XMM, YMM, DiameterMM, HoleMM : Double) : IPCB_Via;
Var V : IPCB_Via;
Begin
    Result := Nil;
    If (GroundNet = Nil) Or (DiameterMM <= HoleMM) Or (HoleMM <= 0) Then Exit;
    V := PCBServer.PCBObjectFactory(eViaObject, eNoDimension, eCreate_Default);
    V.X := MMsToCoord(XMM); V.Y := MMsToCoord(YMM);
    V.Mode := ePadMode_Simple;
    V.Size := MMsToCoord(DiameterMM); V.HoleSize := MMsToCoord(HoleMM);
    V.LowLayer := eTopLayer; V.HighLayer := eBottomLayer; V.Net := GroundNet;
    Board.AddPCBObject(V);
    PCBServer.SendMessageToRobots(Board.I_ObjectAddress, c_Broadcast,
                                 PCBM_BoardRegisteration, V.I_ObjectAddress);
    Result := V;
End;

{ Layer material setters verified by AD26 IPCB_DielectricLayer metadata:
    D.SetState_DielectricMaterial('FR-4');
    D.SetState_DielectricConstant(4.8);
    D.SetState_DielectricHeight(MMsToCoord(0.32004));
    D.SetState_DielectricLossTangent(Df);
  Do NOT set Df to a guessed value. Current generic FR-4/Dk4.8 is a nominal draft.

  IPCB_MatchedNetLengthsConstraint exposes SetState_Tolerance(TCoord) only in the
  legacy scripting SDK. It does not expose a verified delay-in-ps setter here.
  Do not pass a picosecond value to this length-valued setter. Configure a real
  1ps xSignal delay rule with the modern native rule UI if available. A temporary
  length tolerance is meaningful only for identical stack/layer/via topology.

  Ground fences need poured connected GND copper, not merely grounded net labels.
  Run native DRC and saved-native connectivity verification after repour/save.
}
