"""Prepare a hash-guarded local physical delta; never execute Altium here."""
from pathlib import Path
from collections import Counter
import hashlib,json,math,sys
from shapely.geometry import shape,mapping,box
from shapely.geometry.polygon import orient

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
OLD=ROOT/'script/qd38_rotation_20261011'
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
PCB=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
BASE='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
sys.path.insert(0,str(OLD))
from prepare_native_revision import quote as q,number as f,layer
from prepare_native_revision_rules import read_rules
from audit_saved_revision_surface import read_snapshot
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')

HEADER=r'''
Var B:IPCB_Board;D:IServerDocument;L:TStringList;I:IPCB_BoardIterator;
 P:IPCB_Primitive;PD:IPCB_Pad;V:IPCB_Via;T:IPCB_Track;N:IPCB_Net;
 R:IPCB_Rule;VR:IPCB_RoutingViaStyleRule;RG:IPCB_Region;G:IPCB_GeometricPolygon;CT:IPCB_Contour;
 Pads:Array[0..37] Of IPCB_Pad;Vias:Array[0..21] Of IPCB_Via;
 Dead:Array[0..10000] Of IPCB_Primitive;ND,K,Count:Integer;Good:Boolean;
Procedure Note(S:String);Begin L.Add(S);L.SaveToFile('__LOG__');End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Function Near(A:TCoord;V:Double):Boolean;Begin Result:=Abs(CoordToMMs(A)-V)<0.00001;End;
Function FindNet(S:String):IPCB_Net;
Var J:IPCB_BoardIterator;X:IPCB_Net;
Begin Result:=Nil;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(eNetObject));X:=J.FirstPCBObject;
 While X<>Nil Do Begin If X.Name=S Then Result:=X;X:=J.NextPCBObject;End;B.BoardIterator_Destroy(J);End;
Function FindPad(S:String;X,Y,A:Double):IPCB_Pad;
Var J:IPCB_BoardIterator;P:IPCB_Pad;C:Integer;
Begin Result:=Nil;C:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(ePadObject));P:=J.FirstPCBObject;
 While P<>Nil Do Begin If P.Component<>Nil Then If (P.Component.Name.Text='Q1') And (P.Name=S) Then Begin
 Inc(C);If Near(P.X,X) And Near(P.Y,Y) And Near(P.TopXSize,0.8) And Near(P.TopYSize,0.25) And (Abs(P.Rotation-A)<0.00001) And (P.Layer=eBottomLayer) Then Result:=P;
 End;P:=J.NextPCBObject;End;B.BoardIterator_Destroy(J);If C<>1 Then Result:=Nil;End;
Function FindVia(S:String;X,Y:Double):IPCB_Via;
Var J:IPCB_BoardIterator;V:IPCB_Via;C:Integer;
Begin Result:=Nil;C:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(eViaObject));V:=J.FirstPCBObject;
 While V<>Nil Do Begin If V.Net<>Nil Then If (V.Net.Name=S) And Near(V.X,X) And Near(V.Y,Y) Then Begin
 Inc(C);If Near(V.Size,0.4) And Near(V.HoleSize,0.2) And (V.LowLayer=eTopLayer) And (V.HighLayer=eBottomLayer) Then Result:=V;
 End;V:=J.NextPCBObject;End;B.BoardIterator_Destroy(J);If C<>1 Then Result:=Nil;End;
Function FindTrack(S:String;Layer:TLayer;X1,Y1,X2,Y2,W:Double):IPCB_Track;
Var J:IPCB_BoardIterator;T:IPCB_Track;C:Integer;
Begin Result:=Nil;C:=0;J:=B.BoardIterator_Create;J.SetState_FilterAll;J.AddFilter_ObjectSet(MkSet(eTrackObject));T:=J.FirstPCBObject;
 While T<>Nil Do Begin If T.Net<>Nil Then If (T.Net.Name=S) And (T.Layer=Layer) And Near(T.Width,W) Then
 If (Near(T.X1,X1) And Near(T.Y1,Y1) And Near(T.X2,X2) And Near(T.Y2,Y2)) Or (Near(T.X1,X2) And Near(T.Y1,Y2) And Near(T.X2,X1) And Near(T.Y2,Y1)) Then Begin Inc(C);Result:=T;End;
 T:=J.NextPCBObject;End;B.BoardIterator_Destroy(J);If C<>1 Then Result:=Nil;End;
Procedure Track(N:IPCB_Net;Layer:TLayer;X1,Y1,X2,Y2,W:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(W);T.Layer:=Layer;T.Net:=N;T.SetState_InNet(True);Reg(T);End;
Procedure ApplyQDPadAlignment;
Begin
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Exit;Client.ShowDocument(D);
 B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Exit;
 L:=TStringList.Create;Good:=True;ND:=0;
 Note('EXPECTED_NATIVE_SHA256=__BASE__');Note('CANDIDATE_SHA256=__CANDIDATE__');
'''

