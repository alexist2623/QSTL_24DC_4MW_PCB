"""Stage positive pad-aperture expansion repair; never execute or save Altium."""
from pathlib import Path
import hashlib
import html
import json
import re
from shapely.affinity import rotate, translate
from shapely.geometry import box, Point

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
PCB = ROOT / 'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
OLD_PLAN = H / 'pre_mask_repair/full_copper_candidate.json'
OLD_NATIVE = H / 'pre_mask_repair/QSTL_QD4_2SET_38PAD.PcbDoc'
SOURCE_SHA = 'a8e96043d9dcabcbf3b855f37ff28962a55389783f7ca484c95fda7b37b253fe'
NATIVE_SHA = 'c179d313dc7d7c1c5851517d779616fbe7c9c3b1e9a5f4ac565e0541c3e0a047'
OUTPUT = H / 'full_copper_mask_repair_candidate.json'
UNIT = 2.54e-6

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path, value): path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')
def q(s): return "'"+str(s).replace("'", "''")+"'"
def geometry(p):
    if p['shape'] == 'rect':
        return translate(rotate(box(-p['sx']/2, -p['sy']/2, p['sx']/2, p['sy']/2), p['rotation'], origin=(0,0)), p['x'], p['y'])
    assert abs(p['sx']-p['sy']) < 1e-6
    return Point(p['x'], p['y']).buffer(p['sx']/2, quad_segs=128)

CACHE_DUMP = r'''
Procedure DumpPads(S:String;Path:String);
Var I:IPCB_BoardIterator;P:IPCB_Pad;C:TPadCache;RefName,Enabled:String;L:TStringList;Count:Integer;
Begin
 L:=TStringList.Create;L.Add('STAGE='+S);L.Add('BOARD='+B.FileName);L.Add('CANDIDATE_SHA256=__CANDIDATE__');Count:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin
  Inc(Count);RefName:='MOUNT';If P.Component<>Nil Then RefName:=P.Component.Name.Text;
  C:=P.GetState_Cache;Enabled:='0';If P.GetState_PasteMaskEnabled Then Enabled:='1';
  L.Add('PAD='+RefName+'|'+P.Name+'|'+IntToStr(P.X)+'|'+IntToStr(P.Y)+'|'+IntToStr(C.SolderMaskExpansion)+'|'+IntToStr(C.SolderMaskBottomExpansion)+'|'+IntToStr(C.PasteMaskExpansion)+'|'+Enabled);
  P:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);L.Add('PAD_COUNT='+IntToStr(Count));L.Add('COMPLETE');L.SaveToFile(Path);L.Free;
End;
'''

def make_scripts(plan, affected, candidate_sha):
    header = 'Var B:IPCB_Board;L:TStringList;P:IPCB_Pad;C:TPadCache;I:IPCB_BoardIterator;N:Integer;Good:Boolean;\n'
    header += ' Targets:Array[0..17] Of IPCB_Pad;\n'+CACHE_DUMP.replace('__CANDIDATE__', candidate_sha)
    header += r'''
Function FindPad(RefName,Pin:String;X,Y:Double):IPCB_Pad;
Var J:IPCB_BoardIterator;P:IPCB_Pad;Count:Integer;
Begin Result:=Nil;Count:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(ePadObject));P:=J.FirstPCBObject;
 While P<>Nil Do Begin
  If P.Component<>Nil Then If (P.Component.Name.Text=RefName) And (P.Name=Pin) Then Begin
   Inc(Count);If (Abs(CoordToMMs(P.X)-X)<0.00001) And (Abs(CoordToMMs(P.Y)-Y)<0.00001) And (P.Layer=eBottomLayer) Then Result:=P;
  End;P:=J.NextPCBObject;
 End;B.BoardIterator_Destroy(J);If Count<>1 Then Result:=Nil;
End;
'''
    lines = [header, 'Procedure RepairQD38PadMaskSlivers;', 'Begin',
             ' B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;',
             f' If LowerCase(B.FileName)<>LowerCase({q(PCB)}) Then Exit;',
             f" L:=TStringList.Create;L.Add('EXPECTED_NATIVE_SHA256={NATIVE_SHA}');L.Add('CANDIDATE_SHA256={candidate_sha}');Good:=True;",
             " I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));P:=I.FirstPCBObject;N:=0;While P<>Nil Do Begin Inc(N);P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If N<>243 Then Good:=False;"
             ]
    pads = {(p['ref'], p['pin']): p for p in plan['physical_pads'] if p['ref']}
    for i, (ref, pin) in enumerate(affected):
        p = pads[ref, pin]
        lines += [f" Targets[{i}]:=FindPad({q(ref)},{q(pin)},{p['x']:.12f},{p['y']:.12f});",
                  f" If Targets[{i}]=Nil Then Good:=False Else Begin C:=Targets[{i}].GetState_Cache;If (Abs(CoordToMMs(C.SolderMaskExpansion)-0.05)>0.00001) Or (Abs(CoordToMMs(C.SolderMaskBottomExpansion)-0.05)>0.00001) Or (Not Targets[{i}].GetState_PasteMaskEnabled) Then Good:=False;End;"]
    lines += [f" If Not Good Then Begin L.Add('STOP_GUARD');L.SaveToFile({q(H/'native_mask_repair.txt')});L.Free;Exit;End;",
              f" DumpPads('BEFORE_REPAIR',{q(H/'native_mask_before.txt')});",
              ' PCBServer.PreProcess;Try',
              '  For N:=0 To 17 Do Begin',
              '   P:=Targets[N];PCBServer.SendMessageToRobots(P.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);',
              '   C:=P.GetState_Cache;C.SolderMaskExpansionValid:=eCacheManual;C.SolderMaskExpansion:=MMsToCoord(0.025);C.SolderMaskBottomExpansion:=MMsToCoord(0.025);P.SetState_Cache(C);',
              '   PCBServer.SendMessageToRobots(P.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);',
              '  End;', ' Finally PCBServer.PostProcess;End;',
              ' B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;',
              f" DumpPads('AFTER_REPAIR_UNSAVED',{q(H/'native_mask_after_unsaved.txt')});",
              f" L.Add('CHANGED_PAD_COUNT=18');L.Add('COMPLETE_NOT_SAVED');L.SaveToFile({q(H/'native_mask_repair.txt')});L.Free;", 'End;']
    (H/'RepairQD38PadMaskSlivers.pas').write_text('\n'.join(lines)+'\n', encoding='ascii')
    audit_code = header+f'''\nProcedure AuditReopenedQD38PadMasks;
Begin
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase({q(PCB)}) Then Exit;
 DumpPads('AFTER_REOPEN',{q(H/'native_mask_after_reopen.txt')});
End;
'''
    (H/'AuditReopenedQD38PadMasks.pas').write_text(audit_code, encoding='ascii')
    for name in ('RepairQD38PadMaskSlivers','AuditReopenedQD38PadMasks'):
        (H/f'{name}.PrjScr').write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={name}.pas\n[Generic_ScriptingSystem]\nStartProcName={name}.pas>{name}\n', encoding='ascii')

