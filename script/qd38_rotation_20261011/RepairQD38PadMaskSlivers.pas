Var B:IPCB_Board;L:TStringList;P:IPCB_Pad;C:TPadCache;I:IPCB_BoardIterator;N:Integer;Good:Boolean;
 Targets:Array[0..17] Of IPCB_Pad;

Procedure DumpPads(S:String;Path:String);
Var I:IPCB_BoardIterator;P:IPCB_Pad;C:TPadCache;RefName,Enabled:String;L:TStringList;Count:Integer;
Begin
 L:=TStringList.Create;L.Add('STAGE='+S);L.Add('BOARD='+B.FileName);L.Add('CANDIDATE_SHA256=835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495');Count:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  Inc(Count);RefName:='MOUNT';If P.Component<>Nil Then RefName:=P.Component.Name.Text;
  C:=P.GetState_Cache;Enabled:='0';If P.GetState_PasteMaskEnabled Then Enabled:='1';
  L.Add('PAD='+RefName+'|'+P.Name+'|'+IntToStr(P.X)+'|'+IntToStr(P.Y)+'|'+IntToStr(C.SolderMaskExpansion)+'|'+IntToStr(C.SolderMaskBottomExpansion)+'|'+IntToStr(C.PasteMaskExpansion)+'|'+Enabled);
  P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);L.Add('PAD_COUNT='+IntToStr(Count));L.Add('COMPLETE');L.SaveToFile(Path);L.Free;
End;

Function FindPad(RefName,Pin:String;X,Y:Double):IPCB_Pad;
Var J:IPCB_BoardIterator;P:IPCB_Pad;Count:Integer;
Begin Result:=Nil;Count:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(ePadObject));P:=J.FirstPCBObject;
 While P<>Nil Do Begin
  If P.Component<>Nil Then If (P.Component.Name.Text=RefName) And (P.Name=Pin) Then Begin
   Inc(Count);If (Abs(CoordToMMs(P.X)-X)<0.00001) And (Abs(CoordToMMs(P.Y)-Y)<0.00001) And (P.Layer=eBottomLayer) Then Result:=P;
  End;P:=J.NextPCBObject;
 End;B.BoardIterator_Destroy(J);If Count<>1 Then Result:=Nil;
End;

Procedure RepairQD38PadMaskSlivers;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('EXPECTED_NATIVE_SHA256=c179d313dc7d7c1c5851517d779616fbe7c9c3b1e9a5f4ac565e0541c3e0a047');L.Add('CANDIDATE_SHA256=835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495');Good:=True;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;N:=0;While P<>Nil Do Begin Inc(N);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If N<>243 Then Good:=False;
 Targets[0]:=FindPad('C09','1',5.371437330000,48.500000000000);
 If Targets[0]=Nil Then Good:=False Else Begin C:=Targets[0].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[0].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[1]:=FindPad('C09','2',6.328562670000,48.500000000000);
 If Targets[1]=Nil Then Good:=False Else Begin C:=Targets[1].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[1].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[2]:=FindPad('C12','1',5.371437330000,36.500000000000);
 If Targets[2]=Nil Then Good:=False Else Begin C:=Targets[2].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[2].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[3]:=FindPad('C12','2',6.328562670000,36.500000000000);
 If Targets[3]=Nil Then Good:=False Else Begin C:=Targets[3].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[3].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[4]:=FindPad('C15','2',3.750000000000,27.028562670000);
 If Targets[4]=Nil Then Good:=False Else Begin C:=Targets[4].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[4].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[5]:=FindPad('C21','2',15.750000000000,27.028562670000);
 If Targets[5]=Nil Then Good:=False Else Begin C:=Targets[5].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[5].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[6]:=FindPad('C28','1',14.128562670000,36.500000000000);
 If Targets[6]=Nil Then Good:=False Else Begin C:=Targets[6].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[6].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[7]:=FindPad('C28','2',13.171437330000,36.500000000000);
 If Targets[7]=Nil Then Good:=False Else Begin C:=Targets[7].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[7].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[8]:=FindPad('C31','1',14.128562670000,48.500000000000);
 If Targets[8]=Nil Then Good:=False Else Begin C:=Targets[8].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[8].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[9]:=FindPad('C31','2',13.171437330000,48.500000000000);
 If Targets[9]=Nil Then Good:=False Else Begin C:=Targets[9].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[9].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[10]:=FindPad('R09','1',6.328562670000,47.500000000000);
 If Targets[10]=Nil Then Good:=False Else Begin C:=Targets[10].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[10].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[11]:=FindPad('R12','1',6.328562670000,37.500000000000);
 If Targets[11]=Nil Then Good:=False Else Begin C:=Targets[11].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[11].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[12]:=FindPad('R15','1',2.900000430000,28.050000000000);
 If Targets[12]=Nil Then Good:=False Else Begin C:=Targets[12].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[12].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[13]:=FindPad('R15','2',4.599999570000,28.050000000000);
 If Targets[13]=Nil Then Good:=False Else Begin C:=Targets[13].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[13].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[14]:=FindPad('R21','1',16.599999570000,28.050000000000);
 If Targets[14]=Nil Then Good:=False Else Begin C:=Targets[14].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[14].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[15]:=FindPad('R21','2',14.900000430000,28.050000000000);
 If Targets[15]=Nil Then Good:=False Else Begin C:=Targets[15].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[15].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[16]:=FindPad('R28','1',13.171437330000,37.500000000000);
 If Targets[16]=Nil Then Good:=False Else Begin C:=Targets[16].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[16].GetState_PasteMaskEnabled) Then Good:=False;End;
 Targets[17]:=FindPad('R31','1',13.171437330000,47.500000000000);
 If Targets[17]=Nil Then Good:=False Else Begin C:=Targets[17].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[17].GetState_PasteMaskEnabled) Then Good:=False;End;
 If Not Good Then Begin L.Add('STOP_GUARD');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_mask_repair.txt');L.Free;Exit;End;
 DumpPads('BEFORE_REPAIR','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_mask_before.txt');
 PCBServer.PreProcess;Try
  For N:=0 To 17 Do Begin
   P:=Targets[N];PCBServer.SendMessageToRobots(P.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
   C:=P.GetState_Cache;C.SolderMaskExpansionValid:=eCacheManual;C.SolderMaskExpansion:=MMsToCoord(0.025);C.SolderMaskBottomExpansion:=MMsToCoord(0.025);P.SetState_Cache(C);
   PCBServer.SendMessageToRobots(P.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);
  End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 DumpPads('AFTER_REPAIR_UNSAVED','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_mask_after_unsaved.txt');
 L.Add('CHANGED_PAD_COUNT=18');L.Add('COMPLETE_NOT_SAVED');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\native_mask_repair.txt');L.Free;
End;
