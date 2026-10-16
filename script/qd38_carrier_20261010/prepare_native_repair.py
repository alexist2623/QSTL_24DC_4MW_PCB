"""Replace candidate GND regions and explicitly assign all J1 pad membership."""
from pathlib import Path
import hashlib
import json
from shapely.geometry import shape
from shapely.geometry.polygon import orient

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'

def main():
    candidate=DEST/'full_copper_candidate.json'
    p=json.loads(candidate.read_text())
    audit=json.loads((H/'through_via_audit.json').read_text())
    assert audit['passed'] and audit['candidate_sha256']==hashlib.sha256(candidate.read_bytes()).hexdigest()
    layer={1:'eTopLayer',2:'eMidLayer1',3:'eMidLayer2',4:'eMidLayer3',5:'eMidLayer4',32:'eBottomLayer',37:'eTopSolder',38:'eBottomSolder'}
    def q(s):return "'"+str(s).replace("'","''")+"'"
    header=r'''Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;C,J1:IPCB_Component;
 RG:IPCB_Region;G:IPCB_GeometricPolygon;CT:IPCB_Contour;PD:IPCB_Pad;N,Gnd:IPCB_Net;V:IPCB_Via;Cache:TPadCache;
 Dead:Array[0..3000] Of IPCB_Primitive;ND,K,NC:Integer;Log:TStringList;T:IPCB_Track;
 Body:IPCB_ComponentBody;M:IPCB_Model;Pt:TCoordPoint;CX,CY:Double;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__H__\native_repair_log.txt');End;
Function FindNet(S:String):IPCB_Net;
Var NI:IPCB_BoardIterator;NN:IPCB_Net;
Begin Result:=Nil;NI:=B.BoardIterator_Create;NI.SetState_FilterAll;NI.AddFilter_ObjectSet(MkSet(eNetObject));NN:=NI.FirstPCBObject;
 While NN<>Nil Do Begin If NN.Name=S Then Result:=NN;NN:=NI.NextPCBObject;End;B.BoardIterator_Destroy(NI);End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Procedure CapPosition(S:String;X,Y:Double);
Var CI:IPCB_BoardIterator;CP:IPCB_Component;
Begin CI:=B.BoardIterator_Create;CI.SetState_FilterAll;CI.AddFilter_ObjectSet(MkSet(eComponentObject));CP:=CI.FirstPCBObject;
 While CP<>Nil Do Begin If CP.Name.Text=S Then Begin CP.MoveToXY(MMsToCoord(X),MMsToCoord(Y));End;CP:=CI.NextPCBObject;End;B.BoardIterator_Destroy(CI);End;
Procedure CapPad(S,Pin:String;X,Y:Double);
Var PI:IPCB_BoardIterator;PP:IPCB_Pad;
Begin PI:=B.BoardIterator_Create;PI.SetState_FilterAll;PI.AddFilter_ObjectSet(MkSet(ePadObject));PP:=PI.FirstPCBObject;
 While PP<>Nil Do Begin If PP.Component<>Nil Then If (PP.Component.Name.Text=S) And (PP.Name=Pin) Then Begin PP.X:=MMsToCoord(X);PP.Y:=MMsToCoord(Y);End;PP:=PI.NextPCBObject;End;B.BoardIterator_Destroy(PI);End;
'''
    lines=[]
    for c in p['components']:
        if c['ref'].startswith('C'):lines.append(f'CapPosition({q(c["ref"])},{c["x"]},{c["y"]});')
    for d in p['physical_pads']:
        if d['ref'] and d['ref'].startswith('C'):lines.append(f'CapPad({q(d["ref"])},{q(d["pin"])},{d["x"]},{d["y"]});')
    lines.append("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;")
    lines.append("While Body<>Nil Do Begin C:=Body.Component;If C<>Nil Then If Copy(C.Name.Text,1,1)='C' Then Begin M:=Body.GetModel;M:=M.I_Replicate;Pt:=M.GetOrigin;Pt.X:=C.X;Pt.Y:=C.Y;M.SetOrigin(Pt);Body.SetModel(M);Body.SetState_FromModel;Body.ValidateMesh;End;Body:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);")
    for t in p['tracks']:
        if t['layer']!=32 or not t['net'].startswith(('S','MW')):continue
        lines.append(f'T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord({t["a"][0]});T.Y1:=MMsToCoord({t["a"][1]});T.X2:=MMsToCoord({t["b"][0]});T.Y2:=MMsToCoord({t["b"][1]});T.Width:=MMsToCoord({t["width"]});T.Layer:=eBottomLayer;T.Net:=FindNet({q(t["net"])});T.SetState_InNet(True);Reg(T);')
    for d in p['physical_pads']:
        if d['ref']!='J1':continue
        net='Nil' if not d['net'] else 'FindNet('+q(d['net'])+')'
        lines.append(f'PD:=J1.GetState_PadByName({q(d["pin"])});If PD<>Nil Then Begin PD.Net:={net};PD.SetState_InNet({str(bool(d["net"]))});End;')
    for v in p['shield_vias']:
        lines.append(f'V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({v["x"]});V.Y:=MMsToCoord({v["y"]});V.Size:=MMsToCoord({v["diameter"]});V.HoleSize:=MMsToCoord({v["hole"]});V.LowLayer:=eMidLayer4;V.HighLayer:=eBottomLayer;V.Net:=Gnd;V.SetState_InNet(True);V.SetState_PasteMaskEnabled(False);Cache:=V.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord(-2);Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord(-1);Cache.SolderMaskBottomExpansion:=MMsToCoord(-1);V.SetState_Cache(Cache);Reg(V);')
    for family,ll,m in [(f,l,m) for f,rs in [('GND',p['ground_regions']),('MASK',p['solder_openings'])] for l,m in rs.items()]:
        g=shape(m).simplify(.001,preserve_topology=True)
        polys=list(g.geoms) if hasattr(g,'geoms') else [g]
        for i,poly in enumerate(polys):
            poly=orient(poly,sign=1);lines.append('G:=PCBServer.PCBGeometricPolygonFactory;')
            for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
                lines.append('CT:=PCBServer.PCBContourFactory;')
                for x,y in list(ring.coords)[:-1]:lines.append(f'CT.AddPoint(MMsToCoord({x}),MMsToCoord({y}));')
                lines.append(f'G.AddContourIsHole(CT,{str(hole)});')
            net='RG.Net:=Gnd;RG.SetState_InNet(True);' if family=='GND' else ''
            lines.append(f'RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer[int(ll)]};RG.Name:={q(f"QD38_{family}_{ll}_{i}")};RG.SetGeometricPolygon(G);{net}Reg(RG);')
    batches=[lines[i:i+250] for i in range(0,len(lines),250)]
    procs=[];calls=[]
    for i,batch in enumerate(batches):
        name=f'RepairBatch{i:03}';procs.append(f'Procedure {name};\nBegin\n'+'\n'.join(batch)+'\nEnd;');calls.append(name+';')
    main=r'''Procedure RepairNativeQD38;
Begin
 Log:=TStringList.Create;Mark('START');
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Exit;
 NC:=0;J1:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin Inc(NC);If C.Name.Text='J1' Then J1:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Gnd:=FindNet('GND');If (NC<>50) Or (J1=Nil) Or (Gnd=Nil) Then Begin Mark('STOP_PREFLIGHT');Exit;End;
 PCBServer.PreProcess;Try
 ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));RG:=I.FirstPCBObject;
 While RG<>Nil Do Begin If Copy(RG.Name,1,5)='QD38_' Then Begin Dead[ND]:=RG;Inc(ND);End;RG:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If ND=0 Then Begin Mark('NO_GND_REGIONS');Exit;End;
 For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_GND='+IntToStr(ND));
 ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin If V.Net<>Nil Then If V.Net.Name='GND' Then Begin Dead[ND]:=V;Inc(ND);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_SHIELDS='+IntToStr(ND));
 ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject));T:=I.FirstPCBObject;
 While T<>Nil Do Begin If (T.Layer=eBottomLayer) And (T.Net<>Nil) Then If (Copy(T.Net.Name,1,1)='S') Or (Copy(T.Net.Name,1,2)='MW') Then Begin Dead[ND]:=T;Inc(ND);End;T:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_RF_TRACKS='+IntToStr(ND));
 __CALLS__
 B.RebuildPadCaches;
 Finally PCBServer.PostProcess;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 Mark('COMPLETE_NOT_SAVED');Log.Free;
End;
'''
    code=header+'\n'.join(procs)+main.replace('__CALLS__','\n'.join(calls))
    code=code.replace('__H__',str(H)).replace('__PCB__',str(DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'))
    (H/'RepairNativeQD38.pas').write_text(code,encoding='ascii')
    (H/'RepairNativeQD38.PrjScr').write_text('[Design]\nVersion=1.0\n[Document1]\nDocumentPath=RepairNativeQD38.pas\n[Generic_ScriptingSystem]\nStartProcName=RepairNativeQD38.pas>RepairNativeQD38\n')
    print(json.dumps(dict(bytes=len(code),batches=len(batches),status='PREPARED_NOT_RUN')))

if __name__=='__main__':main()
