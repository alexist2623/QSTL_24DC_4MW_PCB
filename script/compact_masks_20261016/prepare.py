"""Prepare a mask-only native revision from the saved sixteen-RF PCB."""
from pathlib import Path
import sys,json,hashlib,shutil
from shapely.geometry import Point,box,shape,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/smp_broad_rounding_20261016'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
from audit_saved_revision_surface import read_snapshot
import native_constructors as nc
pcb=P/(P.name+'.PcbDoc');digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
repair='--repair-slivers' in sys.argv
assert digest==('b916d82d8781786f0029128ab0af41a247a14f659dd2691ffabc31a778c757a1' if repair else 'cc4b516bb2a595396ce22cec023afa5312c15f7b7ff8f72017cb110756e87819'),digest
bk=H/'baseline';bk.mkdir(exist_ok=True)
for src in [pcb,P/(P.name+'.SchDoc'),P/'pin_mapping.csv',OLD/'candidate.json']:
    dst=bk/src.name
    if dst.exists():assert (repair and src==pcb) or dst.read_bytes()==src.read_bytes()
    else:shutil.copy2(src,dst)
for name in ['dispatch.py','audit_saved.py','audit_support.py','audit_mask_cam.py','ValidateNative16RF.pas','ValidateNative16RF.PrjScr','ExportCapPaste.pas','ExportCapPaste.PrjScr']:
    s=(OLD/name).read_text().replace('smp_broad_rounding_20261016','compact_masks_20261016').replace('SMP_Rounded_Entries_20261016','Compact_Masks_20261016').replace('Top: QD via frame and exposed centre','Top: local via covers and exposed centre')
    (H/name).write_text(s)
cam=H/'paste_verification';cam.mkdir(exist_ok=True)
(cam/'Cap_Paste_Verification.OutJob').write_text((OLD/'paste_verification/Cap_Paste_Verification.OutJob').read_text().replace('smp_broad_rounding_20261016','compact_masks_20261016'))
(P/'Compact_Masks_20261016').mkdir(exist_ok=True)
plan=json.loads((OLD/'candidate.json').read_text())
pads,regions,tracks,vias,outline=read_snapshot(bk/pcb.name,json.loads((P/'schematic_validation.json').read_text()))
old_open={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll]) for ll in (37,38)}
field=shape(plan['qd_mask_field']);cx,cy=plan['sample_center'];centre=box(cx-2.15,cy-2.65,cx+2.15,cy+2.65)
mount=unary_union([p['geometry'].buffer(.1) for p in pads if p['ref'] is None])
smp=[unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull.buffer(.3,quad_segs=32) for ref in sorted({p['ref'] for p in pads if p['ref'] and p['ref'].startswith('SMP')})]
rc={ref:unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull.buffer(.2,join_style='mitre') for ref in sorted({p['ref'] for p in pads if p['ref'] and p['ref'][0] in 'RC'})}
zv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in plan['vias'] if v['label'].startswith('J1-')])
zt=box(*unary_union([zv]+[p['geometry'] for p in pads if p['ref']=='J1']).bounds).buffer(.3,join_style='mitre');zb=box(*zv.bounds).buffer(.4,join_style='mitre')
local_top={v['label']:Point(v['x'],v['y']).buffer(v['diameter']/2+.15,quad_segs=96) for v in plan['vias'] if not v['label'].startswith('J1-')}
assert len(rc)==32 and len(local_top)==38
local_bottom=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2+.15,quad_segs=64) for v in vias])
rf=unary_union([t['geometry'] for t in tracks if t['layer']==32 and t['net'] and t['net'].startswith(('S','MW'))]).buffer(.71,quad_segs=96)
extent=outline.buffer(.05,join_style='mitre')
keep_top=unary_union(smp+[zt]+list(local_top.values())).difference(centre)
keep_bottom=unary_union(smp+[zb,rf,local_bottom]+list(rc.values())).difference(field)
opening={37:extent.difference(keep_top).union(mount).union(centre),38:extent.difference(keep_bottom).union(mount).union(field)}
repairs=[]
if repair:
    # Increase only the four narrow mask bridges identified by native DRC.
    # Shrink nearby general openings rather than expose any protected RF/via.
    parts=sorted(opening[38].geoms,key=lambda p:-p.area)
    locked=field.union(mount)
    for i in range(len(parts)):
        for j in range(i+1,len(parts)):
            gap=parts[i].distance(parts[j])
            if gap>=.12:continue
            cut=parts[j].intersection(parts[i].buffer(.12,quad_segs=96))
            if cut.intersection(locked).area<1e-10:
                parts[j]=parts[j].difference(parts[i].buffer(.12,quad_segs=96))
            else:
                cut=parts[i].intersection(parts[j].buffer(.12,quad_segs=96))
                assert cut.intersection(locked).area<1e-10
                parts[i]=parts[i].difference(parts[j].buffer(.12,quad_segs=96))
            repairs.append(dict(previous_gap_mm=gap,added_mask_area_mm2=cut.area))
    opening[38]=unary_union(parts)
    assert locked.difference(opening[38]).area<1e-8
