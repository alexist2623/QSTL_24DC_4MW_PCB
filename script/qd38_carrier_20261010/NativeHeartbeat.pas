Procedure NativeHeartbeat;
Var L : TStringList;
Begin
 L := TStringList.Create;
 L.Add('ALTIUM_SCRIPT_ENTRY_OK');
 L.Add(DateTimeToStr(Now));
 L.SaveToFile('C:\GIT_Workspace\QSTL_24DC_4MW_PCB\script\qd38_carrier_20261010\native_heartbeat.txt');
 L.Free;
End;
