from pathlib import Path
import json
H=Path(__file__).resolve().parent;g=json.loads((H/'geometry.json').read_text());dc=json.loads((H/'dc_routes.json').read_text());assert not dc['validation']['errors']
src=(H/'ApplyRF6.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Function AddSignalVia')]
routes=[]
for t in dc['tracks']:routes.append("AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{2:'eMidLayer1',4:'eMidLayer3'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ['x1','y1','x2','y2','width'])))
rm=g['removed_vias'][0];assert len(g['removed_vias'])==1 and len(g['vias'])==72
s=r'''
@HELPERS@
Procedure FinalDC;
Var B:IPCB_Board;I:IPCB_BoardIterator;O:IPCB_Primitive;V:IPCB_Via;P:IPCB_Pad;C:IPCB_Component;R:IPCB_Region;N:IPCB_Net;Poly:IPCB_Polygon;D:IServerDocument;
 Dead:Array[0..511] Of IPCB_Primitive;Ns:Array[0..63] Of IPCB_Net;Polys:Array[0..7] Of IPCB_Polygon;
 Bridge:IPCB_Via;PT,PB:IPCB_Region;ND,NV,NR,NP,J,NN,NPoly:Integer;S:String;L:TStringList;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>'c:\jeonghyunpark\workspace\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb\qstl_24dc_4mw_pcb.pcbdoc' Then Exit;
 ND:=0;NV:=0;NR:=0;NP:=0;Bridge:=Nil;PT:=Nil;PB:=Nil;L:=TStringList.Create;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eViaObject,eRegionObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
  If O.ObjectId=eTrackObject Then If O.Net<>Nil Then If Copy(O.Net.Name,1,3)='ZIF' Then If (O.Layer=eMidLayer1) Or (O.Layer=eMidLayer3) Then Begin Dead[ND]:=O;Inc(ND);End;
  If O.ObjectId=eViaObject Then Begin V:=O;Inc(NV);If (Abs(V.X-MMsToCoord(13.35))<4) And (Abs(V.Y-MMsToCoord(16.4))<4) Then Bridge:=V;End;
  If O.ObjectId=eRegionObject Then Begin R:=O;If R.Name='@PT@' Then Begin PT:=R;Inc(NR);End;If R.Name='@PB@' Then Begin PB:=R;Inc(NR);End;End;
  O:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 L.Add('COUNTS='+IntToStr(ND)+','+IntToStr(NV)+','+IntToStr(NR));L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_final_dc.txt');
 If (ND<>292) Or (NV<>73) Or (NR<>2) Or (Bridge=Nil) Or (PT=Nil) Or (PB=Nil) Then Exit;
 PCBServer.PreProcess;
 Try
  For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);B.RemovePCBObject(Bridge);B.RemovePCBObject(PT);B.RemovePCBObject(PB);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin C:=P.Component;S:='';If C<>Nil Then If P.Name='2' Then Begin If C.Name.Text='R2' Then S:='ZIF25';If C.Name.Text='R3' Then S:='ZIF23';End;
   If S<>'' Then Begin P.Net:=FindNet(B,S);P.SetState_InNet(True);Inc(NP);End;P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
  While V<>Nil Do Begin
   If (Abs(V.X-MMsToCoord(17.5))<4) And (Abs(V.Y-MMsToCoord(41.45))<4) Then V.Net:=FindNet(B,'ZIF25');
   If (Abs(V.X-MMsToCoord(12.7))<4) And (Abs(V.Y-MMsToCoord(46.4))<4) Then V.Net:=FindNet(B,'ZIF23');
   V:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  @ROUTES@
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;NPoly:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NPoly]:=Poly;Inc(NPoly);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NPoly-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin Ns[NN]:=N;Inc(NN);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin N:=Ns[J];N.ConnectivelyInValidate;N.Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveCurrent;
 D:=Client.GetDocumentByPath(ExtractFilePath(B.FileName)+'QSTL_24DC_4MW_PCB.SchDoc');If D<>Nil Then Client.CloseDocument(D);D:=Client.GetDocumentByPath(ExtractFilePath(B.FileName)+'QSTL_24DC_4MW_PCB.SchLib');If D<>Nil Then Client.CloseDocument(D);
 L.Add('PADS_RENETTED='+IntToStr(NP));L.Add('DC_EXTRA_LAYER_TRANSITION_VIAS=0');L.Add('COMPLETE');L.SaveToFile(ExtractFilePath(B.FileName)+'work\rf6_final_dc.txt');L.Free;
End;
'''
for k,v in dict(HELPERS=helpers,ROUTES='\n'.join(routes),PT=rm['paste_names'][0],PB=rm['paste_names'][1]).items():s=s.replace('@'+k+'@',v)
(H/'FinalDC.pas').write_text(s,encoding='utf-8');print('DC196 tracks; one internal layer per net; remove one extra via and its two paste openings.')
