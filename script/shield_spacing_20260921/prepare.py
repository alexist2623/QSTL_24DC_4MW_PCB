"""Densify L5-L6 GND shields with 0.15 mm land-edge spacing."""
from pathlib import Path
import sys,json,math,shutil,importlib.util,collections
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';OLD=H.parent/'rf50_hdi_milling_20260920';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha,UNIT
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
source=P/(B+'.PcbDoc');assert sha(source)==json.loads((OLD/'validation.json').read_text())['pcb_sha256']
if not (H/'before.PcbDoc').exists():shutil.copy2(source,H/'before.PcbDoc')
assert sha(H/'before.PcbDoc')==sha(source)
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=source;n=m.read_native()
(H/'before_native.json').write_text(json.dumps(n,indent=2));(H/'planned_native.json').write_text(json.dumps(n,indent=2))
WIDTH=.11;LAND=.25;HOLE=.1;GAP=.15;PITCH=LAND+GAP;OFFSET=.51
signals_v=[v for v in n['vias'] if v['net']!='GND'];assert len(signals_v)==60
def padshape(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=64)
    return Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
edges=collections.defaultdict(list)
for t in n['tracks']:
    if t['layer']==32:edges[t['net']].append([(t['x1'],t['y1']),(t['x2'],t['y2'])])
for a in n['arcs']:
    if a['layer']!=32:continue
    sweep=(a['end_angle']-a['start_angle'])%360;k=max(8,math.ceil(sweep/.1));edges[a['net']].append([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/k)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/k))) for j in range(k+1)])
paths={}
for net,items in edges.items():
    ends=[p for e in items for p in (e[0],e[-1])];start=next(p for p in ends if sum(math.dist(p,q)<.00005 for q in ends)==1);out=[start];left=items.copy()
    while left:
        dist,i,reverse=min([(math.dist(out[-1],e[0]),i,False) for i,e in enumerate(left)]+[(math.dist(out[-1],e[-1]),i,True) for i,e in enumerate(left)])
        assert dist<.00005;edge=left.pop(i);out.extend((edge[::-1] if reverse else edge)[1:])
    paths[net]=LineString(out)
center=unary_union(list(paths.values()));signals=unary_union([padshape(p) for p in n['pads'] if p['net']!='GND' and p['layer'] in (32,74)]+[Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64) for v in signals_v])
holes=[(p['x'],p['y'],p['hole']/2) for p in n['pads'] if p['hole']]+[(v['x'],v['y'],v['hole']/2) for v in signals_v]
data=snapshot(source);ns=properties(data['Nets6/Data']);polys=properties(data['Polygons6/Data']);regions=read_regions(data['Regions6/Data']);grounds={}
for layer in (5,32):
    pieces=[]
    for reg in regions:
        ni=reg['net_index']
        if ni==65535 and reg['polygon_index']!=65535:ni=int(polys[reg['polygon_index']]['NET'])
        if reg['layer']==layer and ni!=65535 and ns[ni]['NAME']=='GND':pieces.append(reg['geometry'])
    grounds[layer]=unary_union(pieces)
plan=json.loads((OLD/'plan.json').read_text());keep=shape(plan['QD_exclusion']);board=box(.2,.2,19.3,67.7);vias=[];fences=[]
def snap(x):return round(x/UNIT)*UNIT
def valid(x,y,near=True):
    pt=Point(x,y);disk=pt.buffer(LAND/2,quad_segs=16)
    if not board.covers(disk) or keep.intersects(disk):return False
    if pt.distance(signals)<LAND/2+.200005 or pt.distance(center)<OFFSET-6*UNIT:return False
    if any(math.hypot(x-hx,y-hy)<hr+HOLE/2+.254005 for hx,hy,hr in holes):return False
    if not all(g.covers(pt) for g in grounds.values()):return False
    if near and any(math.hypot(x-v['x'],y-v['y'])<PITCH-2*UNIT for v in vias):return False
    return True
def add(x,y,kind,**extra):
    x,y=snap(x),snap(y)
    if not valid(x,y):return False
    vias.append(dict(x=x,y=y,net='GND',start_layer=5,end_layer=32,diameter=LAND,hole=HOLE,kind=kind,rf_copper_edge_gap_mm=Point(x,y).distance(center)-WIDTH/2-LAND/2,**extra));return True
# Ring increments use a 0.400 mm chord. Clearance gaps occur at the RF exit
# and adjacent through holes; no overlapping or off-reference vias are placed.
for ch in range(1,7):
    p=next(p for p in n['pads'] if p['component']==f'SMP{ch}' and p['number']=='1');radius=p['size_x']/2+.33+LAND/2
    step=2*math.asin(PITCH/(2*radius));last=[]
    for j in range(math.floor(2*math.pi/step)):
        angle=math.pi/4+j*step
        if add(p['x']+radius*math.cos(angle),p['y']+radius*math.sin(angle),'SMP_RING',component=f'SMP{ch}',angle=math.degrees(angle)%360,radius_mm=radius):last.append(j)
    assert len(last)>=4,(ch,last)
