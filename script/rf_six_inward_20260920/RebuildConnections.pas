Var ConnLog:TStringList;ConnPath:String;
Procedure MarkConn(S:String);Begin ConnLog.Add(S);ConnLog.SaveToFile(ConnPath+'work\rf6_connection_rebuild.txt');End;
Procedure CountConnections(B:IPCB_Board;Stage:String);
Var I:IPCB_BoardIterator;C:IPCB_Connection;N:Integer;Name:String;
Begin
 N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eConnectionObject));I.AddFilter_Method(eProcessAll);C:=I.FirstPCBObject;
 While C<>Nil Do Begin
  Inc(N);Name:='';If C.Net<>Nil Then Name:=C.Net.Name;
  MarkConn(Stage+'|'+Name+'|'+IntToStr(C.X1)+','+IntToStr(C.Y1)+'|'+IntToStr(C.X2)+','+IntToStr(C.Y2));
  C:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkConn(Stage+'_COUNT='+IntToStr(N));
End;
Procedure RebuildConnections;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;N:IPCB_Net;Nets:Array[0..63] Of IPCB_Net;J,NC:Integer;
Begin
 ConnPath:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\';
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(ConnPath+'QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 ConnLog:=TStringList.Create;MarkConn('START');CountConnections(B,'BEFORE');
 NC:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin Nets[NC]:=N;Inc(NC);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If NC<>37 Then Begin MarkConn('PREFLIGHT_FAILED');ConnLog.Free;Exit;End;
 For J:=0 To NC-1 Do Begin N:=Nets[J];N.ConnectivelyInValidate;N.Rebuild;End;
 B.ConnectivelyValidateNets;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 CountConnections(B,'AFTER_REBUILD');B.SetState_DocumentHasChanged;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 MarkConn('SAVED');MarkConn('COMPLETE');ConnLog.Free;
End;
