"""Prepare a guarded L5-only correction using actual saved pad outlines."""
from pathlib import Path
import sys,json,hashlib,shutil,math
from shapely.geometry import Point,MultiPoint,shape,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
sys.path[:0]=[str(ROOT/'script/native_16rf_apply_20261016'),str(ROOT/'script/qd38_rotation_20261011')]
import native_constructors as nc
from audit_saved_revision_surface import read_snapshot,UNIT
pcb=P/(N+'.PcbDoc');digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
assert digest=='012ac75a0f807e5213ff8c0638402fbb9aab77252f20f3eacdea856f96112b22',digest
bk=H/'before_l5_voids';bk.mkdir(exist_ok=True)
for f in (pcb,H/'candidate.json',H/'l5_rc_openings_audit.json'):
    assert not (bk/f.name).exists();shutil.copy2(f,bk/f.name)
pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
old=unary_union([r['geometry'] for r in regions if r['layer']==5 and r['net']=='GND'])
refs=sorted(set(p['ref'] for p in pads if p['ref'] and p['ref'][0] in 'RC'));voids={}
for ref in refs:
    pp=[p for p in pads if p['ref']==ref];assert len(pp)==2
    hull=unary_union([p['geometry'] for p in pp]).convex_hull
    corners=[]
    for x,y in list(hull.exterior.coords)[:-1]:
        corners.extend((xi*UNIT,yi*UNIT) for xi in {math.floor(x/UNIT),math.ceil(x/UNIT)} for yi in {math.floor(y/UNIT),math.ceil(y/UNIT)})
    g=MultiPoint(corners).convex_hull
    assert hull.difference(g.buffer(UNIT/100)).area<1e-9
    voids[ref]=g
assert len(voids)==32
new=old.difference(unary_union(list(voids.values())))
for v in vias:
    if v['net']=='GND':assert Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64).difference(new.buffer(.000025)).area<1e-7
plan=json.loads((H/'candidate.json').read_text());plan['ground_regions']['5']=mapping(new);plan['L5_component_cutouts']={k:mapping(v) for k,v in voids.items()}
(H/'candidate.json').write_text(json.dumps(plan,indent=2))
(H/'l5_void_preparation.json').write_text(json.dumps(dict(before_sha256=digest,void_count=32,removed_copper_area_mm2=old.area-new.area,cutouts=plan['L5_component_cutouts']),indent=2))
stm=[];contours=[]
def add(poly,name,cutout=False):
    poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
    for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
        xy=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in xy)
        stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(xy)});',f'G.AddContourIsHole(CT,{hole});'])
    stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:={'eRegionKind_Cutout' if cutout else 'eRegionKind_Copper'};RG.Layer:=eMidLayer4;RG.Name:='{name}';RG.SetGeometricPolygon(G);")
    if not cutout:stm.append('RG.Net:=Ns[0];RG.SetState_InNet(True);')
    stm.append('Reg(RG);')
for i,g in enumerate(new.geoms if hasattr(new,'geoms') else [new]):add(g,f'RF_ENTRY_GND_5_RCVOIDS_{i}')
for ref,g in voids.items():add(g,'L5_RC_PAD_VOID_'+ref,True)
(H/'l5_contours.txt').write_text('\n'.join(contours))
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'l5_apply_log.txt')).replace('Good:Boolean;','ContourData:TStringList;Good:Boolean;')
extra='''Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
'''
batches=[stm[i:i+100] for i in range(0,len(stm),100)]
body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches))
stem='ApplyL5RCVoids'
main=f'''Procedure {stem};
Begin Log:=TStringList.Create;Mark('START_L5_ONLY');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1590) Then Begin Mark('STOP_COUNT');Exit;End;
Ns[0]:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
While N<>Nil Do Begin If N.Name='GND' Then Ns[0]:=N;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If Ns[0]=Nil Then Exit;
ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'l5_contours.txt'}');PCBServer.PreProcess;
Try ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));P:=I.FirstPCBObject;
While P<>Nil Do Begin Good:=False;
If P.Layer=eMidLayer4 Then Begin
If P.Net<>Nil Then If P.Net.Name='GND' Then Good:=True;
RG:=P;If Pos('L5_RC_PAD_VOID_',RG.Name)=1 Then Good:=True;End;
If Good Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_L5_REGIONS='+IntToStr(ND));
{''.join(f'Update{i};' for i in range(len(batches)))}
Finally PCBServer.PostProcess;End;
Ns[0].ConnectivelyInValidate;Ns[0].Rebuild;B.ConnectivelyValidateNets;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
Mark('L5_32_CUTOUTS_COMPLETE_REQUIRES_SAVE');ContourData.Free;Log.Free;End;
'''
(H/(stem+'.pas')).write_text(header+extra+body+main,encoding='ascii')
(H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
print('Prepared 32 persistent L5 cutouts;',old.area-new.area,'mm2 copper removal; all shield lands retained')
