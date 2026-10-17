"""Widen the 38 QD pads and solve minimal local shield displacement."""
from pathlib import Path
import sys,json,hashlib,shutil,math
import numpy as np
from scipy.optimize import minimize
from shapely.geometry import Point,shape,mapping
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
from shapely import points,distance
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/compact_masks_20261016'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
from audit_saved_revision_surface import read_snapshot,pad_shape
import native_constructors as nc
pcb=P/(P.name+'.PcbDoc');digest=hashlib.sha256(pcb.read_bytes()).hexdigest();assert digest=='0abc5c7a8258df4c239ed4535fba5e120190757f4976b8fbe72d4fae5b1eaad0'
bk=H/'baseline';bk.mkdir(exist_ok=True)
for src in [pcb,P/(P.name+'.SchDoc'),P/'pin_mapping.csv',OLD/'candidate.json']:
    dest=bk/src.name
    if dest.exists():assert dest.read_bytes()==src.read_bytes()
    else:shutil.copy2(src,dest)
plan=json.loads((OLD/'candidate.json').read_text());pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
qd=[p for p in pads if p['ref']=='Q1'];widened=[dict(p,sy=.26) for p in qd];qp=unary_union([pad_shape(p) for p in widened]);minpad=min(pad_shape(a).distance(pad_shape(b)) for i,a in enumerate(widened) for b in widened[i+1:]);assert minpad>.151
gnd={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll and r['net']=='GND']) for ll in (5,32)}
newgnd=gnd[32].difference(qp.buffer(.2005,quad_segs=96))
rf=unary_union([t['geometry'] for t in tracks if t['layer']==32 and t['net'] and t['net'].startswith(('MW','S'))])
sh=[v for v in vias if v['net']=='GND'];xy=np.array([[v['x'],v['y']] for v in sh])
seed=[i for i,v in enumerate(sh) if Point(v['x'],v['y']).distance(qp)-v['diameter']/2<.2005]
assert len(seed)==5,seed
active=sorted({i for k in seed for i,z in enumerate(xy) if np.linalg.norm(z-xy[k])<.85});fixed=[i for i in range(len(sh)) if i not in active]
x0=xy[active];fx=xy[fixed];pairs=[(i,j) for i in range(len(active)) for j in range(i+1,len(active)) if np.linalg.norm(x0[i]-x0[j])<.5]
fixed_pairs=[(i,j) for i in range(len(active)) for j in range(len(fixed)) if np.linalg.norm(x0[i]-fx[j])<.5]
signalvias=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=96) for v in vias if v['net']!='GND'])
otherpads=unary_union([p['geometry'] for p in pads if p['layer'] in (32,74) and p['ref']!='Q1' and p['net']!='GND'])
def constraints(z):
    a=z.reshape((-1,2));pts=points(a);vals=[distance(pts,qp)-.326,distance(pts,rf)-.43501,distance(pts,signalvias)-.27501,distance(pts,otherpads)-.27501]
    # Existing ground obstacles remain fixed; every moved land must stay covered.
    for ll,g in ((5,gnd[5]),(32,newgnd)):
        vals.append(distance(pts,g.boundary)-.125005)
    vals += [np.array([np.linalg.norm(a[i]-a[j])-.40001 for i,j in pairs]),np.array([np.linalg.norm(a[i]-fx[j])-.40001 for i,j in fixed_pairs])]
    return np.concatenate(vals)
result=minimize(lambda z:float(np.sum((z-x0.ravel())**2)),x0.ravel(),method='SLSQP',constraints={'type':'ineq','fun':constraints},bounds=[(v-.03,v+.03) for v in x0.ravel()],options={'maxiter':350,'ftol':1e-13})
assert result.success and min(constraints(result.x))>-.0000002,(result.message,min(constraints(result.x)))
newxy=result.x.reshape((-1,2));moves=[]
for k,a,b in zip(active,x0,newxy):
    delta=float(np.linalg.norm(b-a))
    if delta<2.54e-6:continue
    v=sh[k]
    for ll,g in ((5,gnd[5]),(32,newgnd)):
        assert g.buffer(.000015).covers(Point(*b).buffer(v['diameter']/2,quad_segs=96)),(k,ll)
    moves.append(dict(index=k,before=a.tolist(),after=b.tolist(),shift_mm=delta))
    pv=min(plan['shield_vias'],key=lambda p:math.dist((p['x'],p['y']),a));assert math.dist((pv['x'],pv['y']),a)<.00001
    pv['x'],pv['y']=map(float,b)
for p in plan['physical_pads']:
    if p['ref']=='Q1':p['sy']=.26
