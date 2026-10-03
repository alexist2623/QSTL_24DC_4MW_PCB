Procedure Fix(Path:String);
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;C:IPCB_Component;PC:TPadCache;
Begin D:=Client.OpenDocument('PCB',Path);If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(Path) Then Exit;
PCBServer.PreProcess;Try
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin C.SourceDesignator:=C.Name.Text;C.SourceLibReference:=C.Pattern;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
While V<>Nil Do Begin
PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
PC:=V.GetState_Cache;PC.SolderMaskExpansionValid:=eCacheManual;PC.SolderMaskExpansion:=MMsToCoord(-1);PC.SolderMaskBottomExpansion:=MMsToCoord(-1);PC.PasteMaskExpansionValid:=eCacheManual;PC.PasteMaskExpansion:=MMsToCoord(-2);V.SetState_Cache(PC);
V.SetState_SolderMaskExpansionFromHoleEdge(False);V.SetState_IsTenting(True);V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V.SetState_PasteMaskEnabled(False);
PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);
V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Client.CloseDocument(D);
End;
Procedure FixViaFlags;
Begin

Fix('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_2xZIF\ZIF_to_2xZIF.PcbDoc');
Fix('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\FPC_Adapters_20261002\ZIF_to_DSUB25\ZIF_to_DSUB25.PcbDoc');
End;