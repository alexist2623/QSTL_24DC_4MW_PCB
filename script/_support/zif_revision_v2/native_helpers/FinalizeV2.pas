{ AD26 helper TEMPLATE ONLY. Never executed by its author.
  No parameterless entry point, file save, current-document switch, or UI call.
  Caller must guard its NEW v2 working copy, collect/replace old routes first,
  and wrap mutations in PCBServer.PreProcess / PCBServer.PostProcess.
  Methods/enums checked against the installed AD26 SDK; native script binding
  and CAM output still require the caller's scratch-copy round-trip check. }

Function V2EnsureGndViaSolidRule(B:IPCB_Board; Log:TStringList):Boolean;
Var It:IPCB_BoardIterator; R,D:IPCB_Rule;
    Solid:IPCB_PolygonConnectStyleRule; V:IPCB_Via;
    Count,Wrong:Integer;
Begin
 Result:=False;Solid:=Nil;
 It:=B.BoardIterator_Create;
 It.AddFilter_ObjectSet(MkSet(eRuleObject));
 It.AddFilter_LayerSet(AllLayers);It.AddFilter_Method(eProcessAll);
 R:=It.FirstPCBObject;
 While R<>Nil Do Begin
  If R.Name='ZIF24V2_GND_VIA_SOLID' Then Begin
   If R.RuleKind<>eRule_PolygonConnectStyle Then Begin
    B.BoardIterator_Destroy(It);Log.Add('ERROR_RULE_NAME_KIND');Exit;
   End;
   Solid:=R;
  End;
  R:=It.NextPCBObject;
 End;
 B.BoardIterator_Destroy(It);
 If Solid=Nil Then Begin
  Solid:=PCBServer.PCBRuleFactory(eRule_PolygonConnectStyle);
  Solid.Name:='ZIF24V2_GND_VIA_SOLID';
  Solid.Scope1Expression:='IsVia And InNet(''GND'')';
  Solid.Scope2Expression:='All';
  Solid.ConnectStyle:=eDirectConnectToPlane;
  Solid.DRCEnabled:=True;
  Solid.Comment:='Solid GND via connection only; component pads keep their existing rules.';
  B.AddPCBObject(Solid);
  PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,Solid.I_ObjectAddress);
 End Else Begin
  Solid.BeginModify;
  Try
   Solid.Scope1Expression:='IsVia And InNet(''GND'')';
   Solid.Scope2Expression:='All';
   Solid.ConnectStyle:=eDirectConnectToPlane;
   Solid.DRCEnabled:=True;
  Finally Solid.EndModify;End;
 End;
 B.InvalidateScopeTester;B.ValidateScopeTester;
 Log.Add('SOLID_RULE_PRIORITY='+IntToStr(Solid.Priority));
 Count:=0;Wrong:=0;
 It:=B.BoardIterator_Create;
 It.AddFilter_ObjectSet(MkSet(eViaObject));
 It.AddFilter_LayerSet(AllLayers);It.AddFilter_Method(eProcessAll);
 V:=It.FirstPCBObject;
 While V<>Nil Do Begin
  If V.Net<>Nil Then If V.Net.Name='GND' Then Begin
   Inc(Count);D:=B.FindDominantRuleForObject(V,eRule_PolygonConnectStyle);
   If D=Nil Then Inc(Wrong)
   Else If D.Name<>Solid.Name Then Begin
    Inc(Wrong);Log.Add('ERROR_DOMINANT_RULE='+D.Name);
   End;
  End;
  V:=It.NextPCBObject;
 End;
 B.BoardIterator_Destroy(It);
 Log.Add('GND_VIAS='+IntToStr(Count)+'|WRONG_RULE='+IntToStr(Wrong));
 { Rule priority is read-only in the exposed SDK. Do not pretend Priority:=1
   exists. If Wrong<>0, stop before saving and set native rule priority1 or
   prepare a copied Rules6/Data change. No general pad rule is modified here. }
 Result:=(Count>0) And (Wrong=0);
End;

