"""Prepare the explicit QD through-via rule addition; never invoke Altium.

The candidate must pass a hash-matched independent copper audit. Rule scopes
identify the QD and ZIF endpoint banks by their known DC nets and spatial
regions, never by observed via diameter. Existing widths, clearances, drill
clearances, mask-sliver limits, rule enable states and stack are preserved.
A dedicated authorized 0.10 mm DC-pair clearance applies to objects existing
on L2/L4; it does not change the general 0.15 or DC-to-GND 0.20 mm limits.

InRegionAbsolute coordinates are in absolute mils, independent of display units.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import olefile

from revision_invariants import assert_plan_contacts, via_groups

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TARGET = ROOT / "QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc"
BASELINE = HERE / "before_rotation/QSTL_QD4_2SET_38PAD.PcbDoc"
FROZEN = "f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632"
QD_RULE = "QD38_QD_VIA_0P4_0P2"
ZIF_RULE = "QD38_ZIF_VIA_0P4_0P2"
DC_RULE = "QD38_DC_PAIR_GAP_0P1"
LAYER_SCOPE_SOURCE = "https://www.altium.com/documentation/knowledge-base/altium-designer/layer-specific-design-rules-with-through-hole-pads-and-vias"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quote(value):
    text = str(value)
    assert "\n" not in text and "\r" not in text
    return "'" + text.replace("'", "''") + "'"


def read_rules(path):
    with olefile.OleFileIO(path) as source:
        data = source.openstream("Rules6/Data").read()
    rows = []
    pos = 0
    while pos < len(data):
        kind, length = struct.unpack_from("<HI", data, pos)
        pos += 6
        record = data[pos:pos+length]
        pos += length
        row = dict(item.split("=",1) for item in record.rstrip(b"\0").decode("cp1252").split("|") if "=" in item)
        rows.append(row)
    assert pos == len(data)
    assert len({r["NAME"] for r in rows}) == len(rows)
    return {r["NAME"]:r for r in rows}


def net_scope(names):
    return "(" + " Or ".join("InNet(" + quote(name) + ")" for name in sorted(names)) + ")"


def bounds(vias):
    # Fixed design allowance about endpoint centres; independent of actual land
    # or drill sizes so a malformed via cannot select itself out of its rule.
    return [min(v["x"] for v in vias)-.25, min(v["y"] for v in vias)-.25,
            max(v["x"] for v in vias)+.25, max(v["y"] for v in vias)+.25]


def inside(via, rect):
    return rect[0] <= via["x"] <= rect[2] and rect[1] <= via["y"] <= rect[3]


def rule_plan(plan):
    groups = via_groups(plan)
    dc = sorted(n for n in plan["nets"] if n.startswith("DC"))
    direct = sorted(v["net"] for v in groups["direct_qd"])
    zif_box, qd_box = bounds(groups["zif"]), bounds(groups["direct_qd"])
    region = lambda r: "InRegionAbsolute(" + ",".join(f"{n/.0254:.9f}" for n in r) + ")"
    zif_scope = "IsVia And " + net_scope(dc) + " And " + region(zif_box)
    qd_scope = "IsVia And " + net_scope(direct) + " And " + region(qd_box)
    # Assert that the explicit net/region predicates partition all candidate
    # signal vias. No geometry-based selector is used in the scopes.
    for key in ("zif", "direct_qd", "resistor"):
        for via in groups[key]:
            a = via["net"] in dc and inside(via,zif_box)
            b = via["net"] in direct and inside(via,qd_box)
            assert (a,b) == (key=="zif",key=="direct_qd"), (key,via["label"])
    general = "Not (IsVia And InNet('GND')) And Not (" + zif_scope + ") And Not (" + qd_scope + ")"
    # OnLayer would exclude through-vias and pads. ExistsOnLayer includes the
    # actual copper shapes on these internal layers, as documented by Altium.
    # Through-via pairs are eligible as whole objects; the independent saved
    # copper verifier therefore also preserves .15 on every other layer.
    dc_pair_scope = net_scope(dc) + " And (ExistsOnLayer('L2_DC_A') Or ExistsOnLayer('L4_DC_B'))"
    dc_ground_scope = "InNet('GND') And (ExistsOnLayer('L2_DC_A') Or ExistsOnLayer('L4_DC_B'))"
    return dict(zif_scope=zif_scope, direct_qd_scope=qd_scope, general_scope=general,
                dc_pair_scope=dc_pair_scope, dc_ground_scope=dc_ground_scope, dc_ground_second_scope=dc_pair_scope, dc_pair_gap_mm=.10, layer_scope_source=LAYER_SCOPE_SOURCE,
                zif_box_mm=zif_box, direct_qd_box_mm=qd_box, dc_nets=dc, direct_qd_nets=direct,
                group_counts={key:len(value) for key,value in groups.items()},
                expected_native_DRC_rule_instances=23, expected_via_rules=4)


HEADER = r"""Var RB:IPCB_Board;RL:TStringList;
Function FindRevisionRule(Name:String):IPCB_Rule;
Var I:IPCB_BoardIterator;R:IPCB_Rule;
Begin Result:=Nil;I:=RB.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
 While R<>Nil Do Begin If R.Name=Name Then Begin Result:=R;Break;End;R:=I.NextPCBObject;End;RB.BoardIterator_Destroy(I);End;