def main():
    cp=H/'alignment_full_candidate.json';ap=H/'alignment_full_audit.json'
    assert sha(PCB)==BASE and sha(H/'before_alignment'/PCB.name)==BASE
    p=read(cp);audit=read(ap);assert audit['passed'] and audit['candidate_sha256']==sha(cp)
    before=read(H/'before_alignment/full_copper_candidate.json')
    snap=read(OLD/'saved_revision_snapshot.json');assert snap['source_sha256']==BASE
    assert p['nets']==before['nets'] and p['pinmap']==before['pinmap']
    assert p['components']==before['components'] and p['arcs']==before['arcs']
    assert p['solder_openings']==before['solder_openings'] and p['shield_vias']==before['shield_vias']
    pads={x['pin']:x for x in p['physical_pads'] if x['ref']=='Q1'}
    oldpads={x['number']:x for x in snap['pads'] if x['component']=='Q1'}
    oldvias={x['label']:x for x in before['vias'] if x['label'].startswith('Q1-')}
    vias={x['label']:x for x in p['vias'] if x['label'].startswith('Q1-')}
    assert len(pads)==38 and len(vias)==22 and vias.keys()==oldvias.keys()
    internal=lambda plan,net:[x for x in plan['tracks'] if x['net']==net and x['layer'] in (2,4)]
    affected=sorted(n for n in p['nets'] if internal(p,n)!=internal(before,n))
    assert all(n.startswith('DC') for n in affected)
    for plan in (p,before):
        assert all(len({x['layer'] for x in internal(plan,n)})==1 for n in affected)
    assert [x for x in p['tracks'] if x['layer'] not in (2,4)]==[x for x in before['tracks'] if x['layer'] not in (2,4)]
    remove=[x for x in snap['tracks'] if x['net'] in affected and x['layer'] in (2,4)]
    add=[x for x in p['tracks'] if x['net'] in affected and x['layer'] in (2,4)]
    sch=read(DEST/'schematic_validation.json')
    _,regions,_,_,_=read_snapshot(PCB,sch)
    changed_layers=[int(k) for k,g in p['ground_regions'].items() if g!=before['ground_regions'][k]]
    old_regions=[x for x in regions if x['layer'] in changed_layers and x['net']=='GND' and x['name'].startswith('QD38_GND_')]
    rules=read_rules(PCB);qr=rules['QD38_QD_VIA_0P4_0P2']
    changes=[dict(name=qr['NAME'],field=k,before=qr[k],after_mm=.35) for k in ('WIDTH','MINWIDTH','MAXWIDTH')]
    manifest=dict(candidate_file=str(cp),candidate_sha256=sha(cp),inner_alignment='nearest_corner_per_side',outer_alignment='not_requested',
      qd_endpoint_via=dict(count=22,baseline_land_mm=.4,land_mm=.35,drill_mm=.2,low=1,high=32),allowed_rule_changes=changes,
      edit_region=mapping(box(5.5,36,14,49)),baseline_sha256=BASE,affected_internal_nets=affected,
      ground_layers_changed=changed_layers,manufacturer_sources=['https://jlcpcb.com/capabilities/pcb-capabilities/','https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq'])
    # All moved endpoints must remain covered by the existing net/spatial scope.
    import re
    rect=[float(x)*.0254 for x in re.search(r'InRegionAbsolute\(([^)]+)\)',qr['SCOPE1EXPRESSION']).group(1).split(',')]
    assert all(rect[0]<=v['x']<=rect[2] and rect[1]<=v['y']<=rect[3] for v in vias.values())
    lines=[HEADER]
    for i,pin in enumerate(sorted(pads,key=int)):
        b=oldpads[pin];lines += [f'Pads[{i}]:=FindPad({q(pin)},{f(b["x"])},{f(b["y"])},{f(b["rotation"])});If Pads[{i}]=Nil Then Good:=False;']
    for i,key in enumerate(sorted(vias)):
        b=oldvias[key];lines += [f'Vias[{i}]:=FindVia({q(b["net"])},{f(b["x"])},{f(b["y"])});If Vias[{i}]=Nil Then Good:=False;']
    for t in remove:
        args=','.join(f(t[k]) for k in ('x1','y1','x2','y2','width'))
        lines += [f'T:=FindTrack({q(t["net"])},{layer(t["layer"])},{args});If T=Nil Then Good:=False Else Begin Dead[ND]:=T;Inc(ND);End;']
    for rg in old_regions:
        lines += ['Count:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));RG:=I.FirstPCBObject;',
          f'While RG<>Nil Do Begin If (RG.Name={q(rg["name"])}) And (RG.Layer={layer(rg["layer"])}) Then Begin Inc(Count);Dead[ND]:=RG;Inc(ND);End;RG:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If Count<>1 Then Good:=False;']
    lines += ["VR:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRuleObject));R:=I.FirstPCBObject;While R<>Nil Do Begin If R.Name='QD38_QD_VIA_0P4_0P2' Then VR:=R;R:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);",
      "If VR=Nil Then Good:=False Else If Not(Near(VR.PreferedWidth,0.4) And Near(VR.MinWidth,0.4) And Near(VR.MaxWidth,0.4)) Then Good:=False;",
      "If Not Good Then Begin Note('STOP_GUARD');L.Free;Exit;End;Note('GUARDS_PASSED');",
      'PCBServer.PreProcess;Try']
    for i,pin in enumerate(sorted(pads,key=int)):
        v=pads[pin];b=oldpads[pin]
        if tuple(round(v[k]/2.54e-6) for k in ('x','y'))==tuple(round(b[k]/2.54e-6) for k in ('x','y')):continue
        lines += [f'PD:=Pads[{i}];PCBServer.SendMessageToRobots(PD.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);PD.X:=MMsToCoord({f(v["x"])});PD.Y:=MMsToCoord({f(v["y"])});PCBServer.SendMessageToRobots(PD.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);']
    for i,key in enumerate(sorted(vias)):
        v=vias[key];assert v['diameter']==.35 and v['hole']==.2
        lines += [f'V:=Vias[{i}];PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);V.X:=MMsToCoord({f(v["x"])});V.Y:=MMsToCoord({f(v["y"])});V.Size:=MMsToCoord(0.35);PCBServer.SendMessageToRobots(V.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);']
    lines += ['For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);']
    for n in affected:
        lines += [f'N:=FindNet({q(n)});']
        for t in add:
            if t['net']!=n:continue
            lines += [f'Track(N,{layer(t["layer"])},'+','.join(f(x) for x in [*t['a'],*t['b'],t['width']])+');']
    lines += ["N:=FindNet('GND');"]
    for ll in changed_layers:
        geo=shape(p['ground_regions'][str(ll)])
        # The surface preparation emits already simplified/quantized contours.
        polys=list(geo.geoms) if hasattr(geo,'geoms') else [geo]
        for i,poly in enumerate(polys):
            if poly.is_empty:continue
            poly=orient(poly,sign=1);assert poly.is_valid
            lines += ['G:=PCBServer.PCBGeometricPolygonFactory;']
            for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
                lines += ['CT:=PCBServer.PCBContourFactory;']
                lines += [f'CT.AddPoint(MMsToCoord({f(x)}),MMsToCoord({f(y)}));' for x,y in list(ring.coords)[:-1]]
                lines += [f'G.AddContourIsHole(CT,{str(hole)});']
            lines += [f'RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer(ll)};RG.Name:={q(f"QD38_GND_{ll}_{i}")};RG.SetGeometricPolygon(G);RG.Net:=N;RG.SetState_InNet(True);Reg(RG);']
    lines += ['PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_BeginModify,c_NoEventData);VR.MinWidth:=MMsToCoord(0.35);VR.MaxWidth:=MMsToCoord(0.35);VR.PreferedWidth:=MMsToCoord(0.35);PCBServer.SendMessageToRobots(VR.I_ObjectAddress,c_Broadcast,PCBM_EndModify,c_NoEventData);',
      'Finally PCBServer.PostProcess;End;B.InvalidateScopeTester;B.ValidateScopeTester;B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;',
      "Note('COMPLETE_NOT_SAVED');L.Free;End;"]
    code='\n'.join(lines).replace('Near(', 'CoordMatch(').replace('Procedure ApplyQDPadAlignment;', 'Procedure ApplyQDPadAlignmentR1;')
    for a,b in {'__PCB__':str(PCB),'__BASE__':BASE,'__CANDIDATE__':sha(cp),'__LOG__':str(H/'native_alignment_delta.txt')}.items():code=code.replace(a,b)
    assert '__' not in code
    stem='ApplyQDPadAlignmentR1'
    (H/f'{stem}.pas').write_text(code,encoding='ascii')
    (H/f'{stem}.PrjScr').write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
    write(H/'alignment_delta_manifest.json',manifest)
    write(H/'native_alignment_preparation.json',dict(status='PREPARED_NOT_EXECUTED',candidate_sha256=sha(cp),baseline_sha256=BASE,affected_internal_nets=affected,tracks_removed=len(remove),tracks_added=len(add),ground_regions_removed=len(old_regions),changed_ground_layers=changed_layers,script_stem=stem,script_sha256=sha(H/f'{stem}.pas')))
    print('Prepared local alignment delta:',affected,'tracks',len(remove),'->',len(add),'GND layers',changed_layers)

if __name__=='__main__':main()
