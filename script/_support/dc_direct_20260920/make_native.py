from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;W=H.parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');B='QSTL_24DC_4MW_PCB'
dc=json.loads((H/'dc_routes.json').read_text());assert not dc['validation']['errors'];n=json.loads((H/'baseline_native.json').read_text())
assert hashlib.sha256((P/(B+'.PcbDoc')).read_bytes()).hexdigest()==n['source_sha256']
src=(W/'rf_stubless_20260920/ApplyStubless.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Procedure ApplyStubless;')]
lines=[]
for t in dc['tracks']:lines.append("  AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{2:'eMidLayer1',4:'eMidLayer3'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ['x1','y1','x2','y2','width'])))
init=[]
for i,(key,c) in enumerate(dc['pin_changes'].items()):
 p=next(p for p in n['pads'] if p['component']+'-'+p['number']==key) if False else next(p for p in n['pads'] if p['component'] and p['component']+'-'+p['number']==key)
 init.append(" X[%d]:=%d;Y[%d]:=%d;OldN[%d]:='%s';NewN[%d]:='%s';"%(i,round(p['x']/2.54e-6),i,round(p['y']/2.54e-6),i,c['old'],i,c['new']))
script=r'''
@HELPERS@
Var DCLog:TStringList;DCPath:String;
Procedure MarkDC(S:String);Begin DCLog.Add(S);DCLog.SaveToFile(DCPath+'work\dc_direct_apply.txt');End;
Procedure ApplyDirectDC;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;O:IPCB_Primitive;P:IPCB_Pad;V:IPCB_Via;Poly:IPCB_Polygon;
 Dead:Array[0..1023] Of IPCB_Primitive;Polys:Array[0..7] Of IPCB_Polygon;
 ChangePad:Array[0..2] Of IPCB_Pad;ChangeVia:Array[0..2] Of IPCB_Via;
 X,Y:Array[0..2] Of Integer;OldN,NewN:Array[0..2] Of String;
 NC,NP,NV,ND,NT,NRF,NARF,NPoly,NPChange,NVChange,J,K:Integer;N:String;Good:Boolean;
Begin
 DCPath:='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB\';
 D:=Client.OpenDocument('PCB',DCPath+'QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(DCPath+'QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 DCLog:=TStringList.Create;MarkDC('START');NC:=0;NP:=0;NV:=0;ND:=0;NT:=0;NRF:=0;NARF:=0;NPoly:=0;NPChange:=0;NVChange:=0;Good:=True;
@INIT@
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject,ePadObject,eViaObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
  If O.ObjectId=eComponentObject Then Inc(NC);
  If O.ObjectId=ePadObject Then Begin
   Inc(NP);P:=O;
   For K:=0 To 2 Do If (Abs(P.X-X[K])<4) And (Abs(P.Y-Y[K])<4) Then Begin
    If P.Net=Nil Then Good:=False Else If P.Net.Name<>OldN[K] Then Good:=False;
    ChangePad[K]:=P;Inc(NPChange);
   End;
  End;
  If O.ObjectId=eViaObject Then Begin
   Inc(NV);V:=O;
   For K:=0 To 2 Do If (Abs(V.X-X[K])<4) And (Abs(V.Y-Y[K])<4) Then Begin
    If V.Net=Nil Then Good:=False Else If V.Net.Name<>OldN[K] Then Good:=False;
    ChangeVia[K]:=V;Inc(NVChange);
   End;
  End;
  O:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eArcObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
  N:='';If O.Net<>Nil Then N:=O.Net.Name;
  If Copy(N,1,3)='ZIF' Then Begin
   If O.ObjectId<>eTrackObject Then Good:=False;
   If O.Layer=eTopLayer Then Inc(NT) Else Begin
    If (O.Layer<>eMidLayer1) And (O.Layer<>eMidLayer3) Then Good:=False;
    Dead[ND]:=O;Inc(ND);
   End;
  End;
  If (Copy(N,1,2)='MW') Or (Copy(N,1,1)='S') Then Begin
   If O.Layer<>eBottomLayer Then Good:=False;
   If O.ObjectId=eTrackObject Then Inc(NRF) Else Inc(NARF);
  End;
  O:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
 While Poly<>Nil Do Begin Polys[NPoly]:=Poly;Inc(NPoly);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 MarkDC('COUNTS='+IntToStr(NC)+','+IntToStr(NP)+','+IntToStr(NV)+','+IntToStr(ND)+','+IntToStr(NT)+','+IntToStr(NRF)+','+IntToStr(NARF)+','+IntToStr(NPoly));
 If (NC<>22) Or (NP<>147) Or (NV<>65) Or (ND<>305) Or (NT<>24) Or (NRF<>19) Or (NARF<>11) Or (NPoly<>3) Or (NPChange<>3) Or (NVChange<>3) Or (Not Good) Then Begin MarkDC('PREFLIGHT_FAILED');DCLog.Free;Exit;End;
 MarkDC('PREFLIGHT_PASSED');PCBServer.PreProcess;
 Try
  For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);
  For K:=0 To 2 Do Begin
   P:=ChangePad[K];V:=ChangeVia[K];P.Net:=FindNet(B,NewN[K]);V.Net:=FindNet(B,NewN[K]);
  End;
@ROUTES@
 Finally PCBServer.PostProcess;End;
 MarkDC('DC_ROUTES_AND_THREE_PIN_ASSIGNMENTS_APPLIED');
 B.RebuildPadCaches;B.ConnectivelyValidateNets;
 For J:=0 To NPoly-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveCurrent;
 MarkDC('SAVED');
 D:=Client.GetDocumentByPath(DCPath+'QSTL_24DC_4MW_PCB.SchDoc');If D<>Nil Then Client.CloseDocument(D);
 D:=Client.GetDocumentByPath(DCPath+'QSTL_24DC_4MW_PCB.SchLib');If D<>Nil Then Client.CloseDocument(D);
 MarkDC('LOGICAL_DOCUMENTS_CLOSED');MarkDC('COMPLETE');DCLog.Free;
End;
'''
script=script.replace('@HELPERS@',helpers).replace('@INIT@','\n'.join(init)).replace('@ROUTES@','\n'.join(lines));(H/'ApplyDirectDC.pas').write_text(script,encoding='utf-8')
check=(W/'dc_centered_20260920/ReopenCheck.pas').read_text().replace('DC_centered_DRC.html','DC_direct_DRC.html').replace('dc_centered_drc.txt','dc_direct_drc.txt');(H/'ReopenCheck.pas').write_text(check,encoding='utf-8')
check=(W/'symmetric_placement_20260920/ValidateSchematic.pas').read_text().replace('symmetric_schematic_compile.txt','dc_direct_schematic_compile.txt');(H/'ValidateSchematic.pas').write_text(check,encoding='utf-8')
print('Prepared guarded replacement:',len(dc['tracks']),'tracks; three DC pad/via net assignments; zero added vias.')
