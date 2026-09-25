Var WidenLog:TStringList;
Procedure WidenMark(S:String);
Begin
 WidenLog.Add(S);
 WidenLog.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\dc_ground_pour_20260924\widen_native.txt');
End;

Procedure WidenGround;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;
 R:IPCB_Rule;C:IPCB_ClearanceConstraint;Poly:IPCB_Polygon;
 P,DCScope,RFScope:String;N:Integer;
Begin
 P:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc';
 WidenLog:=TStringList.Create;WidenMark('START');
 D:=Client.OpenDocument('PCB',P);If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(P) Then Exit;
 DCScope:='InNet(''GND'') And (OnLayer(''L2_DC_A'') Or OnLayer(''L4_DC_B''))';
 RFScope:='InNet(''GND'') And OnLayer(''L6_RF_QD'')';
 C:=Nil;
 PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;
  I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
  While R<>Nil Do Begin
   If R.Name='DC_GND_GAP_0P2' Then C:=R;
   If R.Name='Clearance' Then Begin
    R.Scope1Expression:='Not ('+RFScope+') And Not ('+DCScope+')';
    R.Scope2Expression:='Not ('+RFScope+') And Not ('+DCScope+')';
   End;
   R:=I.NextPCBObject;
  End;
  B.BoardIterator_Destroy(I);
  If C=Nil Then Begin
   C:=PCBServer.PCBRuleFactory(eRule_Clearance);
   C.Name:='DC_GND_GAP_0P2';
   B.AddPCBObject(C);
   PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,C.I_ObjectAddress);
  End;
  C.Scope1Expression:=DCScope;C.Scope2Expression:='All';
  C.Comment:='L2 and L4 GND pour clearance to signal copper: 0.20 mm.';
  C.Gap:=MMsToCoord(0.2);C.DRCEnabled:=True;
  B.InvalidateScopeTester;B.ValidateScopeTester;
  WidenMark('RULE_DC_GND_GAP_0P2=0.20mm');
  N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;
  I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin
   If (Poly.Name='L2_DC_GND') Or (Poly.Name='L4_DC_GND') Then Begin
    Poly.SetState_CopperPourInvalid;Poly.Rebuild;Inc(N);WidenMark('REPOURED='+Poly.Name);
   End;
   Poly:=I.NextPCBObject;
  End;
  B.BoardIterator_Destroy(I);WidenMark('REPOURED_COUNT='+IntToStr(N));
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;
 B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');
 AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 WidenMark('SAVED');WidenMark('COMPLETE');WidenLog.Free;
End;
