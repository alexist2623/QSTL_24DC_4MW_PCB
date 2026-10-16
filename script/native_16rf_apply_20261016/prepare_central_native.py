"""Stage a DC-only native update and synchronized ZIF schematic labels."""
from pathlib import Path
import sys,json,csv,copy,hashlib
from shapely.geometry import Point,LineString,Polygon,box,mapping,shape
from shapely.affinity import rotate,translate
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
B=H/'before_dc_centralization';NAME='QSTL_QD4_2SET_38PAD';STEM='ApplyCentralDC'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/_support/zif_revision/schematic')]
import native_constructors as nc
import build_zif_schematic as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P/(NAME+'.PcbDoc'))==sha(B/(NAME+'.PcbDoc'))
assert sha(P/(NAME+'.SchDoc'))==sha(B/(NAME+'.SchDoc'))
old=json.loads((B/'candidate.json').read_text());p=copy.deepcopy(old)
dc=json.loads((P/'DC_Centralized_20261016/dc_routed_plan.json').read_text())
assert json.loads((P/'DC_Centralized_20261016/dc_geometry_audit.json').read_text())['passed']
pn={r['port']:r['net'] for r in dc['routes']};assert len(pn)==38
p['tracks']=[t for t in p['tracks'] if not t['net'].startswith('DC')]
for r in dc['routes']:
    p['tracks'] += [dict(net=r['net'],layer=r['layer'],a=a,b=b,width=.125) for a,b in zip(r['points'][:-1],r['points'][1:])]
for r in dc['top_fanout']:
    p['tracks'] += [dict(net=pn[r['port']],layer=1,a=a,b=b,width=r['width']) for a,b in zip(r['points'][:-1],r['points'][1:])]
for v in p['vias']:
    if v['label'].startswith('J1-'):v['net']=pn[v['label']]
for d in p['physical_pads']:
    if d['ref']=='J1':d['net']=pn.get('J1-'+d['pin'])
for net,pins in p['nets'].items():p['nets'][net]=[v for v in pins if not v.startswith('J1-')]
for port,net in pn.items():p['nets'][net].append(port)
rows=list(csv.DictReader((P/'DC_Centralized_20261016/proposed_pin_mapping.csv').open()))
for r in rows:r['zif_pin']=r['proposed_zif_pin'];r['dc_layer']=r['proposed_dc_layer']
p['pinmap']=rows

def pg(d):
    if d['shape']=='round':return Point(d['x'],d['y']).buffer(d['sx']/2,quad_segs=128)
    return translate(rotate(box(-d['sx']/2,-d['sy']/2,d['sx']/2,d['sy']/2),d['rotation'],origin=(0,0)),d['x'],d['y'])
pads=p['physical_pads'];gs=[pg(d) for d in pads];board=Polygon(p['board_outline'])
anchors=unary_union([g for d,g in zip(pads,gs) if d['net']=='GND'])
for ll in (2,3):
    obs=[g.buffer(.2005,quad_segs=64) for d,g in zip(pads,gs) if d['layer'] in (ll,74) and d['net']!='GND']
    obs += [LineString([t['a'],t['b']]).buffer(t['width']/2+.203,quad_segs=32) for t in p['tracks'] if t['layer']==ll]
    obs += [Point(v['x'],v['y']).buffer(v['diameter']/2+.2005,quad_segs=64) for v in p['vias']]
    obs.append(shape(p['qd_ground_exclusion']))
    raw=board.buffer(-.2,join_style='mitre').difference(unary_union(obs))
    parts=list(raw.geoms) if hasattr(raw,'geoms') else [raw]
    keep=[g for g in parts if g.intersects(anchors)]
    p['ground_regions'][str(ll)]=mapping(unary_union(keep))
    p['ground_islands'][str(ll)]=dict(kept=len(keep),removed=len(parts)-len(keep))

# Freeze everything outside the authorized DC routing/net-label changes.
for key in ('components','arcs','shield_vias','board_outline','solder_openings','qd_ground_exclusion','qd_mask_field'):
    assert p[key]==old[key],key
for ll in ('1','4','5','32'):assert p['ground_regions'][ll]==old['ground_regions'][ll]
for a,b in zip(pads,old['physical_pads']):assert {k:v for k,v in a.items() if k!='net'}=={k:v for k,v in b.items() if k!='net'}
for a,b in zip(p['vias'],old['vias']):assert {k:v for k,v in a.items() if k!='net'}=={k:v for k,v in b.items() if k!='net'}
assert [t for t in p['tracks'] if t['layer']==32]==[t for t in old['tracks'] if t['layer']==32]
(H/'candidate.json').write_text(json.dumps(p,indent=2))

