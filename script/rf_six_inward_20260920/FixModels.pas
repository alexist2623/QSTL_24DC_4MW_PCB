Var ModelLog:TStringList;ModelPath:String;
Procedure SaveModelDocument;
Begin ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');End;
Procedure CorrectBody(Body:IPCB_ComponentBody;CX,CY:Integer;Angle:Double;IsRes,Bottom:Boolean);
Var M:IPCB_Model;Pt:TCoordPoint;
Begin
 If IsRes Then M:=Body.ModelFactory_FromFilename(ModelPath+'Models\R_0603_1608Metric.step',True) Else Begin M:=Body.GetModel;M:=M.I_Replicate;End;
 If M=Nil Then Begin ModelLog.Add('MODEL_FACTORY_NIL');Exit;End;
 Pt:=M.GetOrigin;Pt.X:=CX;Pt.Y:=CY;M.SetOrigin(Pt);M.SetState(0,0,Angle,0);M.SetEmbed(True);Body.SetModel(M);Body.SetState_FromModel;
 If Bottom Then Body.SetBodyProjection(eBoardSide_Bottom) Else Body.SetBodyProjection(eBoardSide_Top);
 Body.SetStandoffHeight(0);If IsRes Then Body.SetOverallHeight(MMsToCoord(0.45)) Else Body.SetOverallHeight(MMsToCoord(0.553));
 Body.ValidateMesh;
End;
Procedure FixModels;
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;GI:IPCB_GroupIterator;LI:IPCB_LibraryIterator;Lib:IPCB_Library;F:IPCB_LibComponent;
 Body:IPCB_ComponentBody;C:IPCB_Component;P:IPCB_Pad;N:IPCB_Net;Ns:Array[0..63] Of IPCB_Net;
 Bodies:Array[0..11] Of IPCB_ComponentBody;Count,J,K,PC,NN,CX,CY:Integer;SX,SY:Double;IsRes:Boolean;S,Pattern:String;
Begin
 ModelPath:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\';ModelLog:=TStringList.Create;
 D:=Client.OpenDocument('PCB',ModelPath+'QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 Count:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
 While Body<>Nil Do Begin C:=Body.Component;If C<>Nil Then If (Copy(C.Name.Text,1,1)='R') Or (Copy(C.Name.Text,1,1)='C') Then Begin Bodies[Count]:=Body;Inc(Count);End;Body:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 ModelLog.Add('BOARD_BODIES='+IntToStr(Count));ModelLog.SaveToFile(ModelPath+'work\rf6_models.txt');If Count<>12 Then Exit;
 PCBServer.PreProcess;
 Try
  For J:=0 To Count-1 Do Begin Body:=Bodies[J];C:=Body.Component;SX:=0;SY:=0;PC:=0;
   GI:=C.GroupIterator_Create;GI.AddFilter_ObjectSet(MkSet(ePadObject));P:=GI.FirstPCBObject;While P<>Nil Do Begin SX:=SX+P.X;SY:=SY+P.Y;Inc(PC);P:=GI.NextPCBObject;End;C.GroupIterator_Destroy(GI);
   If PC=2 Then Begin CorrectBody(Body,Round(SX/2),Round(SY/2),C.Rotation,Copy(C.Name.Text,1,1)='R',True);ModelLog.Add('UPDATED='+C.Name.Text);ModelLog.SaveToFile(ModelPath+'work\rf6_models.txt');End;
  End;
 Finally PCBServer.PostProcess;End;
 NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin Ns[NN]:=N;Inc(NN);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin N:=Ns[J];N.ConnectivelyInValidate;N.Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveModelDocument;
 ModelLog.Add('BOARD_SAVED');ModelLog.SaveToFile(ModelPath+'work\rf6_models.txt');
 For K:=0 To 1 Do Begin
  If K=0 Then Begin S:='Passives_0603.PcbLib';Pattern:='CC1608-0603';End Else Begin S:='Capacitors_0402.PcbLib';Pattern:='FP-GCM155-0_05-IPC_A';End;
  D:=Client.OpenDocument('PCBLib',ModelPath+S);If D<>Nil Then Begin Client.ShowDocument(D);Lib:=PCBServer.GetCurrentPCBLibrary;
   If Lib<>Nil Then Begin LI:=Lib.LibraryIterator_Create;LI.SetState_FilterAll;F:=LI.FirstPCBObject;
    While F<>Nil Do Begin If F.Name=Pattern Then Begin
     SX:=0;SY:=0;PC:=0;GI:=F.GroupIterator_Create;GI.AddFilter_ObjectSet(MkSet(ePadObject));P:=GI.FirstPCBObject;While P<>Nil Do Begin SX:=SX+P.X;SY:=SY+P.Y;Inc(PC);P:=GI.NextPCBObject;End;F.GroupIterator_Destroy(GI);
     If PC=2 Then Begin
      PCBServer.PreProcess;Try GI:=F.GroupIterator_Create;GI.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=GI.FirstPCBObject;While Body<>Nil Do Begin CorrectBody(Body,Round(SX/2),Round(SY/2),0,K=0,False);Body:=GI.NextPCBObject;End;F.GroupIterator_Destroy(GI);Finally PCBServer.PostProcess;End;
      F.Board.SetState_DocumentHasChanged;F.Board.ViewManager_FullUpdate;F.Board.GraphicallyInvalidate;ModelLog.Add('LIBRARY_UPDATED='+S);
     End;
    End;F:=LI.NextPCBObject;End;Lib.LibraryIterator_Destroy(LI);SaveModelDocument;
   End;
  End;
 End;
 D:=Client.OpenDocument('PCB',ModelPath+'QSTL_24DC_4MW_PCB.PcbDoc');If D<>Nil Then Client.ShowDocument(D);
 ModelLog.Add('COMPLETE');ModelLog.SaveToFile(ModelPath+'work\rf6_models.txt');ModelLog.Free;
End;
