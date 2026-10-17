"""Prepare a guarded RF-only edit of the existing project-owned PCB."""
from pathlib import Path
import sys,json,hashlib,shutil
from shapely.geometry import shape
from shapely.geometry.polygon import orient
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N='QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/native_16rf_apply_20261016'
sys.path[:0]=[str(OLD),str(ROOT/'script/qd38_rotation_20261011')]
import native_constructors as nc
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
assert sha(P/(N+'.PcbDoc'))==sha(H/'before_c13_rounding'/(N+'.PcbDoc'))
p=json.loads((H/'candidate.json').read_text());assert json.loads((H/'preparation_audit.json').read_text())['passed']
assert json.loads((H/'fitted_copper_audit.json').read_text())['passed']
nmap={n:f'Ns[{i}]' for i,n in enumerate(p['nets'])};stm=[];contours=[]
for t in p['tracks']:
    if t['layer']==32:stm.append(f"Track({nmap[t['net']]},eBottomLayer,"+','.join(nc.number(v) for v in (*t['a'],*t['b'],t['width']))+');')
for a in p['arcs']:stm.append(f"SignalArc({nmap[a['net']]},eBottomLayer,"+','.join(nc.number(a[k]) for k in ('cx','cy','radius','start_angle','end_angle','width'))+');')
for v in p['shield_vias']:
    x,y=nc.number(v['x']),nc.number(v['y'])
    stm.append(f"V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({x});V.Y:=MMsToCoord({y});V.Size:=MMsToCoord(0.25);V.HoleSize:=MMsToCoord(0.10);V.LowLayer:=eMidLayer4;V.HighLayer:=eBottomLayer;V.Net:={nmap['GND']};V.SetState_InNet(True);V.SetState_PasteMaskEnabled(False);Cache:=V.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord(-2);Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord(-1);Cache.SolderMaskBottomExpansion:=MMsToCoord(-1);V.SetState_Cache(Cache);Reg(V);")
for kind,bank in [('GND',{k:p['ground_regions'][k] for k in ('5','32')}),('MASK',{'38':p['solder_openings']['38']})]:
    for ll,geom in bank.items():
        geo=shape(geom).simplify(.0002,preserve_topology=True)
        for i,poly in enumerate(list(geo.geoms) if hasattr(geo,'geoms') else [geo]):
            poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
            for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
                coords=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in coords)
                stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(coords)});',f'G.AddContourIsHole(CT,{hole});'])
            stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={nc.layer(ll)};RG.Name:='RF_ENTRY_{kind}_{ll}_{i}';RG.SetGeometricPolygon(G);")
            if kind=='GND':stm.append(f"RG.Net:={nmap['GND']};RG.SetState_InNet(True);")
            stm.append('Reg(RG);')
(H/'contours.txt').write_text('\n'.join(contours))
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'apply_log.txt')).replace('Good:Boolean;', 'ContourData:TStringList;Good:Boolean;')
header=header.replace('(Abs(CP.Rotation-R)<0.00001)','((Abs(CP.Rotation-R)<0.00001) Or (Abs(Abs(CP.Rotation-R)-360)<0.00001))')
extra='''Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
'''
batches=[stm[i:i+140] for i in range(0,len(stm),140)]
body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches))
binds='\n'.join(f"If N.Name='{name}' Then {v}:=N;" for name,v in nmap.items())
guards='\n'.join(f"If Not ComponentMatches('{c['ref']}',{nc.number(c['x'])},{nc.number(c['y'])},{nc.number(c['rotation'])}) Then Begin Mark('STOP_COMPONENT_{c['ref']}');Exit;End;" for c in p['components'])
stem='ApplyRFEntryFix'
main=f'''Procedure {stem};
Begin Log:=TStringList.Create;Mark('START_RF_CORRECTION');
D:=Client.OpenDocument('PCB','{P/(N+'.PcbDoc')}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{P/(N+'.PcbDoc')}') Then Exit;
If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1576) Or (ObjectCount('bodies',False)<>49) Then Begin Mark('STOP_COUNT');Exit;End;
{guards}
For K:=0 To 70 Do Ns[K]:=Nil;
I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
While N<>Nil Do Begin {binds} N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To 70 Do If Ns[K]=Nil Then Begin Mark('STOP_MISSING_NET');Exit;End;
ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'contours.txt'}');Mark('PREFLIGHT_OK');PCBServer.PreProcess;
Try ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eArcObject,eViaObject,eRegionObject));P:=I.FirstPCBObject;
While P<>Nil Do Begin Good:=False;
If P.Net<>Nil Then Begin
If ((P.ObjectId=eTrackObject) Or (P.ObjectId=eArcObject)) And (P.Layer=eBottomLayer) And ((Copy(P.Net.Name,1,2)='MW') Or (Copy(P.Net.Name,1,1)='S')) Then Good:=True;
If (P.ObjectId=eViaObject) And (P.Net.Name='GND') Then Good:=True;
If (P.ObjectId=eRegionObject) And (P.Net.Name='GND') And ((P.Layer=eMidLayer4) Or (P.Layer=eBottomLayer)) Then Good:=True;
End;
If (P.ObjectId=eRegionObject) And (P.Layer=eBottomSolder) Then Good:=True;
If Good Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_RF_SHIELD_SURFACES='+IntToStr(ND));
{''.join(f'Update{i};' for i in range(len(batches)))}
B.RebuildPadCaches;Finally PCBServer.PostProcess;End;
For K:=0 To 70 Do Begin Ns[K].ConnectivelyInValidate;Ns[K].Rebuild;End;B.ConnectivelyValidateNets;
B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
Mark('BUILT_REQUIRES_SAVE_REOPEN_DRC');ContourData.Free;Log.Free;End;
'''
(H/(stem+'.pas')).write_text(header+extra+body+main,encoding='ascii')
def project(stem):
    (H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
project(stem);shutil.copy2(OLD/'dispatch.py',H/'dispatch.py')
for stem in ('ValidateNative16RF','ExportCapPaste'):
    src=(OLD/(stem+'.pas')).read_text().replace(str(OLD),str(H))
    (H/(stem+'.pas')).write_text(src);project(stem)
for filename in ('audit_saved.py','audit_route_identity.py','audit_support.py'):
    if (H/filename).exists():continue  # Retain the adapted project-specific checks.
    src=(OLD/filename).read_text()
    if filename=='audit_support.py':src=src.replace("H/'backup'", "H/'baseline'")
    (H/filename).write_text(src)
print('Prepared',len(stm),'native statements and',len(contours),'contour points')
