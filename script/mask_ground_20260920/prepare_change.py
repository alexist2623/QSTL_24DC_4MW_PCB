"""Prepare native solder-mask openings, paste suppression and QD pour exclusions."""
from pathlib import Path
import sys,json,math,shutil,hashlib,importlib.util
from shapely.geometry import Polygon,Point,LineString,box,mapping
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
from shapely.geometry.polygon import orient
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
spec=importlib.util.spec_from_file_location('native_reader',W/'zif_revision_v2/render_native_layout.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);reader.SOURCE=P/(B+'.PcbDoc');n=reader.read_native()
backup=H/'before.PcbDoc'
if not backup.exists():
    assert n['source_sha256']=='d8d3e5dc6852aff818760e863640ffa2af25820d1afbc0d0a6ad946ec6c7260b'
    shutil.copy2(reader.SOURCE,backup)
assert hashlib.sha256(backup.read_bytes()).hexdigest()==n['source_sha256'],'Board changed since preflight'
(H/'before_native.json').write_text(json.dumps(n,indent=2),encoding='utf-8')
hashes={f:hashlib.sha256((P/f).read_bytes()).hexdigest() for f in [B+'.PcbDoc',B+'.PrjPcb',B+'.SchDoc',B+'.SchLib',B+'.PcbLib','Passives_0603.PcbLib','Capacitors_0402.PcbLib']}
(H/'before_hashes.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')

def land(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<.00001:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=48)
    return Polygon(reader.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))

protected=[]
for name in ['Q1','J1']+[f'SMP{i}' for i in range(1,9)]:
    shapes=[land(p) for p in n['pads'] if p['component']==name]
    if name=='J1':shapes += [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=24) for v in n['vias'] if v['y']<10]
    protected.append(unary_union(shapes).convex_hull.buffer(.3,quad_segs=12))
for k in range(1,7):
    protected.append(unary_union([land(p) for p in n['pads'] if p['component'] in (f'R{k}',f'C{k}')]).convex_hull.buffer(.3,quad_segs=12))
protected += [land(p).buffer(.3,quad_segs=24) for p in n['pads'] if p['component'] is None]
common=unary_union(protected).buffer(.06).buffer(-.06).simplify(.001,preserve_topology=True)
rf_shapes=[]
for t in n['tracks']:
    if t['layer']==32 and t['net'].startswith(('MW','S')):rf_shapes.append(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2+.26,quad_segs=24))
for a in n['arcs']:
    if a['layer']!=32:continue
    sweep=(a['end_angle']-a['start_angle'])%360;count=max(8,math.ceil(sweep/.5))
    path=LineString([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)])
    rf_shapes.append(path.buffer(a['width']/2+.26,quad_segs=24))
rf_protect=unary_union(rf_shapes)
board=box(0,0,19.5,67.9);opening_board=box(-.05,-.05,19.55,67.95)
kept={37:common,38:unary_union([common,rf_protect]).buffer(.06).buffer(-.06).simplify(.001,preserve_topology=True)}
openings={layer:opening_board.difference(shape) for layer,shape in kept.items()}
assert all(g.is_valid for g in openings.values())
qd=box(7.6,40.35,11.9,44.65)
plan=dict(source_hash=n['source_sha256'],protected_margin_mm=.3,RF_mask_margin_min_mm=.25,
          protected={str(k):mapping(v) for k,v in kept.items()},mask_openings={str(k):mapping(v) for k,v in openings.items()},
          QD_exclusion=mapping(qd),QD_exclusion_layers=[2,3,4,5,32],via_paste_regions_to_remove=144,
          paste_disabled_on=dict(vias=72,SMP_pads=40,standalone_mounting_pads=6),
          component_pad_paste_preserved=['Q1','J1']+[f'{p}{i}' for p in ('R','C') for i in range(1,7)])
