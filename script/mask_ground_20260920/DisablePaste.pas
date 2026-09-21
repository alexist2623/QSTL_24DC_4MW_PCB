Var PasteLog:TStringList;PasteRoot:String;
Function BoolText(V:Boolean):String;
Begin If V Then Result:='1' Else Result:='0';End;
Procedure LogPaste(S:String);
Begin PasteLog.Add(S);PasteLog.SaveToFile(PasteRoot+'script\mask_ground_20260920\paste_flags_change.txt');End;
Procedure DisablePaste;
Var B:IPCB_Board;I:IPCB_BoardIterator;P:IPCB_Pad;V:IPCB_Via;C:IPCB_Component;PC:TPadCache;Name:String;NV,NS,NM,NKeep:Integer;
Begin
 PasteRoot:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\';
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(PasteRoot+'QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 PasteLog:=TStringList.Create;LogPaste('START');NV:=0;NS:=0;NM:=0;NKeep:=0;
 PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   C:=P.Component;If C=Nil Then Name:='MOUNT' Else Name:=C.Name.Text;
   LogPaste('BEFORE|PAD|'+Name+'|'+P.Name+'|'+BoolText(P.GetState_PasteMaskEnabled)+'|'+BoolText(P.GetState_IsTopPasteEnabled)+'|'+BoolText(P.GetState_IsBottomPasteEnabled));
   If (Name='MOUNT') Or (Pos('SMP',Name)=1) Then Begin
    P.BeginModify;
    P.SetState_PasteMaskUsePercent(False);P.SetState_PasteMaskExpansion(0);P.SetState_PasteMaskPercent(0);
    P.SetState_IsTopPasteEnabled(False);P.SetState_IsBottomPasteEnabled(False);P.SetState_PasteMaskEnabled(False);
    P.EndModify;
    If Name='MOUNT' Then Inc(NM) Else Inc(NS);
   End Else Inc(NKeep);
   LogPaste('AFTER|PAD|'+Name+'|'+P.Name+'|'+BoolText(P.GetState_PasteMaskEnabled)+'|'+BoolText(P.GetState_IsTopPasteEnabled)+'|'+BoolText(P.GetState_IsBottomPasteEnabled));
   P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
  While V<>Nil Do Begin
   V.BeginModify;
   PC:=V.GetState_Cache;PC.PasteMaskExpansion:=0;V.SetState_Cache:=PC;
   V.SetState_PasteMaskUsePercent(False);V.SetState_PasteMaskExpansion(0);V.SetState_PasteMaskEnabled(False);
   V.EndModify;
   LogPaste('AFTER|VIA|'+IntToStr(NV)+'|'+BoolText(V.GetState_PasteMaskEnabled));Inc(NV);V:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 LogPaste('COUNTS|'+IntToStr(NV)+'|'+IntToStr(NS)+'|'+IntToStr(NM)+'|'+IntToStr(NKeep));LogPaste('COMPLETE');PasteLog.Free;
End;
