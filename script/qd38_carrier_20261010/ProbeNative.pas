Procedure ProbeNative;
Var W:IWorkspace;P:IProject;D:IServerDocument;B:IPCB_Board;L:TStringList;I:IPCB_BoardIterator;O:IPCB_Primitive;N:Integer;
Begin
 L:=TStringList.Create;L.Add('START');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\probe_native.txt');
 W:=GetWorkspace;P:=W.DM_OpenProject('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb',True);
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');
 If D=Nil Then Begin L.Add('NO_DOCUMENT');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\probe_native.txt');Exit;End;
 Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 L.Add('BOARD='+B.FileName);N:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin Inc(N);O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('COMPONENTS='+IntToStr(N));L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\probe_native.txt');L.Free;
End;
