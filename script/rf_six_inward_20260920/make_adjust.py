from pathlib import Path
import sys,json,math,importlib.util
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB';U=2.54e-6;q=lambda v:round(v/U)
sys.path[:0]=[str(W/'qd_center_revision'),str(W/'final_routing/schematic'),str(W/'zif_revision_v2/board')]
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);reader.SOURCE=P/(B+'.PcbDoc');n=reader.read_native()
g=json.loads((H/'geometry.json').read_text());dc=json.loads((H/'dc_routes.json').read_text());rf=json.loads((H/'rf_routes.json').read_text());np={p['component']+'-'+p['number']:p for p in g['pads'] if p['component']};regions=read_regions(snapshot(P/(B+'.PcbDoc'))['Regions6/Data'])
assert len(n['vias'])==73 and len(n['tracks'])==346 and len(n['arcs'])==18
init=[];move=[]
for i,p in enumerate([p for p in n['pads'] if p['component'] in ['R3','R4','C3','C4']],1):
 z=np[p['component']+'-'+p['number']];names=[r['name'] for r in regions if r['layer'] in [35,36] and math.dist((r['geometry'].centroid.x,r['geometry'].centroid.y),(p['x'],p['y']))<4*U];assert len(names)==2
 init.append(f"OX[{i}]:={q(p['x'])};OY[{i}]:={q(p['y'])};NX[{i}]:={q(z['x'])};NY[{i}]:={q(z['y'])};RN1[{i}]:='{names[0]}';RN2[{i}]:='{names[1]}';")
for c in g['components']:
 if c['designator'] in ['R3','R4','C3','C4']:move.append(f"If C.Name.Text='{c['designator']}' Then Begin C.MoveToXY({q(c['x'])},{q(c['y'])});Inc(NC);End;")
src=(H/'ApplyRF6.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Function AddSignalVia')]
lines=[]
for t in dc['tracks']+rf['tracks']:lines.append("AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{2:'eMidLayer1',4:'eMidLayer3',32:'eBottomLayer'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ['x1','y1','x2','y2','width'])))
for a in rf['arcs']:lines.append("AddRFArc(B,FindNet(B,'%s'),eBottomLayer,%s);"%(a['net'],','.join(f'{a[k]:.12f}' for k in ['cx','cy','radius','width','start_angle','end_angle'])))
s=r'''
@HELPERS@
Procedure AdjustRF6;
Var B:IPCB_Board;I:IPCB_BoardIterator;C:IPCB_Component;P:IPCB_Pad;V:IPCB_Via;R:IPCB_Region;O:IPCB_Primitive;N:IPCB_Net;Poly:IPCB_Polygon;
 PS:Array[1..8] Of IPCB_Pad;VS:Array[1..8] Of IPCB_Via;A1,A2:Array[1..8] Of IPCB_Region;
 OX,OY,NX,NY:Array[1..8] Of Integer;RN1,RN2:Array[1..8] Of String;
 Dead:Array[0..1023] Of IPCB_Primitive;Ns:Array[0..63] Of IPCB_Net;Polys:Array[0..7] Of IPCB_Polygon;
 J,NP,NV,NR,ND,NC,NN,NPoly:Integer;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>'c:\jeonghyunpark\workspace\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb.pcbdoc' Then Exit;
 @INIT@
 L:=TStringList.Create;NP:=0;NV:=0;NR:=0;ND:=0;NC:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject,eViaObject,eRegionObject,eTrackObject,eArcObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
  If O.ObjectId=ePadObject Then Begin P:=O;For J:=1 To 8 Do If (Abs(P.X-OX[J])<4) And (Abs(P.Y-OY[J])<4) Then Begin PS[J]:=P;Inc(NP);End;End;
  If O.ObjectId=eViaObject Then Begin V:=O;For J:=1 To 8 Do If (Abs(V.X-OX[J])<4) And (Abs(V.Y-OY[J])<4) Then Begin VS[J]:=V;Inc(NV);End;End;
  If O.ObjectId=eRegionObject Then Begin R:=O;For J:=1 To 8 Do Begin If R.Name=RN1[J] Then Begin A1[J]:=R;Inc(NR);End;If R.Name=RN2[J] Then Begin A2[J]:=R;Inc(NR);End;End;End;
  If (O.ObjectId=eTrackObject) Or (O.ObjectId=eArcObject) Then Begin C:=O.Component;If C=Nil Then If O.Net<>Nil Then If O.Net.Name<>'GND' Then If (O.Layer=eMidLayer1) Or (O.Layer=eMidLayer3) Or (O.Layer=eBottomLayer) Then Begin Dead[ND]:=O;Inc(ND);End;End;
  O:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('PREFLIGHT='+IntToStr(NP)+','+IntToStr(NV)+','+IntToStr(NR)+','+IntToStr(ND));L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_adjust.txt');
 If (NP<>8) Or (NV<>8) Or (NR<>16) Or (ND<>340) Then Exit;
 PCBServer.PreProcess;
 Try
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
  While C<>Nil Do Begin
   @MOVES@
   If C.Name.Text='Q1' Then Begin C.ChangeNameAutoposition(eAutoPos_Manual);C.Name.MoveToXY(MMsToCoord(9.0),MMsToCoord(52.0));End;
   C:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  For J:=1 To 8 Do Begin PS[J].MoveToXY(NX[J],NY[J]);VS[J].MoveToXY(NX[J],NY[J]);A1[J].MoveByXY(NX[J]-OX[J],NY[J]-OY[J]);A2[J].MoveByXY(NX[J]-OX[J],NY[J]-OY[J]);End;
  For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);
  @ROUTES@
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;NPoly:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NPoly]:=Poly;Inc(NPoly);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NPoly-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin Ns[NN]:=N;Inc(NN);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin N:=Ns[J];N.ConnectivelyInValidate;N.Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveCurrent;
 L.Add('MOVED='+IntToStr(NC));L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_adjust.txt');L.Free;
End;
'''
for k,v in {'HELPERS':helpers,'INIT':'\n'.join(init),'MOVES':'\n'.join(move),'ROUTES':'\n'.join(lines)}.items():s=s.replace('@'+k+'@',v)
(H/'AdjustRF6.pas').write_text(s);print('Prepared 0.2 mm top-pair clearance adjustment.')
