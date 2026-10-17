Function BoolText(V:Boolean):String;
Begin If V Then Result:='1' Else Result:='0';End;
Procedure AuditPaste;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Pad;V:IPCB_Via;C:IPCB_Component;PC:TPadCache;L:TStringList;S:String;N:Integer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 L:=TStringList.Create;L.Add('PAD_FIELDS=TYPE|COMPONENT|PIN|EXPANSION|EXPANSION_MODE|TOP_SOLDER|BOTTOM_SOLDER|PASTE_ENABLED|TOP_PASTE_ENABLED|BOTTOM_PASTE_ENABLED');
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin C:=P.Component;If C=Nil Then S:='MOUNT' Else S:=C.Name.Text;
  PC:=P.GetState_Cache;L.Add('PAD|'+S+'|'+P.Name+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+IntToStr(PC.SolderMaskExpansion)+'|'+IntToStr(PC.SolderMaskBottomExpansion)+'|'+BoolText(P.GetState_PasteMaskEnabled)+'|'+BoolText(P.GetState_IsTopPasteEnabled)+'|'+BoolText(P.GetState_IsBottomPasteEnabled));P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin PC:=V.GetState_Cache;L.Add('VIA|'+IntToStr(N)+'|'+IntToStr(PC.PasteMaskExpansion)+'|'+IntToStr(Ord(PC.PasteMaskExpansionValid))+'|'+BoolText(V.GetState_PasteMaskEnabled));Inc(N);V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 L.Add('COMPLETE');L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\native_paste_audit.txt');L.Free;
End;


Var ExportLog:TStringList;
Procedure MarkExport(S:String);Begin ExportLog.Add(S);ExportLog.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_export_native.txt');End;
Procedure ExportCapPaste;
Var D:IServerDocument;B:IPCB_Board;WS:IWorkspace;Proj:IProject;Added:Boolean;
Begin
 ExportLog:=TStringList.Create;MarkExport('START');WS:=GetWorkspace;Proj:=WS.DM_GetProjectFromPath('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PrjPcb');If Proj=Nil Then Begin MarkExport('NO_PROJECT');Exit;End;Proj.DM_SetAsCurrentProject;
 D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
 AuditPaste;MarkExport('PASTE_FLAGS_READ');
 D:=Client.GetDocumentByPath('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_verification\Cap_Paste_Verification.OutJob');If D<>Nil Then Client.CloseDocument(D);
 Added:=Proj.DM_IndexOfSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_verification\Cap_Paste_Verification.OutJob')<0;If Added Then Proj.DM_AddSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_verification\Cap_Paste_Verification.OutJob');
 D:=Client.OpenDocument('OUTPUTJOB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_verification\Cap_Paste_Verification.OutJob');If D=Nil Then Begin MarkExport('NO_JOB');Exit;End;Client.ShowDocument(D);
 MarkExport('EXPORT_BEGIN');ResetParameters;AddStringParameter('ObjectKind','OutputBatch');AddStringParameter('Action','Run');RunProcess('WorkspaceManager:GenerateReport');MarkExport('EXPORT_RETURNED');
 If Added Then Proj.DM_RemoveSourceDocument('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\compact_masks_20261016\paste_verification\Cap_Paste_Verification.OutJob');MarkExport('COMPLETE');ExportLog.Free;
End;
