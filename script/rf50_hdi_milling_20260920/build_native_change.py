"""Generate the guarded Altium change for the original project board."""
from pathlib import Path
import json,math
from shapely.geometry import shape
from shapely.geometry.polygon import orient
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';B='QSTL_24DC_4MW_PCB';U=2.54e-6
plan=json.loads((H/'plan.json').read_text());n=json.loads((H/'planned_native.json').read_text());old=json.loads((H/'before_native.json').read_text())
coord=lambda x:round(x/U)
lines=[]
def add_region(poly,layer,name,kind='eRegionKind_Copper'):
    poly=orient(poly,sign=1);lines.append(' G:=PCBServer.PCBGeometricPolygonFactory;')
    for hole,ring in [(False,poly.exterior)]+[(True,r) for r in poly.interiors]:
        lines.append(' C:=PCBServer.PCBContourFactory;')
        for x,y in list(ring.coords)[:-1]:lines.append(f' C.AddPoint({coord(x)},{coord(y)});')
        lines.append(f' G.AddContourIsHole(C,{hole});')
    lines.extend([f" Region:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Region.Kind:={kind};Region.Layer:={layer};Region.Name:='{name}';",' Region.SetGeometricPolygon(G);RegisterObject(B,Region);'])
opening=shape(plan['Bottom_mask_opening'])
for i,poly in enumerate(opening.geoms if hasattr(opening,'geoms') else [opening]):add_region(poly,'eBottomSolder',f'SURFACE_MASK_OPEN_38_{i}')
for layer in (2,3,4,5,32):add_region(shape(plan['QD_exclusion']),str(layer),f'QD_GND_EXCLUSION_L{layer}','eRegionKind_Cutout')
regions='\n'.join(lines)
init=[]
for i,m in enumerate(plan['pad_moves'],1):
    init.append(f" PN[{i}]:='{m['number']}';OX[{i}]:={coord(m['old'][0])};OY[{i}]:={coord(m['old'][1])};NX[{i}]:={coord(m['new'][0])};NY[{i}]:={coord(m['new'][1])};")
vias=[]
for v in plan['shield_vias']:vias.append(f" AddShield(B,GN,{coord(v['x'])},{coord(v['y'])});")
outline=[]
# A closed rounded rectangle on a dedicated mechanical fabrication layer.
for x1,y1,x2,y2 in [(8.1,40.35,11.4,40.35),(11.9,40.85,11.9,44.15),(11.4,44.65,8.1,44.65),(7.6,44.15,7.6,40.85)]:
    outline.append(f' AddFabTrack(B,{x1},{y1},{x2},{y2});')
for x,y,a0,a1 in [(11.4,40.85,270,360),(11.4,44.15,0,90),(8.1,44.15,90,180),(8.1,40.85,180,270)]:
    outline.append(f' AddFabArc(B,{x},{y},{a0},{a1});')
stack=[]
for i,(cu,di,mat) in enumerate(zip(plan['stack']['copper_mm'],plan['stack']['dielectric_mm']+[0],['1078RC69%','0.55mm H/HOZ CORE','7628RC50%','0.55mm H/HOZ CORE','1078RC69%',''])):
    stack.append(f' If N={i} Then Begin L.CopperThickness:={coord(cu)};'+(f" D:=L.Dielectric;D.DielectricHeight:={coord(di)};D.DielectricMaterial:='{mat}';" if di else '')+'End;')
