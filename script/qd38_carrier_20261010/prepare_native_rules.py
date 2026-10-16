"""Prepare copied-carrier rule updates without invoking Altium or saving a PCB.

InRegionAbsolute numeric coordinates are absolute mils, independently of the
display units, per the official Altium PCB query membership documentation:
https://www.altium.com/documentation/altium-designer/pcb/query-functions/membership-checks
"""
from pathlib import Path
import hashlib
import json
import struct
import olefile

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
TARGET = DEST / 'QSTL_QD4_2SET_38PAD.PcbDoc'


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def assert_single_line_pascal_strings(text):
    """Reject broken Pascal literals before any generated file is written."""
    in_string = False
    i = 0
    line = 1
    while i < len(text):
        char = text[i]
        if char == '\n':
            assert not in_string, f'Pascal string literal spans newline at line {line}'
            line += 1
        if char == "'":
            if in_string and i + 1 < len(text) and text[i + 1] == "'":
                i += 2
                continue
            in_string = not in_string
        i += 1
    assert not in_string, 'Unclosed Pascal string literal'


def source_rules():
    source = ROOT / 'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc'
    with olefile.OleFileIO(source) as doc:
        data = doc.openstream('Rules6/Data').read()
    rows = []
    pos = 0
    while pos < len(data):
        kind, count = struct.unpack_from('<HI', data, pos)
        pos += 6
        body = data[pos:pos + count]
        pos += count
        rows.append(dict(item.split('=', 1) for item in body.rstrip(b'\0').decode('cp1252').split('|') if '=' in item))
    assert pos == len(data)
    return {row['NAME']: row for row in rows}


