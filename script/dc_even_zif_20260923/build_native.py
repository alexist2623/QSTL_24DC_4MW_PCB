"""Generate guarded Altium mutation, schematic sync and read-only audits."""
from pathlib import Path
import json,sys,copy,shutil
from shapely.geometry import shape
from shapely.geometry.polygon import orient
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB';U=2.54e-6
n=json.loads((H/'before_native.json').read_text());wanted=json.loads((H/'planned_native.json').read_text());plan=json.loads((H/'plan.json').read_text());rename=plan['rename']
sys.path[:0]=[str(W/x) for x in ('zif_revision/schematic','zif_revision_v2/schematic','qd_center_revision')]
import build_zif_schematic as base
from cfb_copy_update import update_copy
from native_metadata_helpers import olefile,sha
D=H/'built';D.mkdir(exist_ok=True)
e=json.loads((H.parent/'rf_six_inward_20260920/expected.json').read_text());pn={p['component']+'-'+p['number']:p['net'] for p in wanted['pads'] if p['component'] and p['net'] is not None};nc=sorted(p['component']+'-'+p['number'] for p in wanted['pads'] if p['component'] and p['net'] is None)
e.update(pin_net_map=pn,nc_pins=nc,nets={},zif_to_target={},rf_bias_zif_pins={},source_hashes={str(H/('before.'+ext)):sha(H/('before.'+ext)) for ext in ('PcbDoc','SchDoc','SchLib')})
for pin,net in pn.items():e['nets'].setdefault(net,[]).append(pin)
for net,pins in e['nets'].items():
 if net.startswith('ZIF'):e['zif_to_target'][str(int(net[3:]))]=next(p for p in pins if not p.startswith('J1-'))
e['rf_bias_zif_pins']={str(i):str(int(pn[f'R{i}-2'][3:])) for i in range(1,7)}
rs=base.records(H/'before.SchDoc');refs={int(r['OwnerIndex']):r['Text'] for r in rs if r.get('RECORD')=='34'}
# Preserve component records and their UIDs. Replace only leaf label/wire/NC records.
out=[copy.deepcopy(r) for r in rs if r.get('RECORD') not in ('22','25','27')]
# All removed objects must occur after components; otherwise owner indexes need remapping.
lastowned=max(i for i,r in enumerate(rs) if 'OwnerIndex' in r and r.get('RECORD') not in ('22','25','27'))
assert all(i>lastowned for i,r in enumerate(rs) if r.get('RECORD') in ('22','25','27'))
for r in out:
 if r.get('RECORD')=='2' and refs[int(r['OwnerIndex'])]=='Q1':r['Name']=pn['Q1-'+r['Designator']]
 if r.get('RECORD')=='4' and r.get('Text','').startswith('J1 uses'):r['Text']='J1 uses even contacts 2..48 only. Pin50, odd contacts and mounts52/53 are NC.'
e['pins']=base.append_connections(out,pn,nc);out[0]['Weight']=str(len(out)-1)
update_copy(H/'before.SchDoc',D/(B+'.SchDoc'),{'FileHeader':base.pack([(0,base.encode(r)) for r in out])})
with olefile.OleFileIO(H/'before.SchLib') as o:rows=base.blocks(o.openstream('QD4/Data').read())
newrows=[]
for flag,b in rows:
 if flag==1:
  assert b[0]==2;pos=27+b[26];num=b[pos+1:pos+1+b[pos]].decode('ascii');name=pn['Q1-'+num].encode('ascii');b=b[:26]+bytes([len(name)])+name+b[pos:]
 newrows.append((flag,b))
update_copy(H/'before.SchLib',D/(B+'.SchLib'),{'QD4/Data':base.pack(newrows)})
(H/'expected.json').write_text(json.dumps(e,indent=2))
ns={'__file__':str(W/'zif_revision_v2/schematic/validate_v2_schematic.py'),'__name__':'even_validator'};exec(compile((H.parent/'rf_six_inward_20260920/validator_source.py').read_text(),ns['__file__'],'exec'),ns)
rep=ns['validate'](D/(B+'.SchDoc'),e);(H/'schematic_preflight.json').write_text(json.dumps(rep,indent=2));assert rep['passed'],rep['errors']
q=lambda v:round(v/U)
lines=[]
for i,(old,new) in enumerate(rename.items()):lines.append(f"OldName[{i}]:='{old}';NewName[{i}]:='{new}';")
for i,f in enumerate(plan['fanouts']):
 v=next(v for v in n['vias'] if v['net']==f['old_net'] and v['y']<10)
 lines.append(f"VX[{i}]:={q(v['x'])};VY[{i}]:={q(v['y'])};NX[{i}]:={q(f['x'])};NY[{i}]:={q(f['y'])};")