(H/'mask_plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
UNIT=2.54e-6
lines=[];count=0
def add_shape(poly,layer,name,kind):
    global count
    poly=orient(poly,sign=1.0);lines.append(' G:=PCBServer.PCBGeometricPolygonFactory;')
    for hole,ring in [(False,poly.exterior)]+[(True,r) for r in poly.interiors]:
        lines.append(' C:=PCBServer.PCBContourFactory;')
        for x,y in list(ring.coords)[:-1]:lines.append(f' C.AddPoint({round(x/UNIT)},{round(y/UNIT)});')
        lines.append(' G.AddContourIsHole(C,'+str(hole)+');')
    lines.extend([f" Region:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Region.Kind:={kind};Region.Layer:={layer};Region.Name:='{name}';",
                  ' Region.SetGeometricPolygon(G);B.AddPCBObject(Region);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,Region.I_ObjectAddress);'])
    count+=1
for layer,g in openings.items():
    for i,poly in enumerate(g.geoms if hasattr(g,'geoms') else [g]):add_shape(poly,'eTopSolder' if layer==37 else 'eBottomSolder',f'SURFACE_MASK_OPEN_{layer}_{i}','eRegionKind_Copper')
for k,layer in zip((2,3,4,5,32),('eMidLayer1','eMidLayer2','eMidLayer3','eMidLayer4','eBottomLayer')):add_shape(qd,layer,f'QD_GND_EXCLUSION_L{k}','eRegionKind_Cutout')
script='''Var ChangeLog:TStringList;ChangePath:String;
Procedure MarkChange(S:String);Begin ChangeLog.Add(S);ChangeLog.SaveToFile(ChangePath+'work\\mask_ground_change.txt');End;
Procedure ApplyMaskGround;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;Region:IPCB_Region;Poly:IPCB_Polygon;Pad:IPCB_Pad;Via:IPCB_Via;Comp:IPCB_Component;
 C:IPCB_Contour;G:IPCB_GeometricPolygon;PC:TPadCache;Owned:Array[0..255] Of IPCB_Region;Polys:Array[0..7] Of IPCB_Polygon;
 N,J,NP,NV,NS,NM,Existing:Integer;
Begin
 ChangePath:='''+"'"+str(P)+"\\';"+'''
 D:=Client.OpenDocument('PCB',ChangePath+'QSTL_24DC_4MW_PCB.PcbDoc');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Exit;If LowerCase(B.FileName)<>LowerCase(ChangePath+'QSTL_24DC_4MW_PCB.PcbDoc') Then Exit;
 ChangeLog:=TStringList.Create;MarkChange('START');N:=0;Existing:=0;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eRegionObject));Region:=I.FirstPCBObject;
 While Region<>Nil Do Begin
  If Pos('ZIFV2_PASTE_',Region.Name)=1 Then Begin Owned[N]:=Region;Inc(N);End;
  If (Pos('SURFACE_MASK_OPEN_',Region.Name)=1) Or (Pos('QD_GND_EXCLUSION_',Region.Name)=1) Then Inc(Existing);
  Region:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);MarkChange('PASTE_REGIONS='+IntToStr(N));
 If (N<>144) Or (Existing<>0) Then Begin MarkChange('PREFLIGHT_FAILED');ChangeLog.Free;Exit;End;
 PCBServer.PreProcess;
 Try
  For J:=0 To N-1 Do B.RemovePCBObject(Owned[J]);MarkChange('VIA_PASTE_REMOVED=144');
  NV:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));Via:=I.FirstPCBObject;
  While Via<>Nil Do Begin PC:=Via.GetState_Cache;PC.PasteMaskExpansion:=-MMsToCoord(5);PC.PasteMaskExpansionValid:=eCacheManual;Via.SetState_Cache(PC);Inc(NV);Via:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  NS:=0;NM:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));Pad:=I.FirstPCBObject;
  While Pad<>Nil Do Begin Comp:=Pad.Component;
   If Comp=Nil Then Begin PC:=Pad.GetState_Cache;PC.PasteMaskExpansion:=-MMsToCoord(5);PC.PasteMaskExpansionValid:=eCacheManual;Pad.SetState_Cache(PC);Inc(NM);End
   Else If Copy(Comp.Name.Text,1,3)='SMP' Then Begin PC:=Pad.GetState_Cache;PC.PasteMaskExpansion:=-MMsToCoord(5);PC.PasteMaskExpansionValid:=eCacheManual;Pad.SetState_Cache(PC);Inc(NS);End;
   Pad:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);MarkChange('PASTE_DISABLED='+IntToStr(NV)+','+IntToStr(NS)+','+IntToStr(NM));
'''+ '\n'.join(lines)+'''
  MarkChange('MASK_AND_EXCLUSIONS_ADDED');
  NP:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin If Poly.Layer<>eTopLayer Then Begin Polys[NP]:=Poly;Inc(NP);End;Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For J:=0 To NP-1 Do Begin Poly:=Polys[J];Poly.SetState_CopperPourInvalid;Poly.Rebuild;MarkChange('REPOURED='+Poly.Name);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');
 MarkChange('SAVED');MarkChange('COMPLETE');ChangeLog.Free;
End;
'''
(H/'ApplyMaskGround.pas').write_text(script,encoding='ascii')
print(json.dumps(dict(regions=count,script_lines=len(script.splitlines()),mask_opening_area_mm2={str(k):v.intersection(board).area for k,v in openings.items()},protected_components=len(protected)),indent=2))