# Change only the existing explicit J1 labels; preserve all symbol/metadata records.
oldsch=json.loads((B/'schematic_validation.json').read_text());rs=s.records(B/(NAME+'.SchDoc'));out=copy.deepcopy(rs)
pin_net={pin:net for net,pins in p['nets'].items() for pin in pins};changed=[]
for pin in oldsch['pins']:
    if not pin['key'].startswith('J1-') or pin['key'] in oldsch['nc']:continue
    dx,dy=((1,0),(0,1),(-1,0),(0,-1))[pin['direction']];x,y=pin['tip'];end=(x+30*dx,y+30*dy)
    ids=[i for i,r in enumerate(out) if r.get('RECORD')=='25' and (int(r['Location.X']),int(r['Location.Y']))==end]
    assert len(ids)==1;i=ids[0];assert out[i]['Text']==oldsch['pin_net'][pin['key']]
    if out[i]['Text']!=pin_net[pin['key']]:changed.append(dict(pin=pin['key'],old=out[i]['Text'],new=pin_net[pin['key']]))
    out[i]['Text']=pin_net[pin['key']]
validation=s.geometry_check(out,oldsch['pins'],pin_net,oldsch['nc'])
stage=H/'centralized.SchDoc';s.update_copy(B/(NAME+'.SchDoc'),stage,{'FileHeader':s.pack([(0,s.encode(r)) for r in out])})
assert s.records(stage)==out
sch=dict(oldsch,nets=p['nets'],pin_net=pin_net,schematic_sha256=sha(stage),schematic_geometry_validation=validation,changed_ZIF_labels=changed,status='Centralized DC schematic staged; native compile pending')
(H/'centralized_schematic_validation.json').write_text(json.dumps(sch,indent=2))
fields=['qd_pad','chip_net','zif_pin','dc_net','dc_layer','rf','rf_net','smp','resistor','capacitor']
with (H/'centralized_pin_mapping.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

# Existing nets/components/vias are reused; no model, pad geometry or rule changes.
nmap={name:f'Ns[{i}]' for i,name in enumerate(p['nets'])};stm=[];contours=[]
for d in pads:
    if d['ref']=='J1':
        net=nmap.get(d['net'],'Nil');stm.append(f"PD:=J1.GetState_PadByName('{d['pin']}');PD.Net:={net};PD.SetState_InNet({net!='Nil'});")
for t in p['tracks']:
    if t['net'].startswith('DC'):stm.append(f"Track({nmap[t['net']]},{nc.layer(t['layer'])},"+','.join(nc.number(v) for v in (*t['a'],*t['b'],t['width']))+');')
for ll in ('2','3'):
    geo=shape(p['ground_regions'][ll]).simplify(.0002,preserve_topology=True)
    for i,poly in enumerate(list(geo.geoms) if hasattr(geo,'geoms') else [geo]):
        poly=orient(poly,sign=1);stm.append('G:=PCBServer.PCBGeometricPolygonFactory;')
        for ring,hole in [(poly.exterior,False)]+[(r,True) for r in poly.interiors]:
            coords=list(ring.coords)[:-1];start=len(contours);contours.extend(f'{nc.number(x)}|{nc.number(y)}' for x,y in coords)
            stm.extend(['CT:=PCBServer.PCBContourFactory;',f'LoadContour({start},{len(coords)});',f'G.AddContourIsHole(CT,{hole});'])
        stm.append(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={nc.layer(ll)};RG.Name:='CENTRAL_DC_GND_{ll}_{i}';RG.SetGeometricPolygon(G);RG.Net:={nmap['GND']};RG.SetState_InNet(True);Reg(RG);")
(H/'central_contours.txt').write_text('\n'.join(contours))
header=nc.HEADER.replace('__COMPONENT_MAX__','49').replace('__NET_MAX__','70').replace('__LOG__',str(H/'central_native_log.txt'))
header=header.replace('Good:Boolean;', 'ContourData:TStringList;Matched:Integer;Good:Boolean;')
header=header.replace('(Abs(CP.Rotation-R)<0.00001)', '((Abs(CP.Rotation-R)<0.00001) Or (Abs(Abs(CP.Rotation-R)-360)<0.00001))')
extra='''Procedure LoadContour(Start,Count:Integer);
Var J:Integer;Fields:TStringList;
Begin Fields:=TStringList.Create;Fields.Delimiter:='|';
For J:=Start To Start+Count-1 Do Begin Fields.DelimitedText:=ContourData[J];CT.AddPoint(MMsToCoord(StrToFloat(Fields[0])),MMsToCoord(StrToFloat(Fields[1])));End;Fields.Free;End;
'''
batches=[stm[i:i+150] for i in range(0,len(stm),150)]
body='\n'.join(f'Procedure Update{i};\nBegin\n'+'\n'.join(b)+'\nEnd;' for i,b in enumerate(batches))
binds='\n'.join(f"If N.Name='{name}' Then {var}:=N;" for name,var in nmap.items())
vbind='\n'.join(f"If (Abs(CoordToMMs(V.X)-{nc.number(v['x'])})<0.00001) And (Abs(CoordToMMs(V.Y)-{nc.number(v['y'])})<0.00001) Then Begin V.Net:={nmap[v['net']]};V.SetState_InNet(True);Inc(Matched);End;" for v in p['vias'] if v['label'].startswith('J1-'))
guards='\n'.join(f"If Not ComponentMatches('{c['ref']}',{nc.number(c['x'])},{nc.number(c['y'])},{nc.number(c['rotation'])}) Then Begin Mark('STOP_COMPONENT_{c['ref']}');Exit;End;" for c in p['components'])
main=f'''Procedure {STEM};
Begin
 Log:=TStringList.Create;Mark('START_CENTRAL_DC');
 D:=Client.OpenDocument('PCB','{P/(NAME+'.PcbDoc')}');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase('{P/(NAME+'.PcbDoc')}') Then Exit;
 If (ObjectCount('components',False)<>50) Or (ObjectCount('pads',False)<>241) Or (ObjectCount('vias',False)<>1515) Or (ObjectCount('bodies',False)<>49) Then Begin Mark('STOP_COUNT');Exit;End;
 {guards}
 For K:=0 To 70 Do Ns[K]:=Nil;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin {binds} N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For K:=0 To 70 Do If Ns[K]=Nil Then Begin Mark('STOP_MISSING_NET');Exit;End;
 J1:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin If C.Name.Text='J1' Then J1:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);If J1=Nil Then Exit;
 ContourData:=TStringList.Create;ContourData.LoadFromFile('{H/'central_contours.txt'}');
 Mark('PREFLIGHT_OK');PCBServer.PreProcess;
 Try
 ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eTrackObject,eRegionObject));P:=I.FirstPCBObject;
 While P<>Nil Do Begin Good:=False;
 If P.Net<>Nil Then Begin
 If (P.ObjectId=eTrackObject) And (Copy(P.Net.Name,1,2)='DC') Then Good:=True;
 If (P.ObjectId=eRegionObject) And (P.Net.Name='GND') And ((P.Layer=eMidLayer1) Or (P.Layer=eMidLayer2)) Then Good:=True;
 End;
 If Good Then Begin Dead[ND]:=P;Inc(ND);End;P:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('REMOVED_DC_AND_L2_L3_GROUND='+IntToStr(ND));
 Matched:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin {vbind} V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('J1_VIAS_REASSIGNED='+IntToStr(Matched));
 {''.join(f'Update{i};' for i in range(len(batches)))}
 B.RebuildPadCaches;
 Finally PCBServer.PostProcess;End;
 For K:=0 To 70 Do Begin Ns[K].ConnectivelyInValidate;Ns[K].Rebuild;End;B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 Mark('BUILT_REQUIRES_SAVE_REOPEN_DRC');ContourData.Free;Log.Free;
End;
'''
(H/(STEM+'.pas')).write_text(header+extra+body+main,encoding='ascii')
def project(stem):
    (H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n')
project(STEM)
close='CloseCentralSchematic'
(H/(close+'.pas')).write_text(f"Procedure {close};Var D:IServerDocument;Begin D:=Client.OpenDocument('SCH','{P/(NAME+'.SchDoc')}');If D<>Nil Then Client.CloseDocument(D);End;",encoding='ascii');project(close)
(H/'central_staging.json').write_text(json.dumps(dict(old_PCB_sha256=sha(B/(NAME+'.PcbDoc')),staged_candidate_sha256=sha(H/'candidate.json'),changed_ZIF_labels=changed,geometry_validation=validation,preserved_RF_components_masks_via_geometry=True),indent=2))
print(json.dumps(dict(staged=True,changed_ZIF_labels=len(changed),new_DC_tracks=sum(t['net'].startswith('DC') for t in p['tracks']),native_script_bytes=(H/(STEM+'.pas')).stat().st_size),indent=2))