routes=[]
for t in wanted['tracks']:
 if t['net'].startswith('ZIF'):routes.append("AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{1:'eTopLayer',2:'eMidLayer1',4:'eMidLayer3'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ('x1','y1','x2','y2','width'))))
mask=[]
for layer,key in [(37,'Top_mask_opening'),(38,'Bottom_mask_opening')]:
 g=shape(plan[key])
 for idx,poly in enumerate(g.geoms if hasattr(g,'geoms') else [g]):
  poly=orient(poly,sign=1);mask+=['G:=PCBServer.PCBGeometricPolygonFactory;']
  for hole,ring in [(False,poly.exterior)]+[(True,x) for x in poly.interiors]:mask+=['Contour:=PCBServer.PCBContourFactory;']+[f'Contour.AddPoint({q(x)},{q(y)});' for x,y in list(ring.coords)[:-1]]+[f'G.AddContourIsHole(Contour,{hole});']
  mask += [f"Reg:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Reg.Kind:=eRegionKind_Copper;Reg.Layer:={'eTopSolder' if layer==37 else 'eBottomSolder'};Reg.Name:='SURFACE_MASK_OPEN_{layer}_{idx}';Reg.SetGeometricPolygon(G);B.AddPCBObject(Reg);"]
src=(H.parent/'lower_rc_70pct_20260921/ApplyMove.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Procedure ApplyMove;')]
pas=r'''Var Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('@LOG@');End;
@HELPERS@
Procedure ApplyEvenDC;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;O:IPCB_Primitive;N:IPCB_Net;Pad:IPCB_Pad;V:IPCB_Via;C:IPCB_Component;Reg:IPCB_Region;Poly:IPCB_Polygon;G:IPCB_GeometricPolygon;Contour:IPCB_Contour;
OldName,NewName:Array[0..23] Of String;NN:Array[0..23] Of IPCB_Net;VV:Array[0..23] Of IPCB_Via;VX,VY,NX,NY:Array[0..23] Of Integer;
Dead:Array[0..2047] Of IPCB_Primitive;Polys:Array[0..7] Of IPCB_Polygon;ND,NV,NP,NZ,NR,NPoly,J,K,PinNumber:Integer;
Begin
 Log:=TStringList.Create;Mark('START');D:=Client.OpenDocument('PCB','@PCB@');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('@PCB@') Then Exit;
 @INIT@
 For J:=0 To 23 Do Begin NN[J]:=FindNet(B,OldName[J]);If NN[J]=Nil Then Begin Mark('NET_GUARD_FAILED');Exit;End;End;
 ND:=0;NV:=0;NP:=0;NZ:=0;NR:=0;NPoly:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eViaObject,ePadObject,eRegionObject,ePolyObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
 If O.ObjectId=eTrackObject Then If O.Net<>Nil Then If Pos('ZIF',O.Net.Name)=1 Then Begin Dead[ND]:=O;Inc(ND);End;
 If O.ObjectId=eViaObject Then Begin Inc(NV);V:=O;For J:=0 To 23 Do If (Abs(V.X-VX[J])<4) And (Abs(V.Y-VY[J])<4) Then Begin VV[J]:=V;Inc(NZ);End;End;
 If O.ObjectId=ePadObject Then Inc(NP);
 If O.ObjectId=eRegionObject Then Begin Reg:=O;If Pos('SURFACE_MASK_OPEN_',Reg.Name)=1 Then Begin Dead[ND]:=O;Inc(ND);Inc(NR);End;End;
 If O.ObjectId=ePolyObject Then Begin Polys[NPoly]:=O;Inc(NPoly);End;
 O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('PREFLIGHT='+IntToStr(ND)+','+IntToStr(NV)+','+IntToStr(NP)+','+IntToStr(NZ)+','+IntToStr(NR)+','+IntToStr(NPoly));
 If (ND<>@DEAD@) Or (NV<>528) Or (NP<>147) Or (NZ<>24) Or (NR<>2) Then Begin Mark('PREFLIGHT_FAILED');Exit;End;
 PCBServer.PreProcess;Try
 For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);
 For J:=0 To 23 Do NN[J].Name:='EVEN_REMAP_'+IntToStr(J);
 For J:=0 To 23 Do NN[J].Name:=NewName[J];
 For J:=0 To 23 Do VV[J].MoveToXY(NX[J],NY[J]);
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;
 While Pad<>Nil Do Begin C:=Pad.Component;If C<>Nil Then If C.Name.Text='J1' Then Begin
 PinNumber:=StrToInt(Pad.Name);Pad.BeginModify;Pad.Net:=Nil;Pad.SetState_InNet(False);
 If (PinNumber>=2) And (PinNumber<=48) And ((PinNumber Mod 2)=0) Then Begin If PinNumber<10 Then Pad.Net:=FindNet(B,'ZIF0'+IntToStr(PinNumber)) Else Pad.Net:=FindNet(B,'ZIF'+IntToStr(PinNumber));End;
 Pad.SetState_InNet(Pad.Net<>Nil);Pad.EndModify;
 End;Pad:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 @ROUTES@
 @MASK@
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.ConnectivelyValidateNets;
 For J:=0 To NPoly-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 For J:=0 To 23 Do Begin NN[J].ConnectivelyInValidate;NN[J].Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveCurrent;Mark('SAVED');
 D:=Client.GetDocumentByPath('@SCH@');If D<>Nil Then Client.CloseDocument(D);
 D:=Client.GetDocumentByPath('@LIB@');If D<>Nil Then Client.CloseDocument(D);
 Mark('COMPLETE');Log.Free;
End;
'''
for key,value in {'LOG':str(H/'apply_native.txt'),'PCB':str(P/(B+'.PcbDoc')),'SCH':str(P/(B+'.SchDoc')),'LIB':str(P/(B+'.SchLib')),'INIT':'\n'.join(lines),'HELPERS':helpers,'DEAD':str(sum(t['net'].startswith('ZIF') for t in n['tracks'])+2),'ROUTES':'\n'.join(routes),'MASK':'\n'.join(mask)}.items():pas=pas.replace('@'+key+'@',value)
(H/'ApplyEvenDC.pas').write_text(pas)
reopen=(H.parent/'lower_rc_70pct_20260921/ReopenAudit.pas').read_text().replace("ConnPath+'work\\lower_rc_70pct_reopen_check.txt'",repr(str(H/'reopen_check.txt'))).replace('docs\\Lower_RC_70pct_DRC.html','docs\\DC_Even_ZIF_DRC.html')
(H/'ReopenAudit.pas').write_text(reopen.replace(chr(92)*2,chr(92)))
compilepas=(H.parent/'rf_six_inward_20260920/ValidateSchematic.pas').read_text().replace("ExtractFilePath(DraftSchPath)+'work\\rf6_schematic_compile.txt'",repr(str(H/'schematic_compile.txt')))
(H/'ValidateSchematic.pas').write_text(compilepas.replace(chr(92)*2,chr(92)))
paste=(H.parent/'lower_rc_70pct_20260921/AuditPaste.pas').read_text().replace('lower_rc_70pct_20260921','dc_even_zif_20260923');(H/'AuditPaste.pas').write_text(paste)
(H/'EvenDC.PrjScr').write_text('[Design]\nVersion=1.0\nHierarchyMode=0\n'+''.join(f'\n[Document{i}]\nDocumentPath={s}.pas\nAnnotationEnabled=1\n' for i,s in enumerate(['ApplyEvenDC','ReopenAudit','ValidateSchematic','AuditPaste'],1)))
print(json.dumps(dict(schematic_preflight=rep['passed'],pin_count=rep['counts'],bias=e['rf_bias_zif_pins'],native_tracks=len(routes),mask_lines=len(mask)),indent=2))
