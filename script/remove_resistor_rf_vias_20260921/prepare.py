"""Remove only the six unused RF-side resistor vias from the original PCB."""
from pathlib import Path
import sys,json,math,copy,shutil,importlib.util
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';OLD=H.parent/'rc_mask_clearance_20260921';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import sha,UNIT
source=P/(B+'.PcbDoc');previous=json.loads((OLD/'validation.json').read_text());assert previous['passed'] and sha(source)==previous['pcb_sha256']
if not (H/'before.PcbDoc').exists():shutil.copy2(source,H/'before.PcbDoc')
assert sha(H/'before.PcbDoc')==sha(source)
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=source;n=m.read_native();assert len(n['vias'])==530
(H/'before_native.json').write_text(json.dumps(n,indent=2));wanted=copy.deepcopy(n);removed=[]
for ch in range(1,7):
    pad=next(p for p in n['pads'] if p['component']==f'R{ch}' and p['number']=='1');assert pad['net']==f'MW{ch}' and pad['layer']==32
    candidates=[v for v in wanted['vias'] if v['net']==pad['net'] and math.dist((v['x'],v['y']),(pad['x'],pad['y']))<4*UNIT];assert len(candidates)==1
    v=candidates[0];assert abs(v['diameter']-.5)<4*UNIT and abs(v['hole']-.25)<4*UNIT
    assert all(t['layer']==32 for t in n['tracks'] if t['net']==pad['net'])
    removed.append(dict(component=f'R{ch}',pad='1',**v));wanted['vias'].remove(v)
assert len(wanted['vias'])==524
plan=json.loads((OLD/'plan.json').read_text());plan.update(source_sha256=sha(source),removed_resistor_RF_vias=removed,component_y_moves_mm={},component_x_moves_mm={})
(H/'plan.json').write_text(json.dumps(plan,indent=2));(H/'planned_native.json').write_text(json.dumps(wanted,indent=2))
req=P/'docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8');needle='- Use via-in-pad for QD and the DC-feeding bias-resistor pads.'
s=s.replace(needle,needle+' R1-R6 must have exactly one via each, at DC pad 2. RF pad 1 connects entirely on Bottom and must have no via; do not add a through via to a same-layer RF junction. This explicitly supersedes the former two-vias-per-resistor implementation.')
req.write_text(s,encoding='utf-8');ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8');s+='\nKeep exactly one via per bias resistor, on DC pad 2. R1-R6 RF pad 1 and both pads of C1-C6 must have no vias because their RF routing remains on Bottom. Preserve QD and ZIF via-in-pad.\n';ag.write_text(s,encoding='utf-8')
for name in ('audit_connectivity.py','verify_final.py','AuditPaste.pas','ReopenAudit.pas','read_drc.py','verify_refinements.py','fabrication_notes.py','publish_outputs.py','verify_fabrication.py','ShowFinal.pas'):
    s=(OLD/name).read_text(encoding='utf-8').replace(OLD.name,H.name).replace('RC_Mask_Clearance_DRC.html','Resistor_RF_Via_Removal_DRC.html').replace('RC_Mask_Clearance_validation.json','Resistor_RF_Via_Removal_validation.json').replace('rc_mask_clearance_reopen_check.txt','resistor_rf_via_removal_reopen_check.txt')
    if name=='verify_final.py':
        s=s.replace("if c=='Q1' or c.startswith('R'):","if c=='Q1' or (c.startswith('R') and p['number']=='2'):")
        s=s.replace("if c.startswith('C'):","if c.startswith('R') and p['number']=='1':check(not matches,f'RF-side resistor via remains {c}.{p[\"number\"]}')\n        if c.startswith('C'):")
        s=s.replace('(22,147,37,530)','(22,147,37,524)').replace('len(signal)==60','len(signal)==54')
        # Prove the via set changed only by the explicitly requested six entries.
        at="for v in shield:\n"
        extra="""def viakey(v):return (v['net'],*(round(v[k]/UNIT) for k in ('x','y','diameter','hole')))
check(collections.Counter(map(viakey,vs))==collections.Counter(map(viakey,wanted['vias'])),'Unexpected via addition, deletion or movement')
from preservation_helpers import text_fingerprint
check(collections.Counter(r['body'] for r in binary_records(s['Tracks6/Data'],4))==collections.Counter(r['body'] for r in binary_records(old['Tracks6/Data'],4)),'Track primitive data changed')
check(collections.Counter(text_fingerprint(s['Texts6/Data']))==collections.Counter(text_fingerprint(old['Texts6/Data'])),'Text primitive data changed')
text_before=(H/'text_before.txt').read_bytes();text_after=(H/'text_after.txt').read_bytes()
check(text_before==text_after and b'COMPLETE' in text_after,'Native text/font properties changed')
for stream in ('Pads6/Data','Components6/Data','Arcs6/Data','Fills6/Data','Nets6/Data'):
    check(s[stream]==old[stream],'Unrequested object change '+stream)
for ext,key in (('.SchDoc','schematic_sha256'),('.PcbLib','pcblib_sha256')):
    check(sha(P/(B+ext))==json.loads((H.parent/'rc_mask_clearance_20260921'/'validation.json').read_text())[key],'Unrequested file change '+ext)
"""
        s=s.replace(at,extra+at)
        s=s.replace('capacitor_vias_remaining=len(cap_vias)',"capacitor_vias_remaining=len(cap_vias),resistor_RF_vias_remaining=0,resistor_DC_vias_remaining=6")
    if name=='fabrication_notes.py':s=s.replace('Preserve QD via-in-pad and required resistor/DC vias.','Preserve QD via-in-pad and one DC-side via on pad 2 of each R1-R6. Remove all six unused RF-side resistor pad 1 vias; their RF path remains on L6.')
    (H/name).write_text(s,encoding='utf-8')