def main():
    candidate = DEST / 'full_copper_candidate.json'
    plan = json.loads(candidate.read_text())
    rules = source_rules()
    required = ['RF_50OHM_WIDTH', 'Width', 'RoutingVias', 'RF_SHIELD_L5_L6',
                'Clearance', 'RF_CPW_GND_GAP_0P2', 'DC_GND_GAP_0P2']
    assert all(name in rules for name in required)
    assert rules['RoutingVias']['VIASTYLE'] == 'Through Hole'
    assert all((v['low'], v['high']) == (1, 32) for v in plan['vias'])
    dc_nets = sorted(n for n in plan['nets'] if n.startswith('DC'))
    rf_nets = sorted(n for n in plan['nets'] if n.startswith(('S', 'MW')))
    assert len(dc_nets) == 38 and len(rf_nets) == 32
    for track in plan['tracks']:
        expected = .11 if track['net'] in rf_nets else .15 if track['layer'] == 1 else .125
        assert abs(track['width'] - expected) < 1e-9
    small = [v for v in plan['vias'] if v['label'].startswith('J1-')]
    regular = [v for v in plan['vias'] if not v['label'].startswith('J1-')]
    assert len(small) == len(regular) == 38
    assert all(abs(v['diameter'] - .4) < 1e-9 and abs(v['hole'] - .2) < 1e-9 for v in small)
    assert all(abs(v['diameter'] - .5) < 1e-9 and abs(v['hole'] - .25) < 1e-9 for v in regular)
    # A spatial exception identifies the ZIF escape bank without selecting
    # vias by their diameter, which would hide wrongly resized small vias.
    box = [min(v['x'] - .2 for v in small) - .05,
           min(v['y'] - .2 for v in small) - .05,
           max(v['x'] + .2 for v in small) + .05,
           max(v['y'] + .2 for v in small) + .05]
    assert all(not (box[0] <= v['x'] <= box[2] and box[1] <= v['y'] <= box[3]) for v in regular)
    dc = '(' + ' Or '.join("InNet('" + n + "')" for n in dc_nets) + ')'
    rf = "OnLayer('L6_RF_QD') And (" + ' Or '.join("InNet('" + n + "')" for n in rf_nets) + ')'
    region = 'InRegionAbsolute(' + ','.join(f'{n / .0254:.9f}' for n in box) + ')'
    small_scope = 'IsVia And ' + dc + ' And ' + region
    general_scope = "Not (IsVia And InNet('GND')) And Not (" + small_scope + ')'
    code = [r'''Var RuleBoard:IPCB_Board;RuleLog:TStringList;
Function FindRule(Name:String):IPCB_Rule;
Var I:IPCB_BoardIterator;R:IPCB_Rule;
Begin
 Result:=Nil;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
 While R<>Nil Do Begin If R.Name=Name Then Begin Result:=R;Break;End;R:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);
End;
Procedure RegisterRule(R:IPCB_Rule);
Begin RuleBoard.AddPCBObject(R);PCBServer.SendMessageToRobots(RuleBoard.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,R.I_ObjectAddress);End;
Procedure Rules38;
Var R:IPCB_Rule;W:IPCB_MaxMinWidthConstraint;VR,VRDefault:IPCB_RoutingViaStyleRule;CL:IPCB_ClearanceConstraint;
 I:IPCB_BoardIterator;C:IPCB_Component;V:IPCB_Via;NC,NSmall,NRegular,NShield,J:Integer;
 RFScope,DCScope,SmallScope:String;IsSmall:Boolean;
Begin
 RuleBoard:=PCBServer.GetCurrentPCBBoard;If RuleBoard=Nil Then Exit;
 If LowerCase(RuleBoard.FileName)<>LowerCase('__TARGET__') Then Exit;
 RuleLog:=TStringList.Create;RuleLog.Add('BOARD|'+RuleBoard.FileName);
 NC:=0;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);C:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);
 If NC<>50 Then Begin RuleLog.Add('STOP_COMPONENT_COUNT');RuleLog.SaveToFile(__LOGPATH__);RuleLog.Free;Exit;End;
 NSmall:=0;NRegular:=0;NShield:=0;I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin
  If V.Net=Nil Then Begin RuleLog.Add('STOP_UNNETTED_VIA');Break;End;
  If V.Net.Name='GND' Then Begin
   If (V.LowLayer<>eMidLayer4) Or (V.HighLayer<>eBottomLayer) Then Begin RuleLog.Add('STOP_SHIELD_SPAN');Break;End;
   Inc(NShield);
  End Else Begin
   If (V.LowLayer<>eTopLayer) Or (V.HighLayer<>eBottomLayer) Then Begin RuleLog.Add('STOP_SIGNAL_SPAN');Break;End;
   IsSmall:=(V.X>=MMsToCoord(__X0__)) And (V.X<=MMsToCoord(__X1__)) And (V.Y>=MMsToCoord(__Y0__)) And (V.Y<=MMsToCoord(__Y1__));
   If IsSmall Then Inc(NSmall) Else Inc(NRegular);
  End;V:=I.NextPCBObject;
 End;RuleBoard.BoardIterator_Destroy(I);
 If (V<>Nil) Or (NSmall<>38) Or (NRegular<>38) Or (NShield<>__NSHIELD__) Then Begin RuleLog.Add('STOP_VIA_COUNTS');RuleLog.SaveToFile(__LOGPATH__);RuleLog.Free;Exit;End;
''']
    for name in required:
        code.append(f"If FindRule({quote(name)})=Nil Then Begin RuleLog.Add({quote('STOP_MISSING_RULE|'+name)});RuleLog.SaveToFile(__LOGPATH__);RuleLog.Free;Exit;End;")
    code.extend([f'RFScope:={quote(rf)};DCScope:={quote(dc)};SmallScope:={quote(small_scope)};',
                 'PCBServer.PreProcess;Try',
                 "R:=FindRule('RF_50OHM_WIDTH');R.Scope1Expression:=RFScope;W:=R;W.MinWidth[eBottomLayer]:=MMsToCoord(0.11);W.MaxWidth[eBottomLayer]:=MMsToCoord(0.11);W.FavoredWidth[eBottomLayer]:=MMsToCoord(0.11);R.DRCEnabled:=True;",
                 "R:=FindRule('QD38_DC_WIDTH');If R=Nil Then Begin R:=PCBServer.PCBRuleFactory(eRule_MaxMinWidth);R.Name:='QD38_DC_WIDTH';RegisterRule(R);End;R.Scope1Expression:=DCScope;R.Scope2Expression:='All';R.DRCEnabled:=True;W:=R;"])
    for layer, width in [('eTopLayer', .15), ('eMidLayer1', .125), ('eMidLayer3', .125), ('eBottomLayer', .125)]:
        code.append(f'W.MinWidth[{layer}]:=MMsToCoord({width});W.MaxWidth[{layer}]:=MMsToCoord({width});W.FavoredWidth[{layer}]:=MMsToCoord({width});')
    code.extend(["R:=FindRule('Width');R.Scope1Expression:='Not ('+RFScope+') And Not ('+DCScope+')';",
                 "R:=FindRule('RoutingVias');R.Scope1Expression:=" + quote(general_scope) + ';',
                 "R:=FindRule('QD38_ZIF_VIA_0P4_0P2');If R=Nil Then Begin R:=PCBServer.PCBRuleFactory(eRule_RoutingViaStyle);R.Name:='QD38_ZIF_VIA_0P4_0P2';RegisterRule(R);End;R.Scope1Expression:=SmallScope;R.Scope2Expression:='All';R.DRCEnabled:=True;VR:=R;VR.MinWidth:=MMsToCoord(0.4);VR.MaxWidth:=MMsToCoord(0.4);VR.PreferedWidth:=MMsToCoord(0.4);VR.MinHoleWidth:=MMsToCoord(0.2);VR.MaxHoleWidth:=MMsToCoord(0.2);VR.PreferedHoleWidth:=MMsToCoord(0.2);",
                 "R:=FindRule('RoutingVias');VRDefault:=R;VR.ViaStyle:=VRDefault.ViaStyle;",
                 "R:=FindRule('RF_SHIELD_L5_L6');VR:=R;VR.ViaStyle:=eViaBlindBuriedPair;VR.MinWidth:=MMsToCoord(0.25);VR.MaxWidth:=MMsToCoord(0.25);VR.PreferedWidth:=MMsToCoord(0.25);VR.MinHoleWidth:=MMsToCoord(0.1);VR.MaxHoleWidth:=MMsToCoord(0.1);VR.PreferedHoleWidth:=MMsToCoord(0.1);R.DRCEnabled:=True;",
                 "R:=FindRule('Clearance');CL:=R;CL.Gap:=MMsToCoord(0.15);",
                 "R:=FindRule('RF_CPW_GND_GAP_0P2');CL:=R;CL.Gap:=MMsToCoord(0.2);",
                 "R:=FindRule('DC_GND_GAP_0P2');CL:=R;CL.Gap:=MMsToCoord(0.2);",
                 'Finally PCBServer.PostProcess;End;',
                 "I:=RuleBoard.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;While R<>Nil Do Begin RuleLog.Add('RULE|'+R.Name+'|'+R.Scope1Expression+'|'+R.Scope2Expression);R:=I.NextPCBObject;End;RuleBoard.BoardIterator_Destroy(I);",
                 "RuleBoard.RebuildPadCaches;RuleBoard.SetState_DocumentHasChanged;RuleBoard.ViewManager_FullUpdate;RuleBoard.GraphicallyInvalidate;RuleLog.Add('COMPLETE_NOT_SAVED');RuleLog.SaveToFile(__LOGPATH__);RuleLog.Free;End;"])
    text = '\n'.join(code).replace('__TARGET__', str(TARGET))
    text = text.replace('__LOGPATH__', quote(H / 'native_rules_log.txt'))
    for key, value in zip(('__X0__', '__Y0__', '__X1__', '__Y1__'), box):
        text = text.replace(key, f'{value:.9f}')
    text = text.replace('__NSHIELD__', str(len(plan['shield_vias'])))
    assert_single_line_pascal_strings(text)
    (H/'Rules38.pas').write_text(text, encoding='ascii')
    (H/'Rules38.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=Rules38.pas\n[Generic_ScriptingSystem]\nStartProcName=Rules38.pas>Rules38\n')
    report = dict(status='PREPARED_NOT_EXECUTED', candidate_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                  dc_nets=dc_nets, rf_nets=rf_nets, small_via_scope=small_scope, small_via_box_mm=box,
                  source_general_signal_via=rules['RoutingVias'],
                  inherited_hole_to_hole_rule=rules['HoleToHoleClearance'],
                  inherited_mask_sliver_rule=rules['MinimumSolderMaskSliver'],
                  added_rules=['QD38_DC_WIDTH','QD38_ZIF_VIA_0P4_0P2'],
                  original_net_class_scopes_found=[],
                  unchanged_rules=[name for name in rules if name not in required],
                  notes=['No rule is disabled or relaxed to waive a geometric violation.',
                         'The new 0.4/0.2 ZIF-bank exception is spatial and independent of actual via diameter.',
                         'The inherited 0.5/0.25 general signal via definition remains unchanged.',
                         'Source hole-to-hole clearance remains 0.254 mm and must pass native DRC.',
                         'Source minimum solder-mask sliver remains 0.1 mm and must pass native DRC.',
                         'Via layer spans are checked in preflight; existing drill-pair rules are unchanged.'])
    (H/'native_rules_plan.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(status=report['status'],bytes=len(text),zif_region_mm=box,dc_nets=38,rf_nets=32),indent=2))


if __name__ == '__main__':
    main()