# Sample the same offset curves. Adjacent centres use 0.400 mm chord spacing,
# including bends; skip locations blocked by component pads and plated holes.
for net,path in sorted(paths.items()):
    for side in (-1,1):
        offset=path.offset_curve(side*OFFSET,quad_segs=64,join_style='round')
        for part_id,line in enumerate(offset.geoms if hasattr(offset,'geoms') else [offset]):
            selected=[];distance=0.0
            while distance<=line.length:
                q=line.interpolate(distance);x,y=snap(q.x),snap(q.y)
                if add(x,y,'RF_FENCE',net_along=net,side=side,path_distance_mm=distance):
                    selected.append(distance)
                    # Find the first point one chord away, using a bracketed
                    # root to avoid short Euclidean spacing on rounded bends.
                    lo=distance;hi=min(distance+.4,line.length)
                    while hi<line.length and math.dist((x,y),(line.interpolate(hi).x,line.interpolate(hi).y))<PITCH:hi=min(hi+.025,line.length)
                    if math.dist((x,y),(line.interpolate(hi).x,line.interpolate(hi).y))<PITCH:break
                    for _ in range(24):
                        mid=(lo+hi)/2;pt=line.interpolate(mid)
                        if math.dist((x,y),(pt.x,pt.y))<PITCH:lo=mid
                        else:hi=mid
                    distance=hi
                else:distance+=.002
            fences.append(dict(net=net,side=side,part=part_id,path_length_mm=line.length,via_distances_mm=selected))
minpair=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-LAND for i,a in enumerate(vias) for b in vias[:i]);assert minpair>=GAP-2*UNIT
nearest=[min(math.dist((a['x'],a['y']),(b['x'],b['y']))-LAND for b in vias if b is not a) for a in vias]
plan.update(source_sha256=sha(source),shield_vias=vias,fences=fences,nominal_pitch_mm=PITCH,shield_to_shield_edge_gap_mm=GAP)
(H/'plan.json').write_text(json.dumps(plan,indent=2))
report=dict(source_sha256=sha(source),shield_vias=len(vias),ring_vias=sum(v['kind']=='SMP_RING' for v in vias),fence_vias=sum(v['kind']=='RF_FENCE' for v in vias),nominal_center_pitch_mm=PITCH,nominal_land_edge_gap_mm=GAP,min_land_edge_gap_mm=minpair,minimum_trace_edge_gap_mm=min(v['rf_copper_edge_gap_mm'] for v in vias),vias_with_nearest_gap_within_5um=sum(abs(g-GAP)<.005 for g in nearest),component_clearance_exceptions='Larger gaps at component pads, holes, RF exits and fence endpoints.')
(H/'preflight.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8').replace('at nominal 2 mm pitch','with nominal 0.15 mm land-edge spacing (0.40 mm centre pitch for 0.25 mm lands)');ag.write_text(s,encoding='utf-8')
req=P/'docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8').replace('at nominal 2 mm pitch.','with nominal 0.15 mm copper-land-edge spacing, equivalent to 0.40 mm centre spacing for the retained 0.25 mm lands. Use chord spacing at curves/rings; larger local gaps are allowed only to preserve pad/hole and RF-exit clearance. This supersedes the previous 2 mm pitch.');req.write_text(s,encoding='utf-8')
# Reuse existing independent audits with explicit counts from this plan.
for name in ('audit_connectivity.py','verify_final.py','AuditPaste.pas','ReopenAudit.pas','read_drc.py','fabrication_notes.py','publish_outputs.py','verify_fabrication.py'):
    s=(OLD/name).read_text(encoding='utf-8').replace('rf50_hdi_milling_20260920','shield_spacing_20260921').replace('RF50_HDI_DRC.html','Shield_spacing_DRC.html').replace('rf50_reopen_check.txt','shield_spacing_reopen_check.txt')
    if name=='verify_final.py':
        s=s.replace('(22,147,37,138)',f'(22,147,37,{60+len(vias)})').replace('len(shield)==78',f'len(shield)=={len(vias)}').replace("'RF50_HDI_validation.json'","'Shield_spacing_validation.json'")
        s=s.replace("check(len(signal)==60",f"pairgap=min(math.dist((a['x'],a['y']),(b['x'],b['y']))-(a['diameter']+b['diameter'])/2 for i,a in enumerate(shield) for b in shield[:i]);check(pairgap>=.15-6*UNIT,'Shield-to-shield spacing');check(len(signal)==60")
        s=s.replace("shield_span=['L5','L6']","shield_span=['L5','L6'],shield_to_shield_edge_gap_mm=pairgap,nominal_center_pitch_mm=.4")
    if name=='publish_outputs.py':
        s=s.replace("'C1-C6: no through vias | 78 GND shield vias | 2 mm nominal fence pitch'",f"'C1-C6: no through vias | {len(vias)} GND shields | 0.15 mm land-edge spacing'")
        s=s.replace('len(shield)==78',f'len(shield)=={len(vias)}').replace('RF50_HDI_validation.json','Shield_spacing_validation.json')
    if name=='verify_fabrication.py':s=s.replace('len(holes)==78',f'len(holes)=={len(vias)}')
    if name=='fabrication_notes.py':
        s=s.replace('nominal 2.0 mm pitch.','nominal 0.15 mm land-edge gap (0.40 mm centre-to-centre chord).').replace('Four diagonal vias form each active SMP signal ring','Circular blind-via fences surround each active SMP signal centre, with local gaps at RF exits and through holes').replace('78 saved L5-L6 vias',f'{len(vias)} saved L5-L6 vias').replace('RF50_HDI_validation.json','Shield_spacing_validation.json')
    (H/name).write_text(s,encoding='utf-8')