def main():
    assert sha(OLD_PLAN) == SOURCE_SHA
    assert sha(OLD_NATIVE) == sha(PCB) == NATIVE_SHA, 'Native pre-repair SHA mismatch; stop before script generation'
    plan = json.loads(OLD_PLAN.read_text())
    assert 'pad_solder_mask_overrides' not in plan
    drc_path = H/'pre_mask_repair/Native_DRC.html'
    drc = html.unescape(re.sub('<[^>]+>', '', drc_path.read_text(encoding='utf-8-sig')))
    pairs = re.findall(r'Minimum Solder Mask Sliver Constraint:.*?Between Pad ([RC]\d+-[12])\(.*?And Pad ((?:R|SMP)\d+-\d+)\(', drc)
    assert len(pairs) == 16, pairs
    keys = sorted({tuple(v.split('-')) for pair in pairs for v in pair if not v.startswith('SMP')})
    assert len(keys) == 18, keys
    pads = {(p['ref'], p['pin']): p for p in plan['physical_pads'] if p['ref']}
    checks = []
    for a, b in pairs:
        pa, pb = pads[tuple(a.split('-'))], pads[tuple(b.split('-'))]
        copper_gap = geometry(pa).distance(geometry(pb))
        gap = copper_gap - sum(.025 if tuple(k.split('-')) in keys else .05 for k in (a,b))
        assert gap > .1049, (a,b,gap)
        checks.append(dict(pads=[a,b], copper_gap_mm=copper_gap, before_mask_sliver_mm=copper_gap-.1, repaired_mask_sliver_mm=gap))
    plan['pad_solder_mask_overrides'] = [dict(ref=r,pin=p,expansion_mm=.025,reason='Preserve positive pad aperture and >=0.10 mm solder-mask dam') for r,p in keys]
    plan['mask_sliver_repair'] = dict(source_candidate_sha256=SOURCE_SHA, native_before_sha256=NATIVE_SHA, inherited_expansion_mm=.05, positive_override_mm=.025, selected_pad_count=18, explicit_mask_regions_unchanged=True, copper_paste_rules_models_unchanged=True)
    write_json(OUTPUT,plan)
    candidate_sha=sha(OUTPUT)
    make_scripts(plan,keys,candidate_sha)
    report=dict(passed=True, scope='Offline mask-only delta, not a native DRC pass',candidate=str(OUTPUT),candidate_sha256=candidate_sha,native_before_sha256=NATIVE_SHA,source_candidate_sha256=SOURCE_SHA,drc_before_sha256=sha(drc_path),selected_pad_count=len(keys),selected_pads=['-'.join(k) for k in keys],minimum_repaired_pair_sliver_mm=min(r['repaired_mask_sliver_mm'] for r in checks),pairs=checks,native_execution_performed=False,native_drc_after_repair_pending=True)
    write_json(H/'mask_sliver_repair_plan_audit.json', report)
    print(json.dumps({k:report[k] for k in ('candidate_sha256','selected_pad_count','minimum_repaired_pair_sliver_mm')},indent=2))

if __name__=='__main__': main()
