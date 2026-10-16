"""Retarget existing, enabled rules to the accepted L2/L3 and terminal banks."""
from pathlib import Path
import json,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[1];sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from prepare_native_revision_rules import read_rules,quote,net_scope,bounds
p=json.loads((H/'candidate.json').read_text());rules=read_rules(H/'backup/QSTL_QD4_2SET_38PAD.PcbDoc')
(H/'before_rules.json').write_text(json.dumps(rules,indent=2))
dc=sorted(n for n in p['nets'] if n.startswith('DC'))
groups={'zif':[v for v in p['vias'] if v['label'].startswith('J1-')],'qd':[v for v in p['vias'] if v['label'].startswith('Q1-')]}
scope={}
for key,vs in groups.items():scope[key]='IsVia And '+net_scope(sorted({v['net'] for v in vs}))+' And InRegionAbsolute('+','.join(f'{x/.0254:.9f}' for x in bounds(vs))+')'
general='Not (IsVia And InNet(\'GND\')) And Not ('+scope['zif']+') And Not ('+scope['qd']+')'
target=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
code=[f"Procedure Update16RFRules;\nVar B:IPCB_Board;I:IPCB_BoardIterator;R:IPCB_Rule;V:IPCB_RoutingViaStyleRule;W:IPCB_MaxMinWidthConstraint;RR:IPCB_RoutingLayersRule;L:TStringList;\nBegin B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase({quote(target)}) Then Exit;L:=TStringList.Create;PCBServer.PreProcess;Try;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;While R<>Nil Do Begin"]
for name,r in rules.items():
    s1=r.get('SCOPE1EXPRESSION','All').replace('L4_DC_B','L3_DC_B').replace('L3_GND','L4_GND');s2=r.get('SCOPE2EXPRESSION','All').replace('L4_DC_B','L3_DC_B').replace('L3_GND','L4_GND')
    if name=='RoutingVias':s1=general
    if name=='QD38_ZIF_VIA_0P4_0P2':s1=scope['zif']
    if name=='QD38_QD_VIA_0P4_0P2':s1=scope['qd']
    code += [f"If R.Name={quote(name)} Then Begin R.Scope1Expression:={quote(s1)};R.Scope2Expression:={quote(s2)};End;"]
code += ["If R.Name='QD38_DC_WIDTH' Then Begin W:=R;W.MinWidth[eMidLayer2]:=MMsToCoord(0.125);W.MaxWidth[eMidLayer2]:=MMsToCoord(0.125);W.FavoredWidth[eMidLayer2]:=MMsToCoord(0.125);End;",
         "If R.RuleKind=eRule_RoutingLayers Then Begin RR:=R;RR.SetState_RoutingLayers(eMidLayer2,True);RR.SetState_RoutingLayers(eMidLayer3,False);R.Comment:='RF on Bottom; DC on L2/L3 with short Top ZIF pad escapes. L1/L4/L5 GND.';End;",
         "If R.Name='QD38_QD_VIA_0P4_0P2' Then Begin V:=R;V.MinWidth:=MMsToCoord(0.35);V.MaxWidth:=MMsToCoord(0.35);V.PreferedWidth:=MMsToCoord(0.35);End;",
         "L.Add(R.Name+'|'+R.Scope1Expression+'|'+R.Scope2Expression);R:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);Finally PCBServer.PostProcess;End;B.InvalidateScopeTester;B.ValidateScopeTester;B.RebuildPadCaches;B.SetState_DocumentHasChanged;L.Add('COMPLETE');",
         f"L.SaveToFile({quote(H/'rules_native.txt')});L.Free;End;"]
(H/'Update16RFRules.pas').write_text('\n'.join(code),encoding='ascii')
(H/'Update16RFRules.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=Update16RFRules.pas\n[Generic_ScriptingSystem]\nStartProcName=Update16RFRules.pas>Update16RFRules\n')
print(json.dumps({n:{k:v for k,v in r.items() if k in ('RULEKIND','GAP','MINIMUM','HOLEWIDTH','MINWIDTH','MAXWIDTH','MINHOLEWIDTH','MAXHOLEWIDTH','DRCENABLED','SCOPE1EXPRESSION')} for n,r in rules.items()},indent=2))
