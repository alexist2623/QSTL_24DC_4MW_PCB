"""Restore rotated C/R solder-control margins without changing copper or Top."""
from pathlib import Path
import json,sys,hashlib,shutil
from shapely.geometry import shape,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
OLD=ROOT/'script/bond_pad_width_20261016';COMPACT=ROOT/'script/compact_masks_20261016'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
from audit_saved_revision_surface import read_snapshot
import native_constructors as nc
pcb=P/(P.name+'.PcbDoc');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pcb)=='5a5d3a83e164647765685761dfe95143e4bacdde0b8763a326cdc1eebfc5e8ac'
bk=H/'baseline';bk.mkdir(exist_ok=True)
for src in [pcb,P/(P.name+'.SchDoc'),P/'pin_mapping.csv']:
    dst=bk/src.name
    if dst.exists():assert sha(dst)==sha(src)
    else:shutil.copy2(src,dst)
for name in ['dispatch.py','audit_saved.py','audit_support.py','audit_mask_cam.py','ValidateNative16RF.pas','ValidateNative16RF.PrjScr','ExportCapPaste.pas','ExportCapPaste.PrjScr']:
    s=(OLD/name).read_text(encoding='utf-8').replace('bond_pad_width_20261016',H.name).replace('Bond_Pad_Width_20261017','RC_Mask_Margin_20261017')
    (H/name).write_text(s,encoding='utf-8')
cam=H/'paste_verification';cam.mkdir(exist_ok=True)
(cam/'Cap_Paste_Verification.OutJob').write_text((OLD/'paste_verification/Cap_Paste_Verification.OutJob').read_text(encoding='utf-8').replace('bond_pad_width_20261016',H.name),encoding='utf-8')
OUT=P/'RC_Mask_Margin_20261017';OUT.mkdir(exist_ok=True)
for name in ['audit_compact.py','render_review.py']:
    s=(COMPACT/name).read_text(encoding='utf-8').replace('Compact_Masks_20261016',OUT.name)
    if name=='audit_compact.py':s=s.replace("not in (37,38)","not in (38,)")
    if name=='render_review.py':
        s=s.replace('Compact solder mask | actual saved PCB / native CAM','Restored C/R solder-control margins | saved PCB / native CAM')
        s=s.replace('C/R pad-hull margin 0.20 mm','C/R pad-hull margin 0.20 -> 0.90 mm')
        s=s.replace("('Before | component face','After | component face','Before | opposite face','After | opposite face')","('Before | 0.20 mm margin','After | 0.90 mm margin','Before | opposite face','After | opposite face unchanged')")
    (H/name).write_text(s,encoding='utf-8')
shutil.copy2(COMPACT/'model_alignment_before.json',H/'model_alignment_before.json')
plan=json.loads((OLD/'candidate.json').read_text(encoding='utf-8'))
pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
old={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll]) for ll in (37,38)}
rc={ref:unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull.buffer(.9,join_style='mitre') for ref in plan['compact_mask_spec']['RC_contours']}
field=shape(plan['qd_mask_field']);mount=unary_union([p['geometry'].buffer(.1) for p in pads if p['ref'] is None]);locked=field.union(mount)
opening=old[38].difference(unary_union(list(rc.values()))).union(locked)
# Preserve exposed mounting/bond fields, and repair any newly narrow bridges
# by reducing only general openings. Do not reduce protective coverage.
parts=sorted(opening.geoms if hasattr(opening,'geoms') else [opening],key=lambda p:-p.area);repairs=[]
for i in range(len(parts)):
    for j in range(i+1,len(parts)):
        gap=parts[i].distance(parts[j])
        if gap>=.12:continue
        cut=parts[j].intersection(parts[i].buffer(.12,quad_segs=96))
        if cut.intersection(locked).area<1e-10:parts[j]=parts[j].difference(parts[i].buffer(.12,quad_segs=96))
        else:
            cut=parts[i].intersection(parts[j].buffer(.12,quad_segs=96));assert cut.intersection(locked).area<1e-10
            parts[i]=parts[i].difference(parts[j].buffer(.12,quad_segs=96))
        repairs.append(dict(before_gap_mm=gap,added_mask_mm2=cut.area))
opening=unary_union(parts);assert locked.difference(opening).area<1e-8
plan['solder_openings']['38']=mapping(opening)
plan['compact_mask_spec']['RC_pad_hull_margin_mm']=.9
plan['compact_mask_spec']['RC_contours']={r:mapping(g) for r,g in rc.items()}
(H/'candidate.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
audit=dict(before_sha256=sha(pcb),RC_footprints=len(rc),before_margin_mm=.2,after_margin_mm=.9,Top_unchanged=True,local_sliver_repairs=repairs,Bottom_mask_area_before_mm2=outline.difference(old[38]).area,Bottom_mask_area_after_mm2=outline.difference(opening).area)
(H/'preparation_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
stm=[];contours=[];g=opening.simplify(.0002,preserve_topology=True)
for i,poly in enumerate(g.geoms if hasattr(g,'geoms') else [g]):
    poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
    for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
        xy=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in xy)
        stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(xy)});',f'G.AddContourIsHole(CT,{hole});'])
    stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:=eBottomSolder;RG.Name:='RC_MARGIN_MASK_38_{i}';RG.SetGeometricPolygon(G);Reg(RG);")
(H/'mask_contours.txt').write_text('\n'.join(contours),encoding='ascii')
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'apply_log.txt')).replace('Good:Boolean;','ContourData:TStringList;Good:Boolean;')
extra="""Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
"""
batches=[stm[i:i+100] for i in range(0,len(stm),100)];body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches));stem='RestoreRCMaskMargin'
main=f"""Procedure {stem};
Begin Log:=TStringList.Create;Mark('START_BOTTOM_MASK_ONLY');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1590) Then Begin Mark('STOP_COUNT');Exit;End;
ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'mask_contours.txt'}');PCBServer.PreProcess;
Try ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));P:=I.FirstPCBObject;
While P<>Nil Do Begin If P.Layer=eBottomSolder Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_BOTTOM_MASK_REGIONS='+IntToStr(ND));
{''.join(f'Update{i};' for i in range(len(batches)))}
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
Mark('COMPLETE_REQUIRES_SAVE');ContourData.Free;Log.Free;End;
"""
(H/(stem+'.pas')).write_text(header+extra+body+main,encoding='ascii')
(H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
print(json.dumps(audit,indent=2))
