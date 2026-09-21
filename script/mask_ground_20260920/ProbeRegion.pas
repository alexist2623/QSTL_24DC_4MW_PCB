Procedure ProbeRegion;
Var R:IPCB_Region;G:IPCB_GeometricPolygon;C,H:IPCB_Contour;L:TStringList;
Begin
 L:=TStringList.Create;
 R:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);
 C:=PCBServer.PCBContourFactory;C.AddPoint(0,0);C.AddPoint(100000,0);C.AddPoint(100000,100000);C.AddPoint(0,100000);
 H:=PCBServer.PCBContourFactory;H.AddPoint(25000,25000);H.AddPoint(25000,75000);H.AddPoint(75000,75000);H.AddPoint(75000,25000);
 G:=PCBServer.PCBGeometricPolygonFactory;G.AddContourIsHole(C,False);G.AddContourIsHole(H,True);R.SetGeometricPolygon(G);
 L.Add('REGION_HOLES='+IntToStr(R.GetHoleCount));L.Add('COMPLETE');
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\mask_ground_20260920\region_probe.txt');L.Free;
End;
