"""Remove real thin mask webs and explicitly tent new blind-via pads."""
from pathlib import Path
import json,math,sys
from shapely.geometry import shape,box,mapping,Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';U=2.54e-6
plan=json.loads((H/'plan.json').read_text());old=shape(plan['Bottom_mask_opening'])
# Increase wire-bond exposure margin and merge openings separated by <0.12 mm of mask.
field=shape(plan['QD_mask_field'])
opening=old
native=json.loads((H/'planned_native.json').read_text())
for pad in native['pads']:
    if pad['component'] in ('R3','R4') and pad['number']=='2':
        land=translate(rotate(box(-pad['size_x']/2,-pad['size_y']/2,pad['size_x']/2,pad['size_y']/2),pad['rotation'],origin=(0,0)),pad['x'],pad['y'])
        opening=opening.difference(land.buffer(.13,quad_segs=32))
plan['QD_mask_field']=mapping(field);plan['Bottom_mask_opening']=mapping(opening)
(H/'plan.json').write_text(json.dumps(plan,indent=2))
lines=[]
for i,poly in enumerate(opening.geoms if hasattr(opening,'geoms') else [opening]):
    poly=orient(poly,sign=1);lines.append('G:=PCBServer.PCBGeometricPolygonFactory;')
    for hole,ring in [(False,poly.exterior)]+[(True,r) for r in poly.interiors]:
        lines.append('C:=PCBServer.PCBContourFactory;')
        for x,y in list(ring.coords)[:-1]:lines.append(f'C.AddPoint({round(x/U)},{round(y/U)});')
        lines.append(f'G.AddContourIsHole(C,{hole});')
    lines.append(f"Region:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Region.Kind:=eRegionKind_Copper;Region.Layer:=eBottomSolder;Region.Name:='SURFACE_MASK_OPEN_38_{i}';Region.SetGeometricPolygon(G);B.AddPCBObject(Region);")
script=r'''Procedure RepairMask;
Var B:IPCB_Board;I:IPCB_BoardIterator;Region:IPCB_Region;V:IPCB_Via;R:IPCB_Rule;VR:IPCB_RoutingViaStyleRule;W:IPCB_MaxMinWidthConstraint;PC:TPadCache;
 G:IPCB_GeometricPolygon;C:IPCB_Contour;Dead:Array[0..15] Of IPCB_Region;N,J,NV:Integer;Log:TStringList;Layer:TLayer;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 Log:=TStringList.Create;Log.Add('START');N:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));Region:=I.FirstPCBObject;
 While Region<>Nil Do Begin If Pos('SURFACE_MASK_OPEN_38_',Region.Name)=1 Then Begin Dead[N]:=Region;Inc(N);End;Region:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 PCBServer.PreProcess;
 Try
  For J:=0 To N-1 Do B.RemovePCBObject(Dead[J]);
__REGIONS__
  NV:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
  While V<>Nil Do Begin If V.Net<>Nil Then If V.Net.Name='GND' Then Begin
   V.BeginModify;PC:=V.GetState_Cache;PC.SolderMaskExpansion:=-MMsToCoord(0.2);PC.SolderMaskBottomExpansion:=-MMsToCoord(0.2);PC.SolderMaskExpansionValid:=eCacheManual;V.SetState_Cache(PC);
   V.SetState_SolderMaskExpansionFromHoleEdge(False);V.SetState_IsTenting(True);V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V.SetState_PasteMaskEnabled(False);V.EndModify;Inc(NV);
  End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);Log.Add('GND_VIAS='+IntToStr(NV));
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
  While R<>Nil Do Begin
   If R.Name='RF_SHIELD_L5_L6' Then Begin VR:=R;VR.ViaStyle:=eViaBlindBuriedPair;End;
   If R.Name='RF_50OHM_WIDTH' Then Begin W:=R;For J:=1 To 32 Do Begin W.MinWidth[J]:=MMsToCoord(0.11);W.MaxWidth[J]:=MMsToCoord(0.11);W.FavoredWidth[J]:=MMsToCoord(0.11);End;End;
   R:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 Log.Add('COMPLETE');Log.SaveToFile('C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\script\rf50_hdi_milling_20260920\mask_repair.txt');Log.Free;
End;
'''.replace('__REGIONS__','\n'.join(lines))
(H/'RepairMask.pas').write_text(script,encoding='ascii')
print('Prepared updated mask',opening.geom_type,'area',opening.area)
