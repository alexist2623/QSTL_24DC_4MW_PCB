"""Prepare guarded QD-via resizing and Bottom capacitor model correction."""
from pathlib import Path
import sys,json,hashlib,shutil,math
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/rc_mask_margin_20261017'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/qd38_carrier_20261010')]
from audit_saved_revision_surface import read_snapshot,UNIT
from audit_source_model_transforms import inspect
pcb=P/(P.name+'.PcbDoc');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pcb)=='214d65cc0d5debf9ef67c7c31496fe23b06b70147fe2f5511073fe110cb24619'
bk=H/'baseline';bk.mkdir(exist_ok=True)
for src in [pcb,P/(P.name+'.SchDoc'),P/'pin_mapping.csv']:
    dst=bk/src.name
    if dst.exists():assert sha(src)==sha(dst)
    else:shutil.copy2(src,dst)
for name in ['dispatch.py','audit_saved.py','audit_support.py','audit_mask_cam.py','ValidateNative16RF.pas','ValidateNative16RF.PrjScr','ExportCapPaste.pas','ExportCapPaste.PrjScr']:
    s=(OLD/name).read_text(encoding='utf-8').replace(OLD.name,H.name).replace('RC_Mask_Margin_20261017','QD_Via_and_Cap_Models_20261017')
    if name=='audit_support.py':
        s=s.replace("rotation=[0,0,c['rotation']];height=", "rotation=[0,0,plan.get('model_rotation_overrides',{}).get(ref,c['rotation'])];height=")
    (H/name).write_text(s,encoding='utf-8')
(H/'paste_verification').mkdir(exist_ok=True)
(H/'paste_verification/Cap_Paste_Verification.OutJob').write_text((OLD/'paste_verification/Cap_Paste_Verification.OutJob').read_text(encoding='utf-8').replace(OLD.name,H.name),encoding='utf-8')
(P/'QD_Via_and_Cap_Models_20261017').mkdir(exist_ok=True)
plan=json.loads((OLD/'candidate.json').read_text());snap=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()));models=inspect(pcb)
(H/'baseline_models.json').write_text(json.dumps(models,indent=2),encoding='utf-8')
selected=[v for v in plan['vias'] if v['label'].startswith('Q1-')];assert len(selected)==22
via_rows=[];increment=math.ceil(.1/UNIT)
for v in selected:
    actual=next(a for a in snap[3] if a['net']==v['net'] and math.dist((a['x'],a['y']),(v['x'],v['y']))<.00001)
    assert abs(actual['diameter']-.35)<UNIT and abs(actual['hole']-.2)<UNIT and (actual['low'],actual['high'])==(1,32)
    v['diameter']=(round(actual['hole']/UNIT)+increment)*UNIT
    via_rows.append(dict(label=v['label'],net=v['net'],x=actual['x'],y=actual['y'],hole=actual['hole'],before=actual['diameter'],after=v['diameter']))
