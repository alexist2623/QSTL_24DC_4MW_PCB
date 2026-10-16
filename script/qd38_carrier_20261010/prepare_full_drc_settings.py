"""Prepare, but never dispatch, native QD38 batch-DRC coverage settings.

The public Altium options API documents RuleSetToCheck and MaxViolationCount:
https://www.altium.com/documentation/altium-dxp-developer/pcb-api-system-interfaces-reference
Installed AD26 metadata additionally exposes the board accessor
Boardobj_intf.IBoardImplementation.GetState_DesignRuleCheckerOptions.
The native accessor still requires a runtime check by the main operator.

This changes only batch coverage and the reporting ceiling, not PCB rules,
their scopes, online checking, geometry, or manufacturing limits.  The limit
is deliberately a positive integer; zero has no documented unlimited meaning.
"""
from pathlib import Path
import json
import struct

import olefile


H = Path(__file__).resolve().parent
ROOT = H.parents[1]
PCB = ROOT / "QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc"
LIMIT = 1_000_000
STEM = "FullDRCSettingsR1"


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def assert_single_line_pascal_strings(code):
    in_string = False
    i = 0
    while i < len(code):
        c = code[i]
        if c == "'":
            if in_string and i + 1 < len(code) and code[i + 1] == "'":
                i += 2
                continue
            in_string = not in_string
        if c in "\r\n" and in_string:
            raise AssertionError("Pascal string literal spans a newline")
        i += 1
    assert not in_string, "Unterminated Pascal string literal"


def saved_options():
    with olefile.OleFileIO(PCB) as doc:
        data = doc.openstream("Design Rule Checker Options6/Data").read()
    length, = struct.unpack_from("<I", data)
    assert length == len(data) - 4
    return dict(item.split("=", 1) for item in
                data[4:].rstrip(b"\0").decode("cp1252").split("|") if "=" in item)