plan['solder_openings']={str(k):mapping(g) for k,g in opening.items()}
plan['compact_mask_spec']=dict(RC_pad_hull_margin_mm=.2,local_via_land_margin_mm=.15,RF_centreline_strip_half_width_mm=.71,RC_contours={k:mapping(v) for k,v in rc.items()},Top_local_via_contours={k:mapping(v) for k,v in local_top.items()},Top_ZIF=mapping(zt),Bottom_ZIF=mapping(zb),SMP=[mapping(g) for g in smp],Bottom_via_contours=mapping(local_bottom),RF_protection=mapping(rf))
(H/'candidate.json').write_text(json.dumps(plan,indent=2))
audit=dict(before_sha256=hashlib.sha256((bk/pcb.name).read_bytes()).hexdigest(),applied_over_sha256=digest,RC_footprints=len(rc),Top_local_vias=len(local_top),local_sliver_repairs=repairs,mask_area_mm2={str(ll):dict(before=outline.difference(old_open[ll]).area,after=outline.difference(opening[ll]).area) for ll in (37,38)})
for ll in (37,38):
    a=audit['mask_area_mm2'][str(ll)];a['reduction_percent']=100*(1-a['after']/a['before'])
assert centre.difference(opening[37]).area<1e-8 and field.difference(opening[38]).area<1e-8
(H/'preparation_audit.json').write_text(json.dumps(audit,indent=2))
stm=[];contours=[]
for ll,g in opening.items():
    g=g.simplify(.0002,preserve_topology=True)
    for i,poly in enumerate(g.geoms if hasattr(g,'geoms') else [g]):
        poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
        for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
            xy=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in xy)
            stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(xy)});',f'G.AddContourIsHole(CT,{hole});'])
        stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={'eTopSolder' if ll==37 else 'eBottomSolder'};RG.Name:='COMPACT_MASK_OPEN_{ll}_{i}';RG.SetGeometricPolygon(G);Reg(RG);")
(H/'mask_contours.txt').write_text('\n'.join(contours))
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'apply_log.txt')).replace('Good:Boolean;','ContourData:TStringList;Good:Boolean;')
extra="""Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
"""
batches=[stm[i:i+100] for i in range(0,len(stm),100)]
body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches))
stem='ApplyCompactMasks'
main=f"""Procedure {stem};
Begin Log:=TStringList.Create;Mark('START_MASK_ONLY');
D:=Client.OpenDocument('PCB','{pcb}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{pcb}') Then Exit;
If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1590) Then Begin Mark('STOP_COUNT');Exit;End;
ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'mask_contours.txt'}');PCBServer.PreProcess;
Try ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));P:=I.FirstPCBObject;
While P<>Nil Do Begin
If (P.Layer=eTopSolder) Or (P.Layer=eBottomSolder) Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_MASK_REGIONS='+IntToStr(ND));
{''.join(f'Update{i};' for i in range(len(batches)))}
Finally PCBServer.PostProcess;End;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
Mark('COMPLETE_REQUIRES_SAVE');ContourData.Free;Log.Free;End;
"""
(H/(stem+'.pas')).write_text(header+extra+body+main,encoding='ascii')
(H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
print(json.dumps(audit,indent=2))