root=str(R)+'\\';log=str(H/'native_change.txt');old_count=sum(v['net']=='GND' for v in n['vias'])
pas='''Var Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('LOGPATH');End;
Procedure AddShield(B:IPCB_Board;GN:IPCB_Net;X,Y:Integer);
Var V:IPCB_Via;PC:TPadCache;
Begin
 V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=X;V.Y:=Y;V.Mode:=ePadMode_Simple;
 V.Size:=MMsToCoord(0.25);V.HoleSize:=MMsToCoord(0.1);V.LowLayer:=eMidLayer4;V.HighLayer:=eBottomLayer;V.Net:=GN;
 PC:=V.GetState_Cache;PC.SolderMaskExpansion:=-MMsToCoord(0.2);PC.SolderMaskBottomExpansion:=-MMsToCoord(0.2);PC.SolderMaskExpansionValid:=eCacheManual;V.SetState_Cache(PC);
 V.SetState_SolderMaskExpansionFromHoleEdge(False);V.SetState_IsTenting(True);V.SetState_IsTenting_Top(True);V.SetState_IsTenting_Bottom(True);V.SetState_PasteMaskEnabled(False);
 B.AddPCBObject(V);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,V.I_ObjectAddress);
End;
Procedure ApplyShieldSpacing;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;V:IPCB_Via;GN:IPCB_Net;Poly:IPCB_Polygon;Dead:Array[0..1023] Of IPCB_Via;Polys:Array[0..7] Of IPCB_Polygon;N,J,NP:Integer;
Begin
 Log:=TStringList.Create;Mark('START');D:=Client.OpenDocument('PCB','PCBDOC');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 If LowerCase(B.FileName)<>LowerCase('PCBDOC') Then Exit;
 N:=0;GN:=Nil;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eViaObject));V:=I.FirstPCBObject;
 While V<>Nil Do Begin If V.Net<>Nil Then If V.Net.Name='GND' Then Begin Dead[N]:=V;GN:=V.Net;Inc(N);End;V:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('OLD_SHIELDS='+IntToStr(N));If (N<>OLDCOUNT) Or (GN=Nil) Then Begin Mark('GUARD_STOP');Exit;End;
 PCBServer.PreProcess;
 Try
  For J:=0 To N-1 Do B.RemovePCBObject(Dead[J]);
ADDALL
  Mark('NEW_SHIELDS=NEWCOUNT');NP:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;
  While Poly<>Nil Do Begin Polys[NP]:=Poly;Inc(NP);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For J:=0 To NP-1 Do Begin Poly:=Polys[J];Poly.SetState_CopperPourInvalid;Poly.Rebuild;Mark('REPOURED='+Poly.Name);End;
 Finally PCBServer.PostProcess;End;
 B.RebuildPadCaches;B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 ResetParameters;AddStringParameter('SaveMode','Standard');AddStringParameter('ObjectKind','Document');RunProcess('WorkspaceManager:SaveObject');Mark('SAVED');Mark('COMPLETE');Log.Free;
End;
Procedure RunSafely;Begin Try ApplyShieldSpacing;Except Mark('CAUGHT_NATIVE_FAILURE');End;End;
'''
pas=pas.replace('LOGPATH',log).replace('PCBDOC',str(source)).replace('OLDCOUNT',str(old_count)).replace('NEWCOUNT',str(len(vias))).replace('ADDALL','\n'.join(f"AddShield(B,GN,{round(v['x']/UNIT)},{round(v['y']/UNIT)});" for v in vias))
(H/'ApplyShieldSpacing.pas').write_text(pas,encoding='utf-8')