q=lambda x:round(x/UNIT)
init='\n'.join(f"VX[{j}]:={q(v['x'])};VY[{j}]:={q(v['y'])};VN[{j}]:='{v['net']}';" for j,v in enumerate(removed,1))
pas='''Var Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('@LOG@');End;
Procedure RemoveRFVias;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;Poly:IPCB_Polygon;Net:IPCB_Net;
Dead:Array[1..6] Of IPCB_Via;Found:Array[1..6] Of Boolean;VX,VY:Array[1..6] Of Integer;VN:Array[1..6] Of String;Polys:Array[0..7] Of IPCB_Polygon;Nets:Array[0..63] Of IPCB_Net;N,NV,NP,NN,J:Integer;
Begin
 Log:=TStringList.Create;Mark('START');D:=Client.OpenDocument('PCB','@PCB@');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('@PCB@') Then Exit;
 @INIT@
 For J:=1 To 6 Do Found[J]:=False;N:=0;NV:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin Inc(NV);If V.Net<>Nil Then For J:=1 To 6 Do If V.Net.Name=VN[J] Then If (Abs(V.X-VX[J])<4) And (Abs(V.Y-VY[J])<4) Then Begin If Found[J] Then Begin Mark('DUPLICATE_TARGET');Exit;End;Found[J]:=True;Dead[J]:=V;Inc(N);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('TOTAL_VIAS='+IntToStr(NV));Mark('RF_RESISTOR_TARGETS='+IntToStr(N));If (NV<>530) Or (N<>6) Then Begin Mark('GUARD_STOP');Exit;End;
 PCBServer.PreProcess;Try
 For J:=1 To 6 Do Begin B.RemovePCBObject(Dead[J]);Mark('REMOVED='+VN[J]);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;NP:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NP]:=Poly;Inc(NP);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NP-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;Mark('REPOURED='+Polys[J].Name);End;
 NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));Net:=I.FirstPCBObject;While Net<>Nil Do Begin Nets[NN]:=Net;Inc(NN);Net:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin Nets[J].ConnectivelyInValidate;Nets[J].Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED');Mark('COMPLETE');Log.Free;
End;
Procedure RunSafely;Begin Try RemoveRFVias;Except Mark('CAUGHT_NATIVE_FAILURE');End;End;
'''
for key,value in {'LOG':str(H/'native_change.txt'),'PCB':str(source),'INIT':init}.items():pas=pas.replace('@'+key+'@',value)
(H/'RemoveRFVias.pas').write_text(pas,encoding='utf-8');print(json.dumps(removed,indent=2))