def main():
    before = saved_options()
    enabled = set(map(int, before["RULESETTOCHECK"].split(",")))
    assert before["RECORD"] == "DesignRuleCheckerOptions"
    plan = {
        "status": "PREPARED_NOT_EXECUTED",
        "pcb": str(PCB),
        "saved_options_before_generation": before,
        "batch_rule_kind_additions": {"11": "RoutingVias", "24": "ComponentClearance"},
        "expected_batch_rule_kinds": sorted(enabled | {11, 24}),
        "requested_max_violation_count": LIMIT,
        "preserve": ["all prior batch categories", "all online categories", "all rule definitions"],
        "completion_requirement": "Run batch DRC and reject a report that says checking stopped early.",
        "native_accessor_evidence": "Installed AD26 Boardobj_intf.IBoardImplementation.GetState_DesignRuleCheckerOptions",
        "native_runtime_verified": False,
        "sources": [
            "https://www.altium.com/documentation/altium-dxp-developer/pcb-api-system-interfaces-reference",
            "https://www.altium.com/documentation/altium-dxp-developer/pcb-api-types-reference",
            "https://www.altium.com/documentation/altium-designer/scripting/delphiscript/functions",
            "https://www.altium.com/documentation/knowledge-base/altium-designer/batch-drc-reports-no-shorts-when-the-violation-limit-is-reached",
        ],
    }
    code = r"""
Procedure FullDRCSettingsR1;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;
    C:IPCB_Component;R:IPCB_Rule;O:IPCB_DesignRuleCheckerOptions;
    BeforeBatch,BeforeOnline:TRuleSet;
    OldLimit,ComponentCount,ViaRules,ComponentRules,K:Integer;
    Log:TStringList;Failed:Boolean;
Begin
 Log:=TStringList.Create;
 Log.Add('START');Log.SaveToFile(__LOG__);
 D:=Client.OpenDocument('PCB',__PCB__);
 If D=Nil Then Begin Log.Add('STOP_NO_DOCUMENT');Log.SaveToFile(__LOG__);Log.Free;Exit;End;
 Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Begin Log.Add('STOP_NO_BOARD');Log.SaveToFile(__LOG__);Log.Free;Exit;End;
 If LowerCase(B.FileName)<>LowerCase(__PCB__) Then Begin
  Log.Add('STOP_WRONG_BOARD');Log.SaveToFile(__LOG__);Log.Free;Exit;
 End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));
 C:=I.FirstPCBObject;ComponentCount:=0;
 While C<>Nil Do Begin Inc(ComponentCount);C:=I.NextPCBObject;End;
 B.BoardIterator_Destroy(I);
 If ComponentCount<>50 Then Begin Log.Add('STOP_COMPONENT_COUNT');Log.SaveToFile(__LOG__);Log.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));
 R:=I.FirstPCBObject;ViaRules:=0;ComponentRules:=0;
 While R<>Nil Do Begin
  If R.DRCEnabled Then Begin
   If R.RuleKind=eRule_RoutingViaStyle Then Inc(ViaRules);
   If R.RuleKind=eRule_ComponentClearance Then Inc(ComponentRules);
  End;
  R:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 Log.Add('ACTIVE_VIA_RULES='+IntToStr(ViaRules));
 Log.Add('ACTIVE_COMPONENT_RULES='+IntToStr(ComponentRules));
 If (ViaRules<>3) Or (ComponentRules<>1) Then Begin
  Log.Add('STOP_RULE_PREFLIGHT');Log.SaveToFile(__LOG__);Log.Free;Exit;
 End;
 Log.Add('GET_OPTIONS');Log.SaveToFile(__LOG__);
 O:=B.GetState_DesignRuleCheckerOptions;
 If O=Nil Then Begin Log.Add('STOP_NO_OPTIONS');Log.SaveToFile(__LOG__);Log.Free;Exit;End;
 BeforeBatch:=O.RuleSetToCheck;BeforeOnline:=O.OnLineRuleSetToCheck;
 OldLimit:=O.MaxViolationCount;
 Log.Add('MAX_BEFORE='+IntToStr(OldLimit));
 For K:=0 To 255 Do Begin
  If InSet(K,BeforeBatch) Then Log.Add('BATCH_BEFORE='+IntToStr(K));
  If InSet(K,BeforeOnline) Then Log.Add('ONLINE_BEFORE='+IntToStr(K));
 End;
 Log.Add('APPLY_OPTIONS');Log.SaveToFile(__LOG__);
 O.RuleSetToCheck:=SetUnion(BeforeBatch,MkSet(eRule_RoutingViaStyle,eRule_ComponentClearance));
 If OldLimit<__LIMIT__ Then O.MaxViolationCount:=__LIMIT__;
 Failed:=False;
 If Not InSet(eRule_RoutingViaStyle,O.RuleSetToCheck) Then Failed:=True;
 If Not InSet(eRule_ComponentClearance,O.RuleSetToCheck) Then Failed:=True;
 If O.MaxViolationCount<__LIMIT__ Then Failed:=True;
 If O.OnLineRuleSetToCheck<>BeforeOnline Then Failed:=True;
 For K:=0 To 255 Do Begin
  If InSet(K,BeforeBatch) And Not InSet(K,O.RuleSetToCheck) Then Failed:=True;
 End;
 If Failed Then Begin
  O.RuleSetToCheck:=BeforeBatch;O.OnLineRuleSetToCheck:=BeforeOnline;O.MaxViolationCount:=OldLimit;
  Log.Add('STOP_VERIFICATION_ROLLED_BACK');Log.SaveToFile(__LOG__);Log.Free;Exit;
 End;
 Log.Add('MAX_AFTER='+IntToStr(O.MaxViolationCount));
 For K:=0 To 255 Do Begin
  If InSet(K,O.RuleSetToCheck) Then Log.Add('BATCH_AFTER='+IntToStr(K));
  If InSet(K,O.OnLineRuleSetToCheck) Then Log.Add('ONLINE_AFTER='+IntToStr(K));
 End;
 B.SetState_DocumentHasChanged;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');
 RunProcess('WorkspaceManager:SaveObject');
 Log.Add('COMPLETE_SETTINGS_ONLY_DRC_STILL_REQUIRED');Log.SaveToFile(__LOG__);Log.Free;
End;
"""
    for token, value in {
        "__PCB__": quote(PCB),
        "__LOG__": quote(H / "native_full_drc_settings_r1.txt"),
        "__LIMIT__": str(LIMIT),
    }.items():
        code = code.replace(token, value)
    assert "__" not in code
    assert_single_line_pascal_strings(code)
    assert " In " not in code and "BeforeBatch+" not in code
    (H / f"{STEM}.pas").write_text(code, encoding="ascii")
    (H / f"{STEM}.PrjScr").write_text(
        f"[Design]\nVersion=1.0\n[Document1]\nDocumentPath={STEM}.pas\n"
        f"[Generic_ScriptingSystem]\nStartProcName={STEM}.pas>{STEM}\n",
        encoding="ascii")
    (H / "full_drc_settings_plan.json").write_text(json.dumps(plan, indent=2))
    print(f"Prepared {STEM}.pas; not dispatched. Native accessor runtime check remains.")
    print("Current batch categories:", sorted(enabled))
    print("Requested batch categories:", sorted(enabled | {11, 24}))
    print("Positive violation ceiling:", max(int(before["MAXVIOLATIONCOUNT"]), LIMIT))


if __name__ == "__main__":
    main()
