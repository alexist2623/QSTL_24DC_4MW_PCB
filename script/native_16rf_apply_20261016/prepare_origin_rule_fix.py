"""Repair the measured J1 origin error and the L3 per-layer width rule."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent
ROOT=H.parents[1]
p=json.loads((H/'candidate.json').read_text())
snap=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
data=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/ZIF10mm_Reference_End_20261016/updated_mechanical_plan.json').read_text())
old=next(c for c in snap['components'] if c['designator']=='J1')
c=next(c for c in p['components'] if c['ref']=='J1')
wrong=data['ZIF']['new_origin_mm']
correct=[old['x'],old['y']+data['ZIF']['delta_y_mm']]
c['x'],c['y']=correct
(H/'candidate.json').write_text(json.dumps(p,indent=2))
q=lambda x:"'"+str(x).replace("'","''")+"'"
pcb=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
code=f"""Procedure Fix16RFOriginAndRules;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;C,J:IPCB_Component;
 R:IPCB_Rule;W:IPCB_MaxMinWidthConstraint;RR:IPCB_RoutingLayersRule;
 L:TStringList;NC,NR:Integer;
Begin
 L:=TStringList.Create;
 D:=Client.OpenDocument('PCB',{q(pcb)});If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase({q(pcb)}) Then Exit;
 NC:=0;J:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);If C.Name.Text='J1' Then J:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If (NC<>50) Or (J=Nil) Then Exit;
 L.Add('J1_BEFORE|'+FloatToStr(CoordToMMs(J.X))+'|'+FloatToStr(CoordToMMs(J.Y)));
 If Abs(CoordToMMs(J.Y)-({wrong[1]:.9f}))>0.00001 Then Begin L.Add('GUARD_FAILED');L.SaveToFile({q(H/'origin_rule_fix.txt')});L.Free;Exit;End;
 PCBServer.PreProcess;
 Try
  J.MoveToXY(MMsToCoord({correct[0]:.9f}),MMsToCoord({correct[1]:.9f}));
  NR:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
  While R<>Nil Do Begin
   If R.Name='QD38_DC_WIDTH' Then Begin W:=R;
    W.MinWidth[eMidLayer2]:=MMsToCoord(0.125);W.MaxWidth[eMidLayer2]:=MMsToCoord(0.125);W.FavoredWidth[eMidLayer2]:=MMsToCoord(0.125);Inc(NR);End;
   If R.RuleKind=eRule_RoutingLayers Then Begin RR:=R;
    RR.SetState_RoutingLayers(eMidLayer2,True);RR.SetState_RoutingLayers(eMidLayer3,False);
    R.Comment:='RF on Bottom; DC on L2/L3 with short Top ZIF pad escapes. L1/L4/L5 GND.';
    L.Add('ROUTING_LAYERS|'+R.Name);End;
   R:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
 Finally PCBServer.PostProcess;End;
 B.InvalidateScopeTester;B.ValidateScopeTester;B.RebuildPadCaches;B.SetState_DocumentHasChanged;
 B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 L.Add('WIDTH_RULES_UPDATED='+IntToStr(NR));L.Add('J1_AFTER|'+FloatToStr(CoordToMMs(J.X))+'|'+FloatToStr(CoordToMMs(J.Y)));
 L.Add('COMPLETE_NOT_SAVED');L.SaveToFile({q(H/'origin_rule_fix.txt')});L.Free;
End;
"""
(H/'Fix16RFOriginAndRules.pas').write_text(code,encoding='ascii')
(H/'Fix16RFOriginAndRules.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=Fix16RFOriginAndRules.pas\n[Generic_ScriptingSystem]\nStartProcName=Fix16RFOriginAndRules.pas>Fix16RFOriginAndRules\n')
a=json.loads((H/'saved_native_audit.json').read_text())
print(json.dumps({'wrong_origin':wrong,'correct_origin':correct,'other_errors':[e for e in a['errors'] if e['issue'] not in ('pad_geometry','disconnected_net')],'rules':json.loads((H/'before_rules.json').read_text()).get('RoutingLayers')},indent=2))
