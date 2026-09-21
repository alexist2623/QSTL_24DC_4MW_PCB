Procedure ProbeRule;
Var W:IPCB_MaxMinWidthConstraint;G:IPCB_Polygon;S:TPolySegment;L:TStringList;
Begin
 L:=TStringList.Create;
 Try
  W:=PCBServer.PCBRuleFactory(eRule_MaxMinWidth);
  W.MinWidth[eBottomLayer]:=MMsToCoord(0.11);W.MaxWidth[eBottomLayer]:=MMsToCoord(0.11);W.FavoredWidth[eBottomLayer]:=MMsToCoord(0.11);
  L.Add('WIDTH='+IntToStr(W.MinWidth[eBottomLayer]));
 Except L.Add('WIDTH_FAILED');End;
 Try
  G:=PCBServer.PCBObjectFactory(ePolyObject,eNoDimension,eCreate_Default);G.PointCount:=4;
  S:=G.Segments[0];S.Kind:=ePolySegmentLine;S.vx:=0;S.vy:=0;G.Segments[0]:=S;
  L.Add('POLYGON_SEGMENT_OK');
 Except L.Add('POLYGON_FAILED');End;
 L.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\rf50_hdi_milling_20260920\rule_probe.txt');L.Free;
End;
