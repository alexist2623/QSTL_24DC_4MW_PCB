Var B:IPCB_Board;Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_finish_log.txt');End;
Procedure Rect(L:TLayer;X1,Y1,X2,Y2:Double);
Var RG:IPCB_Region;G:IPCB_GeometricPolygon;CT:IPCB_Contour;
Begin G:=PCBServer.PCBGeometricPolygonFactory;CT:=PCBServer.PCBContourFactory;
CT.AddPoint(MMsToCoord(X1),MMsToCoord(Y1));CT.AddPoint(MMsToCoord(X2),MMsToCoord(Y1));
CT.AddPoint(MMsToCoord(X2),MMsToCoord(Y2));CT.AddPoint(MMsToCoord(X1),MMsToCoord(Y2));
G.AddContourIsHole(CT,False);RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);
RG.Kind:=eRegionKind_Copper;RG.Layer:=L;RG.Name:='DSUB_ROW_COVERLAY';RG.SetGeometricPolygon(G);
B.AddPCBObject(RG);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,RG.I_ObjectAddress);End;

Procedure Finish0;
Var D:IServerDocument;I:IPCB_BoardIterator;C:IPCB_Component;Rule:IPCB_Rule;HR:IPCB_MaxMinHoleSizeConstraint;Good:Boolean;
Begin Mark('OPEN ZIF_to_2xZIF');D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_2xZIF.PcbDoc');If D=Nil Then Exit;
Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_2xZIF.PcbDoc') Then Exit;
PCBServer.PreProcess;Try
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin
If C.Name.Text='C' Then C.SourceUniqueId:='TYIJSHYP';
If C.Name.Text='A' Then C.SourceUniqueId:='EONXBHWE';
If C.Name.Text='B' Then C.SourceUniqueId:='AOVPLSAL';
C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
B.RebuildPadCaches;Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED ZIF_to_2xZIF');
Good:=B.RunBatchDesignRuleCheck('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_2xZIF_DRC.html',eDRC_HTML,False,False);
If Good Then Mark('DRC_TRUE ZIF_to_2xZIF') Else Mark('DRC_FALSE ZIF_to_2xZIF');
Client.CloseDocument(D);Mark('CLOSED ZIF_to_2xZIF');End;
Procedure Finish1;
Var D:IServerDocument;I:IPCB_BoardIterator;C:IPCB_Component;Rule:IPCB_Rule;HR:IPCB_MaxMinHoleSizeConstraint;Good:Boolean;
Begin Mark('OPEN ZIF_to_DSUB25');D:=Client.OpenDocument('PCB','C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_DSUB25.PcbDoc');If D=Nil Then Exit;
Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_DSUB25.PcbDoc') Then Exit;
PCBServer.PreProcess;Try
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin
If C.Name.Text='A' Then C.SourceUniqueId:='EONXBHWE';
If C.Name.Text='J1' Then C.SourceUniqueId:='JWOPSLLW';
C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
Rect(eTopSolder,7.2974000000000006,8.227400000000001,23.702600000000004,9.3926);
Rect(eBottomSolder,7.2974000000000006,8.227400000000001,23.702600000000004,9.3926);
Rect(eTopSolder,7.932400000000001,5.687400000000001,23.067600000000002,6.8526);
Rect(eBottomSolder,7.932400000000001,5.687400000000001,23.067600000000002,6.8526);
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;While Rule<>Nil Do Begin If Rule.RuleKind=eRule_MaxMinHoleSize Then Begin HR:=Rule;HR.MaxLimit:=MMsToCoord(2.7);End;Rule:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
B.RebuildPadCaches;Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED ZIF_to_DSUB25');
Good:=B.RunBatchDesignRuleCheck('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\branched_fpc_20261002\native_work\ZIF_to_DSUB25_DRC.html',eDRC_HTML,False,False);
If Good Then Mark('DRC_TRUE ZIF_to_DSUB25') Else Mark('DRC_FALSE ZIF_to_DSUB25');
Client.CloseDocument(D);Mark('CLOSED ZIF_to_DSUB25');End;
Procedure NativeFinish;Begin Log:=TStringList.Create;Mark('START');Finish0;Finish1;Mark('COMPLETE');Log.Free;End;