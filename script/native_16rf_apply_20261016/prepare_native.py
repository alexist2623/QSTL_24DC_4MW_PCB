"""Generate guarded Altium scripts for the accepted native implementation."""
from pathlib import Path
import sys,json,re,types,hashlib,shutil,configparser
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD';NAME='QSTL_QD4_2SET_38PAD'
OLD=ROOT/'script/qd38_rotation_20261011';sys.path.insert(0,str(OLD))
source=(OLD/'prepare_native_revision.py').read_text()
# Reuse proven native constructors, with explicit differences for this revision:
# mounts and outline are replaced, J1 is translated, and the new OEM C1206 STEP
# is preloaded before any old geometry is removed.
source=source.replace('if family(ref) in ("R", "C")','if ref and family(ref) in ("R", "C")')
a=source.index('        if ref is None:\n',source.index('def geometry_lines'))
b=source.index('        shp =',a);source=source[:a]+source[b:]
source=source.replace('paste = family(ref) in ("R", "C")','paste = ref is not None and family(ref) in ("R", "C")')
source=source.replace('{cmap[ref]}.AddPCBObject(PD);Reg(PD);','{cmap[ref]+".AddPCBObject(PD);" if ref else ""}Reg(PD);')
source=source.replace('shape(mapping).simplify(.001, preserve_topology=True)','shape(mapping).simplify(.0002, preserve_topology=True)')
source=source.replace('projection = "eBoardSide_Top" if comp["layer"] == 1 else "eBoardSide_Bottom"','projection = "eBoardSide_Top" if model["board_projection"] == 0 else "eBoardSide_Bottom"')
source=source.replace('Good:Boolean;FabText:IPCB_Text;','Good:Boolean;FabText:IPCB_Text;O:IPCB_BoardOutline;Seg:TPolySegment;WS:IWorkspace;Proj:IProject;LS:IPCB_LayerStack_V7;LO:IPCB_LayerObject_V7;')
source=source.replace("If C.Name.Text='C02' Then K:=1;", "If C.Name.Text='C02' Then K:=1;")
step=ROOT/'script/cap_1206_apply_20261014/native_prep/CC1206JKNPO9BN104_OEM_MAX_Centered.step'
source=source.replace('If K>=0 Then Begin M:=Body.GetModel;If M<>Nil Then Models[K]:=M.I_Replicate;End;',f"If K>=0 Then Begin If K=1 Then Models[K]:=Body.ModelFactory_FromFilename('{step}',True) Else Begin M:=Body.GetModel;If M<>Nil Then Models[K]:=M.I_Replicate;End;End;")
old="""   Good:=(P.Component=Nil) And (P.Layer=eMechanical1) And ((P.ObjectId=eTrackObject) Or (P.ObjectId=eArcObject));
   If (P.Component<>J1) And Not Good Then Begin
    If P.ObjectId=ePadObject Then Begin PD:=P;If PD.Component<>Nil Then Begin Dead[ND]:=P;Inc(ND);End;End
    Else Begin Dead[ND]:=P;Inc(ND);End;
   End;P:=I.NextPCBObject;"""
new="""   If P.Component<>J1 Then Begin Dead[ND]:=P;Inc(ND);End;
   P:=I.NextPCBObject;"""
assert old in source;source=source.replace(old,new)
source=source.replace(" D:=Client.OpenDocument('PCB','__PCB__');",f" WS:=GetWorkspace;WS.DM_OpenProject('{DEST/(NAME+'.PrjPcb')}',True);Proj:=WS.DM_GetProjectFromPath('{DEST/(NAME+'.PrjPcb')}');If Proj=Nil Then Begin Mark('NO_PROJECT');Exit;End;Proj.DM_SetAsCurrentProject;\n D:=Client.OpenDocument('PCB','__PCB__');")
mod=types.ModuleType('current_native');mod.__file__=str(HERE/'native_constructors.py');exec(compile(source,str(HERE/'native_constructors.py'),'exec'),mod.__dict__)
mod.HERE=HERE;mod.TARGET=DEST/(NAME+'.PcbDoc')
plan=json.loads((HERE/'candidate.json').read_text());audit=json.loads((HERE/'preparation_audit.json').read_text());assert not audit['uncovered_shield_lands'];assert audit['shield_hole_to_RF_mm']>=.33
sch=json.loads((HERE/'schematic_validation.json').read_text());previous=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
assert mod.sha(mod.TARGET)==previous['source_sha256']
models={m['component']:m for m in json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_models.json').read_text())['models']}
ms={k:dict(models[r]) for k,r in [('R','R02'),('C','C02'),('SMP','SMP02')]}
ms['C'].update(rotation_xyz_deg=[0,0,0],dz_mm=0,standoff_mm=0,overall_height_mm=1.8)
oldgeom=mod.geometry_lines
def geometry(plan,sch,models):
    pre=[f"J1.MoveToXY(MMsToCoord({plan['components'][1]['x']}),MMsToCoord({plan['components'][1]['y']}));"]
    pre+=['LS:=B.LayerStack_V7;LO:=LS.FirstLayer;While LO<>Nil Do Begin',"If LO.LayerID=eMidLayer2 Then LO.Name:='L3_DC_B';If LO.LayerID=eMidLayer3 Then LO.Name:='L4_GND';LO:=LS.NextLayer(LO);End;"]
    pre+=['O:=B.BoardOutline;O.PointCount:=4;Seg:=O.Segments[0];']
    for i,(x,y) in enumerate(plan['board_outline']):pre.append(f'Seg.Kind:=ePolySegmentLine;Seg.vx:=MMsToCoord({x});Seg.vy:=MMsToCoord({y});O.Segments[{i}]:=Seg;')
    pre+=['O.Segments[4]:=O.Segments[0];O.Invalidate;O.Rebuild;O.Validate;B.UpdateBoardOutline;B.RebuildSplitBoardRegions(True);']
    for a,b in zip(plan['board_outline'],plan['board_outline'][1:]+plan['board_outline'][:1]):pre.append('Track(Nil,eMechanical1,'+','.join(str(v) for v in (*a,*b,.05))+');')
    return pre+oldgeom(plan,sch,models)
mod.geometry_lines=geometry
stem='ApplyNative16RF';code,batches=mod.generate(plan,sch,previous,ms,stem,mod.sha(HERE/'candidate.json'))
(HERE/'native_constructors.py').write_text(source)
(HERE/(stem+'.pas')).write_text(code,encoding='ascii')
def project(stem):
    (HERE/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
project(stem)
# Prepare validation separately; the apply script intentionally leaves an
# unsaved document for native geometry inspection before save/reopen and DRC.
validation=(OLD/'ValidateQD90Revision.pas').read_text().replace(str(OLD),str(HERE)).replace('ValidateQD90Revision','ValidateNative16RF')
(HERE/'ValidateNative16RF.pas').write_text(validation,encoding='ascii');project('ValidateNative16RF')
print(json.dumps(dict(prepared=True,batches=batches,bytes=len(code),counts=audit['counts']),indent=2))
