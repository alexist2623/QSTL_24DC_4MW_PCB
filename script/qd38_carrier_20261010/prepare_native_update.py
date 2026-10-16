"""Generate a guarded native update; generation does not modify the PCB."""
from pathlib import Path
import hashlib
import json
import re
import sys
from shapely.geometry import shape
from shapely.geometry.polygon import orient
from design_geometry import ROOT,H,DEST


def main():
    stem=sys.argv[1] if len(sys.argv)>1 else 'NativeUpdate'
    assert re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',stem)
    candidate=DEST/'full_copper_candidate.json'
    p=json.loads(candidate.read_text())
    # Source signal vias are through holes. Only the RF ground shields use
    # the preserved L5-to-Bottom blind span; a routing solution must not
    # manufacture extra blind constructions to avoid copper collisions.
    assert p['vias'] and all((v['low'],v['high'])==(1,32) for v in p['vias']), 'Signal via span must remain Top-to-Bottom'
    assert p['shield_vias'] and all((v['low'],v['high'])==(5,32) for v in p['shield_vias']), 'Shield via span must remain L5-to-Bottom'
    audit_path=H/'through_via_audit.json'
    assert audit_path.is_file(), 'A full-through-via copper audit is required before script generation'
    audit=json.loads(audit_path.read_text())
    assert audit.get('passed') is True, 'Full-through-via copper audit failed'
    assert audit.get('candidate_sha256')==hashlib.sha256(candidate.read_bytes()).hexdigest(), 'Through-via audit does not match this complete copper candidate'
    sch=json.loads((DEST/'schematic_validation.json').read_text())
    target=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
    provenance=json.loads((DEST/'copy_provenance.json').read_text())
    assert hashlib.sha256(target.read_bytes()).hexdigest()==provenance['source_sha256']['QSTL_24DC_4MW_PCB.PcbDoc']
    assert p['nets']==sch['nets'] and p['routing_complete']
    assert all(n==11 for n in p['surface_validation']['smp_ring_counts'].values())
    layer=lambda n:{1:'eTopLayer',2:'eMidLayer1',3:'eMidLayer2',4:'eMidLayer3',5:'eMidLayer4',32:'eBottomLayer',37:'eTopSolder',38:'eBottomSolder',59:'eMechanical3',74:'eMultiLayer'}[n]
    def quote(s):return "'"+str(s).replace("'","''")+"'"
    code=[r'''Var B:IPCB_Board;Log:TStringList;
  D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;C,J1:IPCB_Component;
  Dead:Array[0..30000] Of IPCB_Primitive;ND,K,NC:Integer;
  Cs:Array[0..49] Of IPCB_Component;Ns:Array[0..70] Of IPCB_Net;N:IPCB_Net;
  Body:IPCB_ComponentBody;Models:Array[0..2] Of IPCB_Model;M:IPCB_Model;Pt:TCoordPoint;
  PD:IPCB_Pad;V:IPCB_Via;Cache:TPadCache;G:IPCB_GeometricPolygon;CT:IPCB_Contour;RG:IPCB_Region;
  Rule:IPCB_Rule;WC:IPCB_MaxMinWidthConstraint;Good:Boolean;FabText:IPCB_Text;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\native_update_log.txt');End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Procedure Track(N:IPCB_Net;L:TLayer;X1,Y1,X2,Y2,W:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(W);T.Layer:=L;If N<>Nil Then Begin T.Net:=N;T.SetState_InNet(True);End;Reg(T);End;
Procedure FabArc(CX,CY,R,A0,A1:Double);
Var A:IPCB_Arc;
Begin A:=PCBServer.PCBObjectFactory(eArcObject,eNoDimension,eCreate_Default);A.XCenter:=MMsToCoord(CX);A.YCenter:=MMsToCoord(CY);A.Radius:=MMsToCoord(R);A.LineWidth:=MMsToCoord(0.05);A.StartAngle:=A0;A.EndAngle:=A1;A.Layer:=eMechanical3;Reg(A);End;
Procedure NativeUpdate;
Begin
 Log:=TStringList.Create;Mark('START');
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Begin Mark('NO_DOCUMENT');Exit;End;
 Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Begin Mark('NO_BOARD');Exit;End;
 If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Begin Mark('WRONG_BOARD');Exit;End;
 NC:=0;J1:=Nil;For K:=0 To 2 Do Models[K]:=Nil;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);If C.Name.Text='J1' Then J1:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If (NC<>22) Or (J1=Nil) Then Begin Mark('STOP_BASELINE_COMPONENT_COUNT');Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
 While Body<>Nil Do Begin C:=Body.Component;
  If C<>Nil Then Begin K:=-1;If C.Name.Text='R1' Then K:=0;If C.Name.Text='C1' Then K:=1;If C.Name.Text='SMP1' Then K:=2;
   If K>=0 Then Begin M:=Body.GetModel;If M<>Nil Then Models[K]:=M.I_Replicate;End;
  End;Body:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 For K:=0 To 2 Do If Models[K]=Nil Then Begin Mark('STOP_MISSING_SOURCE_MODEL');Exit;End;
 Mark('PREFLIGHT_OK');PCBServer.PreProcess;
 Try
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;
  I.AddFilter_ObjectSet(MkSet(eTrackObject,eArcObject,eFillObject,eRegionObject,eTextObject,eComponentBodyObject,eViaObject,ePadObject,ePolyObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   { Preserve the source fabrication outline on Mechanical 1. }
   Good:=(P.Component=Nil) And (P.Layer=eMechanical1) And ((P.ObjectId=eTrackObject) Or (P.ObjectId=eArcObject));
   If (P.Component<>J1) And Not Good Then Begin
    If P.ObjectId=ePadObject Then Begin PD:=P;If PD.Component<>Nil Then Begin Dead[ND]:=P;Inc(ND);End;End
    Else Begin Dead[ND]:=P;Inc(ND);End;
   End;P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
  While C<>Nil Do Begin If C<>J1 Then Begin Dead[ND]:=C;Inc(ND);End;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;
  While PD<>Nil Do Begin PD.Net:=Nil;PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
  While N<>Nil Do Begin Dead[ND]:=N;Inc(ND);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('OLD_COPPER_REMOVED');
''']
    e=code.append
    nets=list(p['nets']);nmap={n:f'Ns[{i}]' for i,n in enumerate(nets)}
    cmap={c['ref']:f'Cs[{i}]' for i,c in enumerate(p['components'])}
    for n,v in nmap.items():e(f'{v}:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);{v}.Name:={quote(n)};Reg({v});')
    for c in p['components']:
        v=cmap[c['ref']];ref=c['ref']
        if ref=='J1':e(f'{v}:=J1;')
        else:e(f'{v}:=PCBServer.PCBObjectFactory(eComponentObject,eNoDimension,eCreate_Default);{v}.Name.Text:={quote(ref)};{v}.Pattern:={quote(c["pattern"])};{v}.Layer:={layer(c["layer"])};{v}.X:=MMsToCoord({c["x"]});{v}.Y:=MMsToCoord({c["y"]});{v}.Rotation:={c["rotation"]};{v}.NameOn:=False;{v}.CommentOn:=False;Reg({v});')
        e(f'{v}.SourceUniqueId:={quote(sch["components"][ref])};')
        if ref.startswith(('SMP','R','C')):
            k=2 if ref.startswith('SMP') else 0 if ref.startswith('R') else 1
            projection='eBoardSide_Top' if c['layer']==1 else 'eBoardSide_Bottom'
            rx,dz,standoff=(90,236220,-1263780) if k==2 else (0,0,0)
            height='Body.SetOverallHeight(2125984);' if k==2 else ''
            e(f'Body:=PCBServer.PCBObjectFactory(eComponentBodyObject,eNoDimension,eCreate_Default);M:=Models[{k}].I_Replicate;Pt:=M.GetOrigin;Pt.X:=MMsToCoord({c["x"]});Pt.Y:=MMsToCoord({c["y"]});M.SetOrigin(Pt);M.SetState({rx},0,{c["rotation"]},{dz});M.SetEmbed(True);Body.SetModel(M);Body.SetState_FromModel;Body.SetBodyProjection({projection});Body.SetStandoffHeight({standoff});{height}{v}.AddPCBObject(Body);Reg(Body);Body.ValidateMesh;')
    for d in p['physical_pads']:
        n=nmap.get(d['net'],'Nil');ref=d['ref'];pin=d['pin']
        if ref=='J1':
            e(f'PD:=J1.GetState_PadByName({quote(pin)});If PD<>Nil Then Begin PD.Net:={n};PD.SetState_InNet({str(n!="Nil")});End;')
            continue
        if ref is None:
            e('I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;')
            e(f"While PD<>Nil Do Begin If (PD.Component=Nil) And (PD.Name={quote(pin)}) Then PD.Net:={n};PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);")
            continue
        shp='eRectangular' if d['shape']=='rect' else 'eRounded'
        e(f'PD:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);PD.Name:={quote(pin)};PD.X:=MMsToCoord({d["x"]});PD.Y:=MMsToCoord({d["y"]});PD.Layer:={layer(d["layer"])};PD.Mode:=ePadMode_Simple;PD.TopShape:={shp};PD.MidShape:={shp};PD.BotShape:={shp};PD.TopXSize:=MMsToCoord({d["sx"]});PD.TopYSize:=MMsToCoord({d["sy"]});PD.MidXSize:=PD.TopXSize;PD.BotXSize:=PD.TopXSize;PD.MidYSize:=PD.TopYSize;PD.BotYSize:=PD.TopYSize;PD.Rotation:={d["rotation"]};PD.HoleSize:=MMsToCoord({d["hole"]});PD.Plated:=True;PD.Net:={n};PD.SetState_InNet(True);')
        paste=ref.startswith(('R','C'))
        e(f'PD.SetState_PasteMaskEnabled({str(paste)});Cache:=PD.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord({0 if paste else -2});Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord(0.05);Cache.SolderMaskBottomExpansion:=MMsToCoord(0.05);PD.SetState_Cache(Cache);{cmap[ref]}.AddPCBObject(PD);Reg(PD);')
    for t in p['tracks']:e(f'Track({nmap[t["net"]]},{layer(t["layer"])},{t["a"][0]},{t["a"][1]},{t["b"][0]},{t["b"][1]},{t["width"]});')
    for v in p['vias']+p['shield_vias']:
        e(f'V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({v["x"]});V.Y:=MMsToCoord({v["y"]});V.Size:=MMsToCoord({v["diameter"]});V.HoleSize:=MMsToCoord({v["hole"]});V.LowLayer:={layer(v["low"])};V.HighLayer:={layer(v["high"])};V.Net:={nmap[v["net"]]};V.SetState_InNet(True);V.SetState_PasteMaskEnabled(False);Cache:=V.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord(-2);Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord(-1);Cache.SolderMaskBottomExpansion:=MMsToCoord(-1);V.SetState_Cache(Cache);Reg(V);')
    for family,regions in [('GND',p['ground_regions']),('MASK',p['solder_openings'])]:
        for ll,m in regions.items():
            g=shape(m).simplify(.001,preserve_topology=True)
            polys=list(g.geoms) if hasattr(g,'geoms') else [g]
            for i,poly in enumerate(polys):
                poly=orient(poly,sign=1);e('G:=PCBServer.PCBGeometricPolygonFactory;')
                for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
                    e('CT:=PCBServer.PCBContourFactory;')
                    for x,y in list(ring.coords)[:-1]:e(f'CT.AddPoint(MMsToCoord({x}),MMsToCoord({y}));')
                    e(f'G.AddContourIsHole(CT,{str(hole)});')
                e(f'RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer(int(ll))};RG.Name:={quote(f"QD38_{family}_{ll}_{i}")};RG.SetGeometricPolygon(G);')
                if family=='GND':e(f'RG.Net:={nmap["GND"]};RG.SetState_InNet(True);')
                e('Reg(RG);')
    # Preserve the verified source fabrication layer (Mechanical 3, code
    # 59). This is a Bottom-side blind-pocket instruction, never a cutout.
    # The tangent perimeter is 5.3 x 4.3 mm at (9.75, 42.5), with R0.5.
    for a,b in [((7.6,40.35),(11.9,40.35)),((12.4,40.85),(12.4,44.15)),
                ((11.9,44.65),(7.6,44.65)),((7.1,44.15),(7.1,40.85))]:
        e(f'Track(Nil,eMechanical3,{a[0]},{a[1]},{b[0]},{b[1]},0.05);')
    for cx,cy,a0,a1 in [(11.9,40.85,270,360),(11.9,44.15,0,90),
                        (7.6,44.15,90,180),(7.6,40.85,180,270)]:
        e(f'FabArc({cx},{cy},0.5,{a0},{a1});')
    e("FabText:=PCBServer.PCBObjectFactory(eTextObject,eNoDimension,eCreate_Default);FabText.Layer:=eMechanical3;FabText.MoveToXY(MMsToCoord(21),MMsToCoord(43));FabText.Size:=MMsToCoord(0.8);FabText.Width:=MMsToCoord(0.12);FabText.Text:='BOTTOM BLIND POCKET: 5.3 x 4.3 mm, R0.5, DEPTH 1.2 mm FROM BOTTOM; NON-PLATED; NON-THROUGH';Reg(FabText);")
    e("B.RebuildPadCaches;Mark('GEOMETRY_CREATED');Finally PCBServer.PostProcess;End;")
    e("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;")
    e("B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;Mark('BUILT_NOT_SAVED_REVIEW_RULES_AND_MODELS');Log.Free;End;")
    # The first application deliberately leaves the document unsaved for
    # native inspection and scope updates. It never invokes a fabrication job.
    # Split long generated geometry into bounded subprocedures. Shared
    # construction variables intentionally retain an in-progress contour
    # between consecutive batches; each emitted statement is complete.
    header,preflight=code[0].split('Procedure NativeUpdate;\n',1)
    generated=code[1:-3]
    batches=[generated[i:i+250] for i in range(0,len(generated),250)]
    procedures=[];calls=[]
    for i,batch in enumerate(batches):
        name=f'BuildGeometry{i:03}'
        procedures.append(f'Procedure {name};\nBegin\n'+ '\n'.join(batch)+'\nEnd;')
        calls.append(name+';')
    text='\n'.join([header]+procedures+['Procedure NativeUpdate;',preflight]+calls+code[-3:])
    text=text.replace('__H__',str(H)).replace('__PCB__',str(target))
    text=re.sub(r'(?<![\w.])\.(\d)',r'0.\1',text)
    text=text.replace('Procedure NativeUpdate;',f'Procedure {stem};')
    (H/f'{stem}.pas').write_text(text,encoding='ascii')
    (H/f'{stem}.PrjScr').write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
    print(json.dumps(dict(prepared_bytes=len(text),components=50,signal_vias=len(p['vias']),shield_vias=len(p['shield_vias']),
                         geometry_batches=len(batches),status='SCRIPT_PREPARED_NOT_EXECUTED',native_pcb_modified=False),indent=2))


if __name__=='__main__':main()
