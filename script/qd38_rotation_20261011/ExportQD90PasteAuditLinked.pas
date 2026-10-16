Var PasteLog:TStringList;
Function BText(B:Boolean):String;Begin If B Then Result:='1' Else Result:='0';End;
Procedure MarkPaste(S:String);Begin PasteLog.Add(S);PasteLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\revision_paste_export_native_log.txt');End;
Procedure ExportQD90PasteAuditLinked;
Var D:IServerDocument;B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;P:IPCB_Pad;V:IPCB_Via;
    PC:TPadCache;Count:Integer;RefName:String;WS:IWorkspace;Project:IProject;AddedJob:Boolean;
Begin
 PasteLog:=TStringList.Create;MarkPaste('START');MarkPaste('TOKEN=e25cdee1823c4479b9fb6207dc1c3a80');MarkPaste('BOUND_NATIVE_SHA256=1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c');
 ResetParameters;AddStringParameter('ObjectKind','Project');AddStringParameter('FileName','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb');RunProcess('WorkspaceManager:OpenObject');
 WS:=GetWorkspace;If WS=Nil Then Begin MarkPaste('STOP_NO_WORKSPACE');Exit;End;
 Project:=WS.DM_GetProjectFromPath('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb');If Project=Nil Then Begin MarkPaste('STOP_NO_PROJECT');Exit;End;
 If LowerCase(Project.DM_ProjectFullPath)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb') Then Begin MarkPaste('STOP_WRONG_PROJECT');Exit;End;
 Project.DM_SetAsCurrentProject;MarkPaste('PROJECT='+Project.DM_ProjectFullPath);
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Begin MarkPaste('STOP_NO_DOCUMENT');Exit;End;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Begin MarkPaste('STOP_NO_BOARD');Exit;End;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Begin MarkPaste('STOP_WRONG_BOARD');Exit;End;
 MarkPaste('BOARD='+B.FileName);Count:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(Count);C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If Count<>50 Then Begin MarkPaste('STOP_COMPONENT_COUNT='+IntToStr(Count));Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  RefName:='MOUNT';If P.Component<>Nil Then RefName:=P.Component.Name.Text;
  PC:=P.GetState_Cache;
  PasteLog.Add('PAD|'+RefName+'|'+P.Name+'|'+IntToStr(P.X)+'|'+IntToStr(P.Y)+'|'+IntToStr(P.Layer)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BText(P.GetState_PasteMaskEnabled)+'|'+BText(P.GetState_IsTopPasteEnabled)+'|'+BText(P.GetState_IsBottomPasteEnabled));
  P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkPaste('PAD_FLAGS_READ');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;Count:=0;
 While V<>Nil Do Begin
  PC:=V.GetState_Cache;
  PasteLog.Add('VIA|'+IntToStr(Count)+'|'+IntToStr(V.X)+'|'+IntToStr(V.Y)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BText(V.GetState_PasteMaskEnabled));
  Inc(Count);V:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkPaste('VIA_FLAGS_READ='+IntToStr(Count));
 D:=Client.OpenDocument('OUTPUTJOB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob');If D<>Nil Then Client.CloseDocument(D);
 AddedJob:=Project.DM_IndexOfSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob')<0;
 Try
  If AddedJob Then Project.DM_AddSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob');
  Project.DM_SetAsCurrentProject;
  MarkPaste('OUTJOB_PROJECT_INDEX='+IntToStr(Project.DM_IndexOfSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob')));
  D:=Client.OpenDocument('OUTPUTJOB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob');If D=Nil Then Begin MarkPaste('STOP_NO_OUTJOB');Exit;End;Client.ShowDocument(D);
  MarkPaste('EXPORT_BEGIN');ResetParameters;AddStringParameter('ObjectKind','OutputBatch');AddStringParameter('Action','Run');RunProcess('WorkspaceManager:GenerateReport');
  MarkPaste('EXPORT_RETURNED');
 Finally
  If D<>Nil Then Client.CloseDocument(D);
  If AddedJob Then Begin Project.DM_RemoveSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_rotation_20261011\Revision_Paste_Audit_Only.OutJob');MarkPaste('TEMPORARY_OUTJOB_REMOVED');End;
 End;
 MarkPaste('COMPLETE');PasteLog.Free;
End;