Procedure V2AddPasteAperture(B:IPCB_Board; V:IPCB_Via;
                           PasteLayer:TLayer; ApertureName:String);
Var R:IPCB_Region; C:IPCB_Contour; I:Integer;
    Angle,Radius:Double;
Begin
 { Explicit positive artwork on the PASTE layer = stencil opening.
   This is independent of SOLDER mask and of the via's old PasteMask cache.
   Aperture diameter equals via copper diameter (zero paste expansion).
   72 vertices approximate a circle with <0.00015mm radial error for D=0.3mm. }
 C:=PCBServer.PCBContourFactory;Radius:=V.Size/2;
 For I:=0 To 71 Do Begin
  Angle:=I*2*3.141592653589793/72;
  C.AddPoint(V.X+Round(Radius*Cos(Angle)),V.Y+Round(Radius*Sin(Angle)));
 End;
 R:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);
 R.Kind:=eRegionKind_Copper;R.Layer:=PasteLayer;
 R.Name:=ApertureName;R.SetOutlineContour(C);
 B.AddPCBObject(R);
 PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,R.I_ObjectAddress);
 { Contour closes implicitly, as in Altium's CreateRegionsFromBitmap sample. }
End;

Function V2RebuildExplicitPasteForAllVias(B:IPCB_Board;
                   ExpectedViaCount:Integer;Log:TStringList):Boolean;
Var It:IPCB_BoardIterator;V:IPCB_Via;R:IPCB_Region;
    Vias:Array[0..4095] Of IPCB_Via;
    Owned:Array[0..8191] Of IPCB_Region;
    N,OldCount,I:Integer;Token:String;
Begin
 Result:=False;N:=0;OldCount:=0;
 { Collect before changing object lists. Only owned aperture regions may
   be replaced. SMP cutouts, polygons and component regions stay untouched. }
 It:=B.BoardIterator_Create;It.AddFilter_ObjectSet(MkSet(eViaObject));
 It.AddFilter_LayerSet(AllLayers);It.AddFilter_Method(eProcessAll);
 V:=It.FirstPCBObject;
 While V<>Nil Do Begin
  If N>=4096 Then Begin B.BoardIterator_Destroy(It);Exit;End;
  If (V.Size<=0) Or (V.HoleSize<=0) Or (V.HoleSize>=V.Size) Then Begin
   B.BoardIterator_Destroy(It);Log.Add('ERROR_VIA_GEOMETRY');Exit;
  End;
  Vias[N]:=V;Inc(N);V:=It.NextPCBObject;
 End;
 B.BoardIterator_Destroy(It);
 If N<>ExpectedViaCount Then Begin Log.Add('ERROR_VIA_COUNT='+IntToStr(N));Exit;End;
 It:=B.BoardIterator_Create;It.AddFilter_ObjectSet(MkSet(eRegionObject));
 It.AddFilter_LayerSet(AllLayers);It.AddFilter_Method(eProcessAll);
 R:=It.FirstPCBObject;
 While R<>Nil Do Begin
  If Pos('ZIFV2_PASTE_',R.Name)=1 Then Begin
   If OldCount>=8192 Then Begin B.BoardIterator_Destroy(It);Exit;End;
   If (R.Layer<>eTopPaste) And (R.Layer<>eBottomPaste) Then Begin
    B.BoardIterator_Destroy(It);Log.Add('ERROR_OWNED_APERTURE_LAYER');Exit;
   End;
   Owned[OldCount]:=R;Inc(OldCount);
  End;
  R:=It.NextPCBObject;
 End;
 B.BoardIterator_Destroy(It);
 For I:=0 To OldCount-1 Do B.RemovePCBObject(Owned[I]);
 For I:=0 To N-1 Do Begin
  V:=Vias[I];Token:=IntToStr(I)+'_'+IntToStr(V.X)+'_'+IntToStr(V.Y);
  V2AddPasteAperture(B,V,eTopPaste,'ZIFV2_PASTE_T_'+Token);
  V2AddPasteAperture(B,V,eBottomPaste,'ZIFV2_PASTE_B_'+Token);
 End;
 Log.Add('EXPLICIT_PASTE_TOP='+IntToStr(N)+'|BOTTOM='+IntToStr(N));
 Log.Add('PASTE_APERTURE_DIAMETER=VIA_COPPER_DIAMETER');
 Result:=True;
End;

Function V2FlipPassiveAndPlaceBottom(B:IPCB_Board;C:IPCB_Component;
                     TargetX,TargetY:TCoord;TargetRotation:Double;
                     Log:TStringList):Boolean;
Var It:IPCB_GroupIterator;P:IPCB_Pad;Body:IPCB_ComponentBody;
    PadCount,BottomPads,BodyCount,BottomBodies:Integer;
Begin
 Result:=False;
 If C=Nil Then Exit;
 If (C.Name.Text<>'R1') And (C.Name.Text<>'R2') And
    (C.Name.Text<>'R3') And (C.Name.Text<>'R4') And
    (C.Name.Text<>'C1') And (C.Name.Text<>'C2') And
    (C.Name.Text<>'C3') And (C.Name.Text<>'C4') Then Exit;
 If C.Pattern<>'CC1608-0603' Then Exit;
 Log.Add('PASSIVE_BEFORE='+C.Name.Text+'|LAYER='+IntToStr(C.Layer)+
         '|X='+IntToStr(C.X)+'|Y='+IntToStr(C.Y)+'|ROT='+FloatToStr(C.Rotation));
 PCBServer.SendMessageToRobots(C.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
 Try
  If C.Layer=eTopLayer Then C.FlipComponent;
  If C.Layer=eBottomLayer Then Begin
   C.MoveToXY(TargetX,TargetY);
   C.RotateAroundXY(C.X,C.Y,TargetRotation-C.Rotation);

  End;
 Finally PCBServer.SendMessageToRobots(C.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);End;
 PadCount:=0;BottomPads:=0;BodyCount:=0;BottomBodies:=0;
 It:=C.GroupIterator_Create;It.AddFilter_ObjectSet(MkSet(ePadObject));
 P:=It.FirstPCBObject;
 While P<>Nil Do Begin
  Inc(PadCount);If P.Layer=eBottomLayer Then Inc(BottomPads);
  Log.Add('PASSIVE_PAD='+C.Name.Text+'-'+P.Name+'|LAYER='+IntToStr(P.Layer)+
          '|X='+IntToStr(P.X)+'|Y='+IntToStr(P.Y));
  P:=It.NextPCBObject;
 End;
 C.GroupIterator_Destroy(It);
 It:=C.GroupIterator_Create;It.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
 Body:=It.FirstPCBObject;
 While Body<>Nil Do Begin
  Inc(BodyCount);If Body.GetBodyProjection=eBoardSide_Bottom Then Inc(BottomBodies);
  Body:=It.NextPCBObject;
 End;
 C.GroupIterator_Destroy(It);
 Log.Add('PASSIVE_AFTER='+C.Name.Text+'|LAYER='+IntToStr(C.Layer)+
   '|PADS='+IntToStr(PadCount)+'|BOTTOM_PADS='+IntToStr(BottomPads)+
   '|BODIES='+IntToStr(BodyCount)+'|BOTTOM_BODIES='+IntToStr(BottomBodies));
 Result:=(C.Layer=eBottomLayer) And (PadCount=2) And (BottomPads=2)
          And (BodyCount>0) And (BottomBodies=BodyCount);
 { Verify the returned pad positions against the route plan before adding
   routes. FlipComponent mirrors the footprint; setting Layer alone does not.
   After all components: B.RebuildPadCaches, B.ViewManager_FullUpdate,
   B.GraphicallyInvalidate; then save/reopen and inspect native/3D geometry. }
End;

Function V2AuditBiasViaInPad(B:IPCB_Board;Log:TStringList):Boolean;
Var CI,VI:IPCB_BoardIterator;C:IPCB_Component;P:IPCB_Pad;
    V:IPCB_Via;Channel,Found,Matched:Integer;ExpectedNet:String;
Begin
 { Read-only check for the requested four resistor bias tees. A via centered
   in Rn-1, on MWn, is deliberately stricter than merely touching its pad. }
 Result:=True;Found:=0;
 CI:=B.BoardIterator_Create;CI.AddFilter_ObjectSet(MkSet(eComponentObject));
 CI.AddFilter_LayerSet(AllLayers);CI.AddFilter_Method(eProcessAll);
 C:=CI.FirstPCBObject;
 While C<>Nil Do Begin
  Channel:=0;
  If C.Name.Text='R1' Then Channel:=1;
  If C.Name.Text='R2' Then Channel:=2;
  If C.Name.Text='R3' Then Channel:=3;
  If C.Name.Text='R4' Then Channel:=4;
  If Channel>0 Then Begin
   Inc(Found);ExpectedNet:='MW'+IntToStr(Channel);Matched:=0;
   P:=C.GetState_PadByName('1');
   If P=Nil Then Result:=False
   Else If P.Layer<>eBottomLayer Then Result:=False
   Else If P.Net=Nil Then Result:=False
   Else If P.Net.Name<>ExpectedNet Then Result:=False
   Else Begin
    VI:=B.BoardIterator_Create;VI.AddFilter_ObjectSet(MkSet(eViaObject));
    VI.AddFilter_LayerSet(AllLayers);VI.AddFilter_Method(eProcessAll);
    V:=VI.FirstPCBObject;
    While V<>Nil Do Begin
     If V.Net<>Nil Then If V.Net.Name=ExpectedNet Then
      If (Abs(V.X-P.X)<=MMsToCoord(0.001)) And
         (Abs(V.Y-P.Y)<=MMsToCoord(0.001)) And
         (V.Size<=P.BotXSize) And (V.Size<=P.BotYSize) Then Inc(Matched);
     V:=VI.NextPCBObject;
    End;
    B.BoardIterator_Destroy(VI);
   End;
   Log.Add('BIAS_VIA_IN_PAD='+C.Name.Text+'-1|MATCHES='+IntToStr(Matched));
   If Matched<>1 Then Result:=False;
  End;
  C:=CI.NextPCBObject;
 End;
 B.BoardIterator_Destroy(CI);
 If Found<>4 Then Result:=False;
End;
Procedure V2SetLabel(C:IPCB_Component;X,Y:Double);
Begin
 C.ChangeNameAutoposition(eAutoPos_Manual);
 C.Name.Rotation:=0;C.Name.MoveToXY(MMsToCoord(X),MMsToCoord(Y));
End;

Procedure V2FixAppearance(B:IPCB_Board;L:TStringList);
Var It:IPCB_BoardIterator;C:IPCB_Component;P:IPCB_Pad;PC:TPadCache;N:Integer;
Begin
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eComponentObject));It.AddFilter_Method(eProcessAll);
 C:=It.FirstPCBObject;
 While C<>Nil Do Begin
  If C.Name.Text='C1' Then V2SetLabel(C,1.5,44.65);
  If C.Name.Text='R1' Then V2SetLabel(C,1.5,43.05);
  If C.Name.Text='C2' Then V2SetLabel(C,1.5,40.9);
  If C.Name.Text='R2' Then V2SetLabel(C,1.5,39.3);
  If C.Name.Text='C3' Then V2SetLabel(C,8.8,32.7);
  If C.Name.Text='C4' Then V2SetLabel(C,11.5,32.7);
  If C.Name.Text='R3' Then V2SetLabel(C,6.8,35.1);
  If C.Name.Text='R4' Then V2SetLabel(C,14.2,35.1);
  C:=It.NextPCBObject;
 End;B.BoardIterator_Destroy(It);
 N:=0;It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(ePadObject));It.AddFilter_Method(eProcessAll);
 P:=It.FirstPCBObject;
 While P<>Nil Do Begin
  C:=P.Component;
  If C<>Nil Then If (Copy(C.Name.Text,1,1)='R') Or (Copy(C.Name.Text,1,1)='C') Then Begin
   PC:=P.GetState_Cache;PC.SolderMaskExpansion:=0;PC.SolderMaskBottomExpansion:=0;
   PC.SolderMaskExpansionValid:=eCacheManual;P.SetState_Cache(PC);Inc(N);
  End;
  P:=It.NextPCBObject;
 End;B.BoardIterator_Destroy(It);
 L.Add('RC_PAD_MASK_ZERO_BOTH='+IntToStr(N));L.Add('RC_LABELS_MANUALLY_PLACED=8');
