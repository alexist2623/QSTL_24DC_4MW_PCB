Procedure ResizeQDVias;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;R:IPCB_Rule;VR:IPCB_RoutingViaStyleRule;
Q:Array[0..21] Of IPCB_Via;N,K,Total:Integer;L:TStringList;
Begin L:=TStringList.Create;L.Add('START');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd_via_land_20261017\via_apply_log.txt');
D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
N:=0;Total:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
While V<>Nil Do Begin Inc(Total);If V.Net<>Nil Then If ((V.Net.Name='DC01') And (Abs(CoordToMMs(V.X)-9.495538540000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.616393020000)<0.00001)) Or
((V.Net.Name='DC03') And (Abs(CoordToMMs(V.X)-8.492439200000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.765915200000)<0.00001)) Or
((V.Net.Name='DC04') And (Abs(CoordToMMs(V.X)-7.972097340000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.753255840000)<0.00001)) Or
((V.Net.Name='DC06') And (Abs(CoordToMMs(V.X)-6.834629460000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.654312680000)<0.00001)) Or
((V.Net.Name='DC07') And (Abs(CoordToMMs(V.X)-6.669544700000)<0.00001) And (Abs(CoordToMMs(V.Y)-48.249105940000)<0.00001)) Or
((V.Net.Name='DC08') And (Abs(CoordToMMs(V.X)-6.648958000000)<0.00001) And (Abs(CoordToMMs(V.Y)-47.658949640000)<0.00001)) Or
((V.Net.Name='DC10') And (Abs(CoordToMMs(V.X)-6.652160940000)<0.00001) And (Abs(CoordToMMs(V.Y)-46.451489520000)<0.00001)) Or
((V.Net.Name='DC14') And (Abs(CoordToMMs(V.X)-6.669544700000)<0.00001) And (Abs(CoordToMMs(V.Y)-44.050892340000)<0.00001)) Or
((V.Net.Name='DC17') And (Abs(CoordToMMs(V.X)-8.238680500000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.556379200000)<0.00001)) Or
((V.Net.Name='DC18') And (Abs(CoordToMMs(V.X)-8.770246620000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.523105200000)<0.00001)) Or
((V.Net.Name='DC19') And (Abs(CoordToMMs(V.X)-9.276989320000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.544128780000)<0.00001)) Or
((V.Net.Name='DC20') And (Abs(CoordToMMs(V.X)-9.769919500000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.657555020000)<0.00001)) Or
((V.Net.Name='DC22') And (Abs(CoordToMMs(V.X)-10.753897720000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.529188500000)<0.00001)) Or
((V.Net.Name='DC23') And (Abs(CoordToMMs(V.X)-11.261318600000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.556379200000)<0.00001)) Or
((V.Net.Name='DC25') And (Abs(CoordToMMs(V.X)-12.691099840000)<0.00001) And (Abs(CoordToMMs(V.Y)-42.611860420000)<0.00001)) Or
((V.Net.Name='DC26') And (Abs(CoordToMMs(V.X)-12.833116320000)<0.00001) And (Abs(CoordToMMs(V.Y)-44.124189120000)<0.00001)) Or
((V.Net.Name='DC27') And (Abs(CoordToMMs(V.X)-12.855750260000)<0.00001) And (Abs(CoordToMMs(V.Y)-44.789971380000)<0.00001)) Or
((V.Net.Name='DC29') And (Abs(CoordToMMs(V.X)-12.878998880000)<0.00001) And (Abs(CoordToMMs(V.Y)-46.149999140000)<0.00001)) Or
((V.Net.Name='DC33') And (Abs(CoordToMMs(V.X)-12.713799820000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.717987940000)<0.00001)) Or
((V.Net.Name='DC36') And (Abs(CoordToMMs(V.X)-11.007562440000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.765915200000)<0.00001)) Or
((V.Net.Name='DC37') And (Abs(CoordToMMs(V.X)-10.499130640000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.775188740000)<0.00001)) Or
((V.Net.Name='DC38') And (Abs(CoordToMMs(V.X)-9.977447660000)<0.00001) And (Abs(CoordToMMs(V.Y)-49.780873260000)<0.00001)) Then Begin If N>=22 Then Exit;Q[N]:=V;Inc(N);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
If (N<>22) Or (Total<>1590) Then Exit;
For K:=0 To 21 Do Begin V:=Q[K];If (Abs(CoordToMMs(V.Size)-0.35)>0.00001) Or (Abs(CoordToMMs(V.HoleSize)-0.2)>0.00001) Or (V.LowLayer<>eTopLayer) Or (V.HighLayer<>eBottomLayer) Then Exit;End;
VR:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
While R<>Nil Do Begin If R.Name='QD38_QD_VIA_0P4_0P2' Then VR:=R;R:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If VR=Nil Then Exit;
PCBServer.PreProcess;
Try For K:=0 To 21 Do Begin V:=Q[K];PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
V.Size:=V.HoleSize+39371;PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);End;
PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
VR.MinWidth:=118111;VR.MaxWidth:=118111;VR.PreferedWidth:=118111;
PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
L.Add('QD_VIAS_RESIZED=22');L.Add('ONLY_QD_STYLE_WIDTH_UPDATED');L.Add('COMPLETE_REQUIRES_SAVE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd_via_land_20261017\via_apply_log.txt');L.Free;End;