script=r'''Var Log:TStringList;Root:String;PN:Array[1..24] Of String;OX,OY,NX,NY:Array[1..24] Of Integer;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile(Root+'script\rf50_hdi_milling_20260920\native_change.txt');End;
Procedure RegisterObject(B:IPCB_Board;O:IPCB_Primitive);Begin B.AddPCBObject(O);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,O.I_ObjectAddress);End;
Procedure AddShield(B:IPCB_Board;GN:IPCB_Net;X,Y:Integer);
Var V:IPCB_Via;
Begin
 V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=X;V.Y:=Y;V.Mode:=ePadMode_Simple;
 V.Size:=MMsToCoord(0.25);V.HoleSize:=MMsToCoord(0.1);V.LowLayer:=eMidLayer4;V.HighLayer:=eBottomLayer;V.Net:=GN;
 V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V.SetState_PasteMaskEnabled(False);
 RegisterObject(B,V);
End;
Procedure AddFabTrack(B:IPCB_Board;X1,Y1,X2,Y2:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.Layer:=eMechanical2;
 T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(0.01);RegisterObject(B,T);End;
Procedure AddFabArc(B:IPCB_Board;X,Y,A0,A1:Double);
Var A:IPCB_Arc;
Begin A:=PCBServer.PCBObjectFactory(eArcObject,eNoDimension,eCreate_Default);A.Layer:=eMechanical2;A.XCenter:=MMsToCoord(X);A.YCenter:=MMsToCoord(Y);
 A.Radius:=MMsToCoord(0.5);A.StartAngle:=A0;A.EndAngle:=A1;A.LineWidth:=MMsToCoord(0.01);RegisterObject(B,A);End;
Procedure ApplyRF50;
Var B:IPCB_Board;Doc:IServerDocument;I:IPCB_BoardIterator;Pad:IPCB_Pad;Comp:IPCB_Component;Via:IPCB_Via;Track:IPCB_Track;Arc:IPCB_Arc;
 Region:IPCB_Region;Poly:IPCB_Polygon;GN,Net:IPCB_Net;Rule:IPCB_Rule;Clear:IPCB_ClearanceConstraint;Width:IPCB_MaxMinWidthConstraint;VR:IPCB_RoutingViaStyleRule;
 Dead:Array[0..255] Of IPCB_Primitive;Polys:Array[0..7] Of IPCB_Polygon;C:IPCB_Contour;G:IPCB_GeometricPolygon;Seg:TPolySegment;
 Stack:IPCB_LayerStack_V7;L:IPCB_LayerObject_V7;D:IPCB_DielectricObject;FabText:IPCB_Text;
 J,N,ND,NP,NV,NC,NPoly,NT,NA:Integer;CPWScope:String;
Begin
 Root:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\';
 Doc:=Client.OpenDocument('PCB',Root+'QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc');If Doc=Nil Then Exit;Client.ShowDocument(Doc);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(Root+'QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 Log:=TStringList.Create;Mark('START');
__INIT__
 NP:=0;NV:=0;ND:=0;NC:=0;GN:=Nil;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;
 While Pad<>Nil Do Begin Comp:=Pad.Component;If Comp<>Nil Then If Comp.Name.Text='Q1' Then For J:=1 To 24 Do If Pad.Name=PN[J] Then If (Abs(Pad.X-OX[J])<2) And (Abs(Pad.Y-OY[J])<2) Then Inc(NP);Pad:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));Via:=I.FirstPCBObject;
 While Via<>Nil Do Begin Inc(NV);Via:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));Net:=I.FirstPCBObject;
 While Net<>Nil Do Begin If Net.Name='GND' Then GN:=Net;Net:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('PREFLIGHT='+IntToStr(NP)+','+IntToStr(NV));If (NP<>24) Or (NV<>72) Or (GN=Nil) Then Begin Mark('STOP_PREFLIGHT');Log.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));Region:=I.FirstPCBObject;
 While Region<>Nil Do Begin
  If (Pos('SURFACE_MASK_OPEN_38_',Region.Name)=1) Or (Pos('QD_GND_EXCLUSION_',Region.Name)=1) Or ((Region.Layer=eBottomLayer) And (Region.Kind=eRegionKind_Cutout)) Then Begin Dead[ND]:=Region;Inc(ND);End;
  Region:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);Mark('REGIONS_REPLACE='+IntToStr(ND));
 PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;
  While Pad<>Nil Do Begin Comp:=Pad.Component;If Comp<>Nil Then If Comp.Name.Text='Q1' Then For J:=1 To 24 Do If Pad.Name=PN[J] Then Begin Pad.BeginModify;Pad.X:=NX[J];Pad.Y:=NY[J];Pad.EndModify;End;Pad:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));Via:=I.FirstPCBObject;
  While Via<>Nil Do Begin For J:=1 To 24 Do If (Abs(Via.X-OX[J])<2) And (Abs(Via.Y-OY[J])<2) Then Begin Via.BeginModify;Via.X:=NX[J];Via.Y:=NY[J];Via.EndModify;Inc(NC);End;Via:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject));Track:=I.FirstPCBObject;NT:=0;
  While Track<>Nil Do Begin If Track.Net<>Nil Then Begin
   Track.BeginModify;
   For J:=1 To 24 Do Begin
    If (Abs(Track.X1-OX[J])<2) And (Abs(Track.Y1-OY[J])<2) Then Begin Track.X1:=NX[J];Track.Y1:=NY[J];End;
    If (Abs(Track.X2-OX[J])<2) And (Abs(Track.Y2-OY[J])<2) Then Begin Track.X2:=NX[J];Track.Y2:=NY[J];End;
   End;
   If Track.Layer=eBottomLayer Then Begin Track.Width:=MMsToCoord(0.11);Inc(NT);End;Track.EndModify;
  End;Track:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eArcObject));Arc:=I.FirstPCBObject;NA:=0;
  While Arc<>Nil Do Begin If (Arc.Layer=eBottomLayer) And (Arc.Net<>Nil) Then Begin Arc.BeginModify;Arc.LineWidth:=MMsToCoord(0.11);Arc.EndModify;Inc(NA);End;Arc:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  Mark('PAD_VIAS_MOVED='+IntToStr(NC)+'|RF='+IntToStr(NT)+','+IntToStr(NA));
  Stack:=B.LayerStack_V7;L:=Stack.FirstLayer;N:=0;
  While L<>Nil Do Begin
__STACK__
   Inc(N);L:=Stack.NextLayer(L);
  End;Mark('STACK_UPDATED');
  For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);
__REGIONS__
  Mark('MASK_AND_CUTOUTS_UPDATED');
  CPWScope:='InNet(''GND'') And OnLayer(''L6_RF_QD'')';
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=I.FirstPCBObject;
  While Rule<>Nil Do Begin
   If Rule.Name='Clearance' Then Begin Rule.Scope1Expression:='Not ('+CPWScope+')';Rule.Scope2Expression:='Not ('+CPWScope+')';End;
   If Rule.Name='Width' Then Rule.Scope1Expression:='Not OnLayer(''L6_RF_QD'')';
   If Rule.Name='RoutingVias' Then Rule.Scope1Expression:='Not (IsVia And InNet(''GND''))';
   Rule:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  Clear:=PCBServer.PCBRuleFactory(eRule_Clearance);Clear.Name:='RF_CPW_GND_GAP_0P2';Clear.Scope1Expression:=CPWScope;Clear.Scope2Expression:='All';Clear.Gap:=MMsToCoord(0.2);Clear.DRCEnabled:=True;RegisterObject(B,Clear);
  Width:=PCBServer.PCBRuleFactory(eRule_MaxMinWidth);Width.Name:='RF_50OHM_WIDTH';Width.Scope1Expression:='OnLayer(''L6_RF_QD'')';Width.MinWidth[eBottomLayer]:=MMsToCoord(0.11);Width.MaxWidth[eBottomLayer]:=MMsToCoord(0.11);Width.FavoredWidth[eBottomLayer]:=MMsToCoord(0.11);Width.DRCEnabled:=True;RegisterObject(B,Width);
  VR:=PCBServer.PCBRuleFactory(eRule_RoutingViaStyle);VR.Name:='RF_SHIELD_L5_L6';VR.Scope1Expression:='IsVia And InNet(''GND'')';VR.MinWidth:=MMsToCoord(0.25);VR.MaxWidth:=MMsToCoord(0.25);VR.PreferedWidth:=MMsToCoord(0.25);VR.MinHoleWidth:=MMsToCoord(0.1);VR.MaxHoleWidth:=MMsToCoord(0.1);VR.PreferedHoleWidth:=MMsToCoord(0.1);VR.DRCEnabled:=True;RegisterObject(B,VR);
  B.InvalidateScopeTester;B.ValidateScopeTester;Mark('RULES_UPDATED');
__VIAS__
  Mark('SHIELD_VIAS_ADDED');
  Poly:=PCBServer.PCBObjectFactory(ePolyObject,eNoDimension,eCreate_Default);Poly.Layer:=eBottomLayer;Poly.Net:=GN;Poly.Name:='L6_RF_COPLANAR_GND';Poly.PolygonType:=eSignalLayerPolygon;Poly.PolyHatchStyle:=ePolySolid;Poly.PourOver:=ePolygonPourOver_SameNet;Poly.RemoveDead:=True;Poly.RemoveNarrowNecks:=True;Poly.NeckWidthThreshold:=MMsToCoord(0.1);Poly.RemoveIslandsByArea:=False;Poly.TrackSize:=MMsToCoord(0.1);Poly.Grid:=MMsToCoord(0.1);Poly.PointCount:=4;
  Seg:=Poly.Segments[0];Seg.Kind:=ePolySegmentLine;Seg.vx:=MMsToCoord(0.25);Seg.vy:=MMsToCoord(0.25);Poly.Segments[0]:=Seg;
  Seg.vx:=MMsToCoord(19.25);Poly.Segments[1]:=Seg;Seg.vy:=MMsToCoord(67.65);Poly.Segments[2]:=Seg;Seg.vx:=MMsToCoord(0.25);Poly.Segments[3]:=Seg;RegisterObject(B,Poly);
__OUTLINE__
  FabText:=PCBServer.PCBObjectFactory(eTextObject,eNoDimension,eCreate_Default);FabText.Layer:=eMechanical3;FabText.MoveToXY(MMsToCoord(21),MMsToCoord(43));FabText.Size:=MMsToCoord(0.8);FabText.Width:=MMsToCoord(0.12);FabText.Text:='BOTTOM BLIND SLOT: 4.3 x 4.3, R0.5, DEPTH 1.2 mm; NON-PLATED';RegisterObject(B,FabText);
  Mark('CAVITY_ANNOTATED');
  NPoly:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin Polys[NPoly]:=Poly;Inc(NPoly);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For J:=0 To NPoly-1 Do Begin Poly:=Polys[J];Poly.SetState_CopperPourInvalid;Poly.Rebuild;Mark('REPOURED='+Poly.Name);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Mark('SAVED');Mark('COMPLETE');Log.Free;
End;
'''
for key,value in [('INIT','\n'.join(init)),('STACK','\n'.join(stack)),('REGIONS',regions),('VIAS','\n'.join(vias)),('OUTLINE','\n'.join(outline))]:script=script.replace('__'+key+'__',value)
(H/'ApplyRF50.pas').write_text(script,encoding='ascii')
print('Generated',len(script.splitlines()),'lines')