End;

Procedure FinalizeV2;
Var B:IPCB_Board;It:IPCB_BoardIterator;P:IPCB_Polygon;V:IPCB_Via;
 A:Array[0..7] Of IPCB_Polygon;C:IPCB_Component;N,I:Integer;L:TStringList;PC:TPadCache;
 ReportPath:String;O:IPCB_BoardOutline;S:TPolySegment;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If ExtractFileName(B.FileName)<>'QSTL_ZIF24_V2.PcbDoc' Then Exit;
 If Pos('\outputs\qstl_zif24_v2_project\',LowerCase(B.FileName))=0 Then Exit;
 ReportPath:=ExtractFilePath(B.FileName);L:=TStringList.Create;
 L.Add('BOARD='+B.FileName);L.Add('START');L.SaveToFile(ReportPath+'native_finalize_v2.txt');
 PCBServer.PreProcess;
 Try
  It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eComponentObject));It.AddFilter_Method(eProcessAll);
  C:=It.FirstPCBObject;
  While C<>Nil Do Begin
   If (C.Name.Text='R1') Or (C.Name.Text='R2') Or (C.Name.Text='R3') Or (C.Name.Text='R4') Then C.Comment.Text:='10k / 0603';
   If (C.Name.Text='C1') Or (C.Name.Text='C2') Or (C.Name.Text='C3') Or (C.Name.Text='C4') Then C.Comment.Text:='1nF / 0603';
   C:=It.NextPCBObject;
  End;B.BoardIterator_Destroy(It);
  V2FixAppearance(B,L);
  V2EnsureGndViaSolidRule(B,L);
  L.SaveToFile(ReportPath+'native_finalize_v2.txt');
  It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eViaObject));It.AddFilter_Method(eProcessAll);
  V:=It.FirstPCBObject;N:=0;
  While V<>Nil Do Begin
   PC:=V.GetState_Cache;
   PC.SolderMaskExpansion:=MMsToCoord(0.025);PC.SolderMaskBottomExpansion:=MMsToCoord(0.025);
   PC.SolderMaskExpansionValid:=eCacheManual;V.SetState_Cache(PC);
   Inc(N);V:=It.NextPCBObject;
  End;B.BoardIterator_Destroy(It);L.Add('VIA_MASK_COUNT='+IntToStr(N));
  V2RebuildExplicitPasteForAllVias(B,218,L);
  L.SaveToFile(ReportPath+'native_finalize_v2.txt');
  V2AuditBiasViaInPad(B,L);
  L.SaveToFile(ReportPath+'native_finalize_v2.txt');
  O:=B.BoardOutline;S:=O.Segments[0];O.Segments[O.PointCount]:=S;
  O.Invalidate;O.Rebuild;O.Validate;B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);
  It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(ePolyObject));It.AddFilter_Method(eProcessAll);
  N:=0;P:=It.FirstPCBObject;
  While P<>Nil Do Begin A[N]:=P;Inc(N);P:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);
  For I:=0 To N-1 Do Begin
   P:=A[I];P.SetState_CopperPourInvalid;P.Rebuild;
   If P.GetState_Poured Then L.Add('POURED='+P.Name) Else L.Add('NOT_POURED='+P.Name);
   L.SaveToFile(ReportPath+'native_finalize_v2.txt');
  End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 L.Add('SAVED');L.SaveToFile(ReportPath+'native_finalize_v2.txt');L.Free;
End;