plan['ground_regions']['32']=mapping(newgnd)
plan['bond_pad_width_mm']=.26
(H/'candidate.json').write_text(json.dumps(plan,indent=2))
metrics=dict(before_sha256=digest,width_before_mm=.25,width_after_mm=.26,min_pad_gap_mm=minpad,initial_shield_conflicts=len(seed),optimized_shields=len(active),moved_shields=moves,max_shift_mm=max(m['shift_mm'] for m in moves),L6_removed_ground_mm2=gnd[32].area-newgnd.area,ground_before_area_mm2=gnd[32].area)
(H/'preparation_audit.json').write_text(json.dumps(metrics,indent=2))
for name in ['dispatch.py','audit_saved.py','audit_support.py','audit_mask_cam.py','ValidateNative16RF.pas','ValidateNative16RF.PrjScr','ExportCapPaste.pas','ExportCapPaste.PrjScr']:
    s=(OLD/name).read_text().replace('compact_masks_20261016','bond_pad_width_20261016').replace('Compact_Masks_20261016','Bond_Pad_Width_20261017')
    if name=='audit_saved.py':s=s.replace("int(ll)==5 and plan.get('L5_component_cutouts')","((int(ll)==5 and plan.get('L5_component_cutouts')) or (int(ll)==32 and plan.get('bond_pad_width_mm')))")
    (H/name).write_text(s)
(H/'paste_verification').mkdir(exist_ok=True)
(H/'paste_verification/Cap_Paste_Verification.OutJob').write_text((OLD/'paste_verification/Cap_Paste_Verification.OutJob').read_text().replace('compact_masks_20261016','bond_pad_width_20261016'))
(P/'Bond_Pad_Width_20261017').mkdir(exist_ok=True)
stm=[];contours=[];ground_shape=shape(plan['ground_regions']['32'])
for i,poly in enumerate(ground_shape.geoms if hasattr(ground_shape,'geoms') else [ground_shape]):
    poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
    for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
        xy2=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in xy2)
        stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(xy2)});',f'G.AddContourIsHole(CT,{hole});'])
    stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:=eBottomLayer;RG.Name:='WIDE_QD_GND_{i}';RG.Net:=Ns[0];RG.SetState_InNet(True);RG.SetGeometricPolygon(G);Reg(RG);")
(H/'ground_contours.txt').write_text('\n'.join(contours))
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'apply_log.txt')).replace('Good:Boolean;','ContourData:TStringList;Good:Boolean;').replace('PD:IPCB_Pad;','PD:IPCB_Pad;QDPads:Array[0..37] Of IPCB_Pad;')
extra="""Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
Procedure MoveShield(X,Y,U,W:Double);
Var It:IPCB_BoardIterator;V:IPCB_Via;Count:Integer;
Begin Count:=0;It:=B.BoardIterator_Create;It.SetState_FilterAll;It.AddFilter_ObjectSet(MkSet(eViaObject));V:=It.FirstPCBObject;
While V<>Nil Do Begin If (Abs(CoordToMMs(V.X)-X)<0.00001) And (Abs(CoordToMMs(V.Y)-Y)<0.00001) Then Begin
If V.Net<>Nil Then If V.Net.Name='GND' Then Begin Inc(Count);PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);V.X:=MMsToCoord(U);V.Y:=MMsToCoord(W);PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);End;End;V:=It.NextPCBObject;End;B.BoardIterator_Destroy(It);Mark('SHIELD_MOVE_COUNT='+IntToStr(Count));End;
"""
batches=[stm[i:i+100] for i in range(0,len(stm),100)];body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches));stem='WidenQDBondPads'
main=f"""Procedure {stem};
Begin Log:=TStringList.Create;Mark('START_QD_WIDTH');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1590) Then Begin Mark('STOP_COUNT');Exit;End;
Ns[0]:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
While N<>Nil Do Begin If N.Name='GND' Then Ns[0]:=N;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If Ns[0]=Nil Then Exit;
ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'ground_contours.txt'}');PCBServer.PreProcess;
Try NC:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;
While PD<>Nil Do Begin If PD.Component<>Nil Then If PD.Component.Name.Text='Q1' Then Begin If NC>=38 Then Exit;QDPads[NC]:=PD;Inc(NC);End;PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If NC<>38 Then Exit;
For K:=0 To 37 Do Begin PD:=QDPads[K];
PCBServer.SendMessageToRobots(PD.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);
PD.TopYSize:=MMsToCoord(0.26);PD.MidYSize:=PD.TopYSize;PD.BotYSize:=PD.TopYSize;
PCBServer.SendMessageToRobots(PD.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);End;Mark('QD_PADS_WIDENED=38');
{''.join('MoveShield('+','.join(nc.number(v) for v in m['before']+m['after'])+');' for m in moves)}
ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));P:=I.FirstPCBObject;
While P<>Nil Do Begin If P.Layer=eBottomLayer Then If P.Net<>Nil Then If P.Net.Name='GND' Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_L6_GND='+IntToStr(ND));
{''.join(f'Update{i};' for i in range(len(batches)))}
Finally PCBServer.PostProcess;End;
Ns[0].ConnectivelyInValidate;Ns[0].Rebuild;B.ConnectivelyValidateNets;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
Mark('COMPLETE_REQUIRES_SAVE');ContourData.Free;Log.Free;End;
"""
(H/(stem+'.pas')).write_text(header+extra+body+main,encoding='ascii')
(H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
print(json.dumps(metrics,indent=2))