Procedure RegisterRevisionRule(R:IPCB_Rule);
Begin RB.AddPCBObject(R);PCBServer.SendMessageToRobots(RB.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,R.I_ObjectAddress);End;
Procedure Note(S:String);Begin RL.Add(S);RL.SaveToFile(__LOG__);End;
Function ViaDimensions(V:IPCB_Via;D,H:Double):Boolean;
Begin Result:=(Abs(CoordToMMs(V.Size)-D)<0.00001) And (Abs(CoordToMMs(V.HoleSize)-H)<0.00001);End;
Procedure RulesQD90Revision;
Var I:IPCB_BoardIterator;C:IPCB_Component;V:IPCB_Via;R:IPCB_Rule;VR,VD:IPCB_RoutingViaStyleRule;CL:IPCB_ClearanceConstraint;
 NC,NZ,NQ,NR,NS:Integer;IsZ,IsQ,IsDC,Good:Boolean;
Begin
 RB:=PCBServer.GetCurrentPCBBoard;If RB=Nil Then Exit;
 If LowerCase(RB.FileName)<>LowerCase(__TARGET__) Then Exit;
 RL:=TStringList.Create;Note('BOARD|'+RB.FileName);Good:=True;
 NC:=0;I:=RB.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);C:=I.NextPCBObject;End;RB.BoardIterator_Destroy(I);
 If NC<>50 Then Begin Note('STOP_COMPONENT_COUNT');RL.Free;Exit;End;
 NZ:=0;NQ:=0;NR:=0;NS:=0;I:=RB.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin
  If V.Net=Nil Then Begin Good:=False;Note('STOP_UNNETTED_VIA');Break;End;
  If V.Net.Name='GND' Then Begin
   If (V.LowLayer<>eMidLayer4) Or (V.HighLayer<>eBottomLayer) Or (Not ViaDimensions(V,0.25,0.1)) Then Begin Good:=False;Note('STOP_SHIELD_GEOMETRY');Break;End;Inc(NS);
  End Else Begin
   If (V.LowLayer<>eTopLayer) Or (V.HighLayer<>eBottomLayer) Then Begin Good:=False;Note('STOP_SIGNAL_SPAN');Break;End;
   IsDC:=__DC_NET_TEST__;
   If Not IsDC Then Begin Good:=False;Note('STOP_NON_DC_SIGNAL_VIA');Break;End;
   IsZ:=(V.X>=MMsToCoord(__ZX0__)) And (V.X<=MMsToCoord(__ZX1__)) And (V.Y>=MMsToCoord(__ZY0__)) And (V.Y<=MMsToCoord(__ZY1__));
   IsQ:=(__QD_NET_TEST__) And (V.X>=MMsToCoord(__QX0__)) And (V.X<=MMsToCoord(__QX1__)) And (V.Y>=MMsToCoord(__QY0__)) And (V.Y<=MMsToCoord(__QY1__));
   If IsZ And IsQ Then Begin Good:=False;Note('STOP_OVERLAPPING_VIA_SCOPES');Break;End;
   If IsZ Then Begin Inc(NZ);Good:=ViaDimensions(V,0.4,0.2);End
   Else If IsQ Then Begin Inc(NQ);Good:=ViaDimensions(V,0.4,0.2);End
   Else Begin Inc(NR);Good:=ViaDimensions(V,0.5,0.25);End;
   If Not Good Then Begin Note('STOP_SIGNAL_VIA_GEOMETRY');Break;End;
  End;V:=I.NextPCBObject;
 End;RB.BoardIterator_Destroy(I);
 If (Not Good) Or (NZ<>38) Or (NQ<>22) Or (NR<>16) Or (NS<>__NSHIELD__) Then Begin Note('STOP_VIA_GROUP_COUNTS');RL.Free;Exit;End;
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,required=True)
    parser.add_argument("--audit",type=Path,required=True)
    args = parser.parse_args()
    candidate, audit_path = args.candidate.resolve(), args.audit.resolve()
    plan = json.loads(candidate.read_text())
    audit = json.loads(audit_path.read_text())
    assert audit.get("passed") is True and audit.get("candidate_sha256")==sha(candidate)
    assert plan.get("routing_complete") is True
    pool = assert_plan_contacts(plan)
    assert sha(BASELINE)==FROZEN and sha(TARGET)==FROZEN, "Regenerate/review the rule plan if the saved PCB changed"
    rules = read_rules(BASELINE)
    assert QD_RULE not in rules and DC_RULE not in rules
    assert len([r for r in rules.values() if r["RULEKIND"]=="RoutingVias"])==3
    assert rules["RoutingVias"]["VIASTYLE"]=="Through Hole"
    assert rules[ZIF_RULE]["VIASTYLE"]=="Through Hole"
    assert rules["RF_SHIELD_L5_L6"]["VIASTYLE"]=="Blind Buried (Adjacent Layers)"
    report = rule_plan(plan)
    code = [HEADER]
    for name in ("RoutingVias",ZIF_RULE,"RF_SHIELD_L5_L6","QD38_DC_WIDTH","Clearance","DC_GND_GAP_0P2"):
        code.append(f"If FindRevisionRule({quote(name)})=Nil Then Begin Note({quote('STOP_MISSING_RULE|'+name)});RL.Free;Exit;End;")
    code.extend([
        f"If FindRevisionRule({quote(QD_RULE)})<>Nil Then Begin Note('STOP_QD_RULE_ALREADY_EXISTS');RL.Free;Exit;End;",
        f"If FindRevisionRule({quote(DC_RULE)})<>Nil Then Begin Note('STOP_DC_PAIR_RULE_ALREADY_EXISTS');RL.Free;Exit;End;",
        "PCBServer.PreProcess;Try",
        "R:=FindRevisionRule('RoutingVias');VD:=R;R.Scope1Expression:="+quote(report["general_scope"])+";",
        "R:=FindRevisionRule("+quote(ZIF_RULE)+");R.Scope1Expression:="+quote(report["zif_scope"])+";",
        "R:=FindRevisionRule('DC_GND_GAP_0P2');R.Scope1Expression:="+quote(report["dc_ground_scope"])+";R.Scope2Expression:="+quote(report["dc_ground_second_scope"])+";",
        "R:=PCBServer.PCBRuleFactory(eRule_RoutingViaStyle);R.Name:="+quote(QD_RULE)+";RegisterRevisionRule(R);R.Scope1Expression:="+quote(report["direct_qd_scope"])+";R.Scope2Expression:='All';R.DRCEnabled:=True;VR:=R;VR.ViaStyle:=VD.ViaStyle;",
        "VR.MinWidth:=MMsToCoord(0.4);VR.MaxWidth:=MMsToCoord(0.4);VR.PreferedWidth:=MMsToCoord(0.4);VR.MinHoleWidth:=MMsToCoord(0.2);VR.MaxHoleWidth:=MMsToCoord(0.2);VR.PreferedHoleWidth:=MMsToCoord(0.2);",
        "R:=PCBServer.PCBRuleFactory(eRule_Clearance);R.Name:="+quote(DC_RULE)+";R.Scope1Expression:="+quote(report["dc_pair_scope"])+";R.Scope2Expression:="+quote(report["dc_pair_scope"])+";R.NetScope:=eNetScope_DifferentNetsOnly;R.DRCEnabled:=True;CL:=R;CL.Gap:=MMsToCoord(0.10);RegisterRevisionRule(R);",
        "Finally PCBServer.PostProcess;End;",
        "RB.InvalidateScopeTester;RB.ValidateScopeTester;",
        "R:=FindRevisionRule("+quote(DC_RULE)+");CL:=FindRevisionRule('Clearance');If R.Priority>=CL.Priority Then Begin Note('STOP_DC_RULE_PRIORITY_REQUIRES_NATIVE_FIX');RL.Free;Exit;End;",
        "I:=RB.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;While R<>Nil Do Begin Note('RULE|'+R.Name+'|'+R.Scope1Expression+'|'+R.Scope2Expression);R:=I.NextPCBObject;End;RB.BoardIterator_Destroy(I);",
        "RB.RebuildPadCaches;RB.SetState_DocumentHasChanged;RB.ViewManager_FullUpdate;RB.GraphicallyInvalidate;Note('COMPLETE_NOT_SAVED');RL.Free;End;"])
    text="\n".join(code).replace("__TARGET__",quote(TARGET)).replace("__LOG__",quote(HERE/"native_revision_rules_log.txt"))
    for prefix,key in (("Z","zif_box_mm"),("Q","direct_qd_box_mm")):
        for suffix,value in zip(("X0","Y0","X1","Y1"),report[key]):
            text=text.replace("__"+prefix+suffix+"__",f"{value:.9f}")
    test=lambda nets: " Or ".join("(V.Net.Name="+quote(n)+")" for n in nets)
    text=text.replace("__DC_NET_TEST__",test(report["dc_nets"]))
    text=text.replace("__QD_NET_TEST__",test(report["direct_qd_nets"]))
    text=text.replace("__NSHIELD__",str(len(plan["shield_vias"])))
    assert "__" not in text
    for line in text.splitlines():
        assert len(line.replace("''", "").split("'"))%2==1, "Unbalanced single-line Pascal literal"
    stem="RulesQD90Revision"
    (HERE/(stem+".pas")).write_text(text,encoding="ascii")
    (HERE/(stem+".PrjScr")).write_text(f"[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n")
    report.update(status="PREPARED_NOT_EXECUTED",candidate_file=str(candidate),candidate_sha256=sha(candidate),
                  audit_file=str(audit_path),audit_sha256=sha(audit_path),baseline_sha256=sha(BASELINE),
                  baseline_rules=rules,modified_rules=["RoutingVias",ZIF_RULE,"DC_GND_GAP_0P2"],added_rules=[QD_RULE,DC_RULE],
                  unchanged_rules=[n for n in rules if n not in ("RoutingVias",ZIF_RULE,"DC_GND_GAP_0P2")],ZIF_contact_pool=pool,
                  modified_rule_fields={"RoutingVias":["SCOPE1EXPRESSION"],ZIF_RULE:["SCOPE1EXPRESSION"],"DC_GND_GAP_0P2":["SCOPE1EXPRESSION","SCOPE2EXPRESSION"]},
                  note="Two existing via scopes change; DC_GND_GAP_0P2 now includes multilayer GND copper in Scope1 and explicitly limits Scope2 to DC nets existing on L2/L4, preserving its .20 mm gap without selecting RF nets. One via rule and one dedicated DC-pair clearance rule are added. All inherited limits and enable states remain. Native priority must place each specific clearance above general clearance. Genuine DRC violations must be retained.",
                  layer_scope_caveat="ExistsOnLayer includes whole through objects. Independent saved copper checks require >=.15 mm DC-pair clearance on non-DC layers and >=.20 mm DC-to-GND on L2/L4. The corrected GND rule is restricted to GND/DC pairs, excluding RF nets; any newly exposed native DRC result must be examined, not suppressed.")
    (HERE/"native_revision_rules_plan.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ("baseline_rules","dc_nets","direct_qd_nets")},indent=2))


if __name__=="__main__":
    main()
