Var B:IPCB_Board;D:IServerDocument;Log:TStringList;I:IPCB_BoardIterator;C:IPCB_Connection;N:IPCB_Net;Count:Integer;S:String;
Procedure CountStage(Stage:String);
Begin Count:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));C:=I.FirstPCBObject;
While C<>Nil Do Begin Inc(Count);S:='';If C.Net<>Nil Then S:=C.Net.Name;Log.Add(Stage+'|'+S+'|'+FloatToStr(CoordToMMs(C.X1))+','+FloatToStr(CoordToMMs(C.Y1))+'|'+FloatToStr(CoordToMMs(C.X2))+','+FloatToStr(CoordToMMs(C.Y2)));C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);Log.Add(Stage+'_COUNT='+IntToStr(Count));Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\smp_broad_rounding_20261016\connection_recalculation.txt');End;
Procedure RecalculateConnections;
Begin
D:=Client.OpenDocument('PCB','C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
If LowerCase(B.FileName)<>LowerCase('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\QSTL_QD4_2SET_38PAD\QSTL_QD4_2SET_38PAD.PcbDoc') Then Exit;
Log:=TStringList.Create;CountStage('BEFORE');
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;CountStage('AFTER_REBUILD');
B.SetState_DocumentHasChanged;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
Log.Add('COMPLETE');Log.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\smp_broad_rounding_20261016\connection_recalculation.txt');Log.Free;
End;