assert len({v['after'] for v in via_rows})==1
new_units=round(via_rows[0]['after']/UNIT)
caps=[c for c in plan['components'] if c['ref'].startswith('C') and abs(c['rotation']%90)>1e-7];assert len(caps)==8
plan['model_rotation_overrides']={c['ref']:(-c['rotation'])%360 for c in caps}
plan['QD_via_land_nominal_mm']=.3
(H/'candidate.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(H/'preparation_audit.json').write_text(json.dumps(dict(source_sha256=sha(pcb),via_changes=via_rows,minimum_diameter_difference_units=increment,new_diameter_units=new_units,model_rotation_overrides=plan['model_rotation_overrides']),indent=2),encoding='utf-8')
match=' Or\n'.join(f"((V.Net.Name='{v['net']}') And (Abs(CoordToMMs(V.X)-{v['x']:.12f})<0.00001) And (Abs(CoordToMMs(V.Y)-{v['y']:.12f})<0.00001))" for v in via_rows)
stem='ResizeQDVias'
pas=f"""Procedure {stem};
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;R:IPCB_Rule;VR:IPCB_RoutingViaStyleRule;
Q:Array[0..21] Of IPCB_Via;N,K,Total:Integer;L:TStringList;
Begin L:=TStringList.Create;L.Add('START');L.SaveToFile('{H/'via_apply_log.txt'}');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
N:=0;Total:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
While V<>Nil Do Begin Inc(Total);If V.Net<>Nil Then If {match} Then Begin If N>=22 Then Exit;Q[N]:=V;Inc(N);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
If (N<>22) Or (Total<>1590) Then Exit;
For K:=0 To 21 Do Begin V:=Q[K];If (Abs(CoordToMMs(V.Size)-0.35)>0.00001) Or (Abs(CoordToMMs(V.HoleSize)-0.2)>0.00001) Or (V.LowLayer<>eTopLayer) Or (V.HighLayer<>eBottomLayer) Then Exit;End;
VR:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;
While R<>Nil Do Begin If R.Name='QD38_QD_VIA_0P4_0P2' Then VR:=R;R:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If VR=Nil Then Exit;
PCBServer.PreProcess;
Try For K:=0 To 21 Do Begin V:=Q[K];PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
V.Size:=V.HoleSize+{increment};PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);End;
PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
VR.MinWidth:={new_units};VR.MaxWidth:={new_units};VR.PreferedWidth:={new_units};
PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
L.Add('QD_VIAS_RESIZED=22');L.Add('ONLY_QD_STYLE_WIDTH_UPDATED');L.Add('COMPLETE_REQUIRES_SAVE');L.SaveToFile('{H/'via_apply_log.txt'}');L.Free;End;
"""
def write(stem,pas):
    (H/(stem+'.pas')).write_text(pas,encoding='ascii')
    (H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
write(stem,pas)
for stem,refs in [('TestC11Model',{'C11'}),('CorrectCapModels',{c['ref'] for c in caps})]:
    conditions=' Or '.join(f"(C.Name.Text='{r}')" for r in sorted(refs))
    pas=f"""Procedure {stem};
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;Body:IPCB_ComponentBody;C:IPCB_Component;
Bodies:Array[0..15] Of IPCB_ComponentBody;M:IPCB_Model;K,N:Integer;Angle:Double;L:TStringList;
Begin L:=TStringList.Create;L.Add('START');L.SaveToFile('{H/(stem+'_log.txt')}');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
N:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
While Body<>Nil Do Begin C:=Body.Component;If C<>Nil Then If {conditions} Then Begin If N>=16 Then Exit;Bodies[N]:=Body;Inc(N);End;Body:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
If N<>{len(refs)} Then Exit;PCBServer.PreProcess;
Try For K:=0 To N-1 Do Begin Body:=Bodies[K];C:=Body.Component;Angle:=360-C.Rotation;While Angle>=360 Do Angle:=Angle-360;While Angle<0 Do Angle:=Angle+360;
PCBServer.SendMessageToRobots(Body.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
M:=Body.GetModel;M:=M.I_Replicate;M.SetState(0,0,Angle,0);M.SetEmbed(True);Body.SetModel(M);Body.SetState_FromModel;
Body.SetBodyProjection(eBoardSide_Bottom);Body.SetStandoffHeight(0);Body.SetOverallHeight(MMsToCoord(1.8));Body.ValidateMesh;
PCBServer.SendMessageToRobots(Body.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);L.Add('MODEL='+C.Name.Text+'|ROTZ='+FloatToStr(Angle));End;
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
L.Add('COMPLETE_REQUIRES_VISUAL_CHECK_AND_SAVE');L.SaveToFile('{H/(stem+'_log.txt')}');L.Free;End;
"""
    write(stem,pas)
print(json.dumps(dict(QD_vias=len(selected),new_land_mm=via_rows[0]['after'],ring_mm=(via_rows[0]['after']-via_rows[0]['hole'])/2,model_rotation_trial=plan['model_rotation_overrides']),indent=2))
