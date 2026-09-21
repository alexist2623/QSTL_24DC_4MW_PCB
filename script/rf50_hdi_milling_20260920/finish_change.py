"""Prepare continuation after native polygon binding failure, preserving completed edits."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB'
f=P/'docs/DESIGN_REQUIREMENTS.md';s=f.read_text(encoding='utf-8').replace('Use via-in-pad for QD and RF tee R/C pads. Place R/C close together, with C naturally aligned to the RF path.', 'Use via-in-pad for QD and the DC-feeding bias-resistor pads. RF series capacitors remain entirely on Bottom: remove their redundant through vias to avoid RF stubs. Retain their normal SMD pads and paste. Place R/C close together, with C naturally aligned to the RF path.')
f.write_text(s,encoding='utf-8')
source=(H/'ApplyRF50.pas').read_text();head=source[:source.index('Procedure ApplyRF50;')]
tail=source[source.index('  Poly:=PCBServer.PCBObjectFactory(ePolyObject'):]
plan=json.loads((H/'plan.json').read_text());fixes=[];U=2.54e-6
for m in plan['dc_moves']:
    x,y=[round(v/U) for v in m['old']];xx,yy=[round(v/U) for v in m['new']]
    fixes.append(f"If Track.Net.Name='{m['net']}' Then Begin If (Abs(Track.X1-{x})<2) And (Abs(Track.Y1-{y})<2) Then Begin Track.X1:={xx};Track.Y1:={yy};End;If (Abs(Track.X2-{x})<2) And (Abs(Track.Y2-{y})<2) Then Begin Track.X2:={xx};Track.Y2:={yy};End;End;")
dcfix='''
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eTrackObject));Track:=It.FirstPCBObject;
 While Track<>Nil Do Begin If Track.Net<>Nil Then Begin Track.BeginModify;
'''+ '\n'.join(fixes)+'''
 Track.EndModify;End;Track:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);Mark('DC_CLEARANCE_ADJUSTED');
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eRuleObject));Rule:=It.FirstPCBObject;
 While Rule<>Nil Do Begin If Rule.Name='RF_CPW_GND_GAP_0P2' Then Rule.NetScope:=eNetScope_DifferentNetsOnly;Rule:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);
'''
# Separate statements to identify the exact unsupported binding before retrying it.
tail=tail.replace(';Poly.',";Mark('POLY_STEP');Poly.")
script=head+'''Procedure FinishRF50;
Var B:IPCB_Board;K,J,NP,NC:Integer;I,It,It2:IPCB_BoardIterator;V:IPCB_Via;Pad:IPCB_Pad;Comp:IPCB_Component;Track:IPCB_Track;Rule:IPCB_Rule;
 Poly:IPCB_Polygon;GN,Net:IPCB_Net;Seg:TPolySegment;FabText:IPCB_Text;Polys:Array[0..7] Of IPCB_Polygon;Dead:Array[0..23] Of IPCB_Via;NPoly:Integer;
Begin
 Root:='C:\\JeonghyunPark\\Workspace\\QSTL_24DC_4MW_PCB\\';B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase(Root+'QSTL_24DC_4MW_PCB\\QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 Log:=TStringList.Create;Mark('CONTINUE_START');GN:=Nil;
 It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eNetObject));Net:=It.FirstPCBObject;
 While Net<>Nil Do Begin If Net.Name='GND' Then GN:=Net;Net:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);
 NC:=0;It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=It.FirstPCBObject;
 While Pad<>Nil Do Begin Comp:=Pad.Component;If Comp<>Nil Then If Copy(Comp.Name.Text,1,1)='C' Then Begin
  It2:=B.BoardIterator_Create;It2.SetState_FilterAll;It2.AddFilter_ObjectSet(MkSet(eViaObject));V:=It2.FirstPCBObject;
  While V<>Nil Do Begin If (Abs(V.X-Pad.X)<2) And (Abs(V.Y-Pad.Y)<2) Then Begin Dead[NC]:=V;Inc(NC);End;V:=It2.NextPCBObject;End;B.BoardIterator_Destroy(It2);
 End;Pad:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);Mark('CAP_VIAS='+IntToStr(NC));
 PCBServer.PreProcess;
 Try
  For K:=0 To NC-1 Do B.RemovePCBObject(Dead[K]);Mark('CAP_VIAS_REMOVED');
'''+dcfix+tail
script=script.replace("Mark('POLY_STEP');Poly.","Mark('POLY_STEP');Poly.")
# Number progress checkpoints without relying on the error dialog text.
for i in range(script.count("'POLY_STEP'")):script=script.replace("'POLY_STEP'",f"'POLY_STEP_{i+1}'",1)
(H/'FinishRF50.pas').write_text(script,encoding='ascii')
print('Prepared continuation')
