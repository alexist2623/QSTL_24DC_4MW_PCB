"""Move the requested R/C groups and rebuild rectangular solder-control masks."""
from pathlib import Path
import sys,json,math,shutil,importlib.util,copy
from shapely.geometry import Point,LineString,Polygon,box,shape,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';OLD=H.parent/'shield_rc_ring_20260921';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha,UNIT
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
source=P/(B+'.PcbDoc')
if not (H/'before.PcbDoc').exists():shutil.copy2(source,H/'before.PcbDoc')
assert sha(H/'before.PcbDoc')=='5b0c672d0e64da5583e6cd3d61593bc834a61589a50c359124617ee5e220df8e'
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=source;live=m.read_native();m.SOURCE=H/'before.PcbDoc';n=m.read_native();before=copy.deepcopy(n)
(H/'before_native.json').write_text(json.dumps(n,indent=2))
q=lambda x:round(x/UNIT);snap=lambda x:q(x)*UNIT
moves={name:snap(dy) for names,dy in [(('R3','C3','R4','C4'),2.0),(('R1','C1','R5','C5'),1.0)] for name in names}
for c in n['components']:
    if c['designator'] in moves:c['y']=snap(c['y']+moves[c['designator']])
pmoves=[]
for p in n['pads']:
    if p['component'] not in moves:continue
    dy=moves[p['component']];pmoves.append(dict(component=p['component'],number=p['number'],old=[p['x'],p['y']],new=[p['x'],snap(p['y']+dy)]));p['y']=snap(p['y']+dy)
for v in n['vias']:
    for z in pmoves:
        if math.dist((v['x'],v['y']),z['old'])<4*UNIT:v['y']=z['new'][1];break
n['vias']=[v for v in n['vias'] if v['net']!='GND']
# Move only the capacitor endpoint of the existing through-resistor RF trunk.
oldpads={(p['component'],p['number']):p for p in before['pads'] if p['component']}
for ch in (1,3,4,5):
    p=oldpads[f'C{ch}','2'];hits=0
    for t in n['tracks']:
        if t['net']!=f'MW{ch}':continue
        for k in (1,2):
            if math.dist((t[f'x{k}'],t[f'y{k}']),(p['x'],p['y']))<4*UNIT:t[f'y{k}']=snap(t[f'y{k}']+moves[f'C{ch}']);hits+=1
    assert hits==1,(ch,hits)
# Extend lower capacitor input legs, retaining their SMP exit direction.
for ch in (1,5):
    p=oldpads[f'C{ch}','1'];hits=0
    for t in n['tracks']:
        if t['net']!=f'S{ch}':continue
        for k in (1,2):
            if math.dist((t[f'x{k}'],t[f'y{k}']),(p['x'],p['y']))<4*UNIT:t[f'y{k}']=snap(t[f'y{k}']+moves[f'C{ch}']);hits+=1
    assert hits==1
# Translate terminal DC corners and extend the existing single-layer trunks.
for net,threshold,dy in [('ZIF23',45.9,moves['R3']),('ZIF26',45.9,moves['R4']),('ZIF21',29.9,moves['R1']),('ZIF02',29.9,moves['R5'])]:
    for t in n['tracks']:
        if t['net']!=net or t['layer'] not in (2,4):continue
        for k in (1,2):
            if t[f'y{k}']>threshold:t[f'y{k}']=snap(t[f'y{k}']+dy)
n['tracks']=[t for t in n['tracks'] if t['net'] not in ('S3','S4')]
n['arcs']=[a for a in n['arcs'] if a['net'] not in ('S3','S4')]
def track(net,a,b):n['tracks'].append(dict(net=net,layer=32,native_layer_code=16842751,x1=snap(a[0]),y1=snap(a[1]),x2=snap(b[0]),y2=snap(b[1]),width=snap(.11)))
def arc(net,x,y,r,a,b):n['arcs'].append(dict(net=net,layer=32,cx=snap(x),cy=snap(y),radius=snap(r),start_angle=a,end_angle=b,width=snap(.11)))
for ch in (3,4):
    p=next(p for p in n['pads'] if p['component']==f'SMP{ch}' and p['number']=='1');cap=next(p for p in n['pads'] if p['component']==f'C{ch}' and p['number']=='1');x,y=p['x'],p['y'];cx,cy=cap['x'],cap['y'];yt=snap(51.3);r=snap(.3);d=1 if ch==4 else -1;net=f'S{ch}'
    track(net,(x,y),(x,yt-r));arc(net,x+d*r,yt-r,r,90 if d==1 else 0,180 if d==1 else 90)
    track(net,(x+d*r,yt),(cx-d*r,yt));arc(net,cx-d*r,yt-r,r,0 if d==1 else 90,90 if d==1 else 180);track(net,(cx,yt-r),(cx,cy))
# Latest user steering moves only the lower R1/C1 pair toward board centre.
dx=snap(-.35)
for c in n['components']:
    if c['designator'] in ('R1','C1'):c['x']=snap(c['x']+dx)
for p in n['pads']:
    if p['component'] in ('R1','C1'):p['x']=snap(p['x']+dx)
for z in pmoves:
    if z['component'] in ('R1','C1'):z['new'][0]=snap(z['new'][0]+dx)
for v in n['vias']:
    if v['net'] in ('MW1','ZIF21') and abs(v['y']-31)<.01:v['x']=snap(v['x']+dx)
for t in n['tracks']:
    if t['net']=='S1':
        for k in (1,2):
            if t[f'x{k}']<16:t[f'x{k}']=snap(t[f'x{k}']+dx)
    if t['net']=='MW1':
        for k in (1,2):
            if t[f'x{k}']>13:
                t[f'x{k}']=snap(t[f'x{k}']+dx)
                if t[f'y{k}']>31.1:t[f'y{k}']=snap(t[f'y{k}']-dx)
for a in n['arcs']:
    if a['net']=='S1':a['cx']=snap(a['cx']+dx)
    if a['net']=='MW1' and a['cx']>13:a['cx']=snap(a['cx']+dx);a['cy']=snap(a['cy']-dx)
# Replace the three terminal DC segments with one horizontal and two 45-degree bends.
removed=[t for t in n['tracks'] if t['net']=='ZIF21' and t['layer']==4 and min(t['y1'],t['y2'])>30.9]
assert len(removed)==3
n['tracks']=[t for t in n['tracks'] if t not in removed]
rp=next(p for p in n['pads'] if p['component']=='R1' and p['number']=='2');end=(rp['x'],rp['y']);start=(snap(12.95),snap(31.3));corner_y=snap(31.8)
verts=[start,(snap(13.45),corner_y),(snap(end[0]-(corner_y-end[1])),corner_y),end]
for a,b in zip(verts,verts[1:]):n['tracks'].append(dict(net='ZIF21',layer=4,native_layer_code=16777220,x1=a[0],y1=a[1],x2=b[0],y2=b[1],width=snap(.125)))
def padshape(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=64)
    return Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
def bounds_rect(g,margin):
    a,b,c,d=g.bounds;return box(a-margin,b-margin,c+margin,d+margin)
rc={f'R{k}/C{k}':bounds_rect(unary_union([padshape(p) for p in n['pads'] if p['component'] in (f'R{k}',f'C{k}')]),.9) for k in range(1,7)}
smp=[unary_union([padshape(p) for p in n['pads'] if p['component']==f'SMP{k}']).convex_hull.buffer(.3,quad_segs=32) for k in range(1,9)]
zifvias=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32) for v in n['vias'] if v['y']<10]);zifbottom=bounds_rect(zifvias,.4)
zifall=unary_union([zifvias]+[padshape(p) for p in n['pads'] if p['component']=='J1']);ziftop=bounds_rect(zifall,.3)
plan=json.loads((OLD/'plan.json').read_text());field=shape(plan['QD_mask_field']);rf=[]
for t in n['tracks']:
    if t['layer']==32:rf.append(LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]))
for a in n['arcs']:
    sweep=(a['end_angle']-a['start_angle'])%360;k=max(8,math.ceil(sweep/.1));rf.append(LineString([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/k)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/k))) for j in range(k+1)]))
center=unary_union(rf);extent=box(-.05,-.05,19.55,67.95)
top=unary_union(smp+list(rc.values())+[ziftop,field.buffer(.25,join_style='mitre')])
bottom=unary_union(smp+list(rc.values())+[zifbottom,center.buffer(.71,quad_segs=64)]).difference(field)
openings={37:extent.difference(top).simplify(.0003,preserve_topology=True),38:extent.difference(bottom).simplify(.0003,preserve_topology=True)}
plan.update(source_sha256=sha(H/'before.PcbDoc'),component_y_moves_mm=moves,component_x_moves_mm={'R1':dx,'C1':dx},pad_component_moves=pmoves,RC_mask_rectangles={k:mapping(v) for k,v in rc.items()},RC_mask_margin_mm=.9,ZIF_bottom_mask_rectangle=mapping(zifbottom),Top_mask_opening=mapping(openings[37]),Bottom_mask_opening=mapping(openings[38]),shield_center_offset_mm=.435,shield_distance_reference='RF copper edge to laser hole edge',shield_edge_gap_mm=.33)
(H/'plan.json').write_text(json.dumps(plan,indent=2));(H/'planned_native.json').write_text(json.dumps(n,indent=2))
req=P/'docs/DESIGN_REQUIREMENTS.md';s=req.read_text(encoding='utf-8')
s=s.replace('Via copper edges should sit approximately three RF trace widths from RF copper edges, not three widths to via centres. For 0.11 mm RF and 0.25 mm via lands, the straight-line centre offset is 0.51 mm.','The latest correction measures three RF widths from the RF copper edge to the laser-drill hole edge, not to the via land. For 0.11 mm RF and 0.10 mm holes, the centre offset is 0.435 mm; the 0.25 mm land edge is 0.255 mm from RF copper.')
s=s.replace('Use a 14-position angular grid (25.7142857 degrees) at the retained nominal 0.955 mm radius; omit only the two positions symmetrically straddling the RF exit. The remaining 12 vias per ring have approximately 0.425 mm chord spacing, close to 0.40 mm straight-fence spacing.','Choose an equal-angle grid from the hole-edge clearance radius and nominal 0.40 mm chord pitch. Keep the RF exit gap symmetric; do not retain an obsolete fixed via count when the radius changes.')
s=s.split('\n## Latest placement and rectangular mask refinement')[0]
s+='\n## Latest placement and rectangular mask refinement\n\n- Move upper R3/C3 and R4/C4 upward by 2.0 mm, away from the QD bond pads. Move both lower R1/C1 and R5/C5 upward by 1.0 mm, as confirmed by the user. Additionally move R1/C1 inward by 0.35 mm. Preserve pair spacing and rotations; reconnect RF/DC without adding transition vias.\n- Increase the retained solder-control margin around each R/C group from 0.30 to 0.90 mm. Use exact axis-aligned group rectangles, not rounded convex-hull patches. Preserve normal SMD pad openings and paste, RF coverage and the unmasked QD field.\n- Cover the complete Bottom ZIF fanout-via array with a rectangular solder-mask area, extending 0.40 mm beyond its via lands.\n'
req.write_text(s,encoding='utf-8');ag=R/'AGENTS.md';s=ag.read_text(encoding='utf-8').replace('from RF copper edge to via copper edge','from RF copper edge to laser-hole edge');s+='\nThe RF shield offset is measured to the laser hole edge: 0.435 mm centre offset for 0.11 mm RF and 0.10 mm holes. R/C solder-control masks use 0.90 mm rectangular group margins; the Bottom ZIF via array has a rectangular mask boundary. Preserve these conditions during subsequent edits.\n';ag.write_text(s,encoding='utf-8')
src=(H.parent/'rf_six_inward_20260920/ApplyRF6.pas').read_text();helpers=src[src.index('Function FindNet'):src.index('Function AddSignalVia')]
init=[]
for j,z in enumerate(pmoves,1):
    oldp=next(p for p in live['pads'] if p['component']==z['component'] and p['number']==z['number'])
    init.append(f"OX[{j}]:={q(oldp['x'])};OY[{j}]:={q(oldp['y'])};NX[{j}]:={q(z['new'][0])};NY[{j}]:={q(z['new'][1])};")
cmoves=[f"If C.Name.Text='{c['designator']}' Then Begin C.MoveToXY({q(c['x'])},{q(c['y'])});Inc(NC);End;" for c in n['components'] if c['designator'] in moves]
routes=[]
for t in n['tracks']:
    if t['layer'] in (2,4,32):routes.append("AddRFTrack(B,FindNet(B,'%s'),%s,%s);"%(t['net'],{2:'eMidLayer1',4:'eMidLayer3',32:'eBottomLayer'}[t['layer']],','.join(f'{t[k]:.12f}' for k in ('x1','y1','x2','y2','width'))))
for a in n['arcs']:routes.append("AddRFArc(B,FindNet(B,'%s'),eBottomLayer,%s);"%(a['net'],','.join(f'{a[k]:.12f}' for k in ('cx','cy','radius','width','start_angle','end_angle'))))
masklines=[]
for layer,geom in openings.items():
    for idx,poly in enumerate(geom.geoms if hasattr(geom,'geoms') else [geom]):
        poly=orient(poly,sign=1);masklines+=['G:=PCBServer.PCBGeometricPolygonFactory;']
        for hole,ring in [(False,poly.exterior)]+[(True,r) for r in poly.interiors]:
            masklines+=['Contour:=PCBServer.PCBContourFactory;']+[f'Contour.AddPoint({q(x)},{q(y)});' for x,y in list(ring.coords)[:-1]]+[f'G.AddContourIsHole(Contour,{hole});']
        masklines += [f"Reg:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);Reg.Kind:=eRegionKind_Copper;Reg.Layer:={'eTopSolder' if layer==37 else 'eBottomSolder'};Reg.Name:='SURFACE_MASK_OPEN_{layer}_{idx}';Reg.SetGeometricPolygon(G);B.AddPCBObject(Reg);"]
pas='''Var Log:TStringList;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('@LOG@');End;
@HELPERS@
Procedure ApplyMove;
Var B:IPCB_Board;D:IServerDocument;I:IPCB_BoardIterator;C:IPCB_Component;O:IPCB_Primitive;Pad:IPCB_Pad;V:IPCB_Via;Reg:IPCB_Region;Poly:IPCB_Polygon;G:IPCB_GeometricPolygon;Contour:IPCB_Contour;
HasVia:Array[1..16] Of Boolean;PS:Array[1..16] Of IPCB_Pad;VS:Array[1..16] Of IPCB_Via;OX,OY,NX,NY:Array[1..16] Of Integer;Dead:Array[0..2047] Of IPCB_Primitive;Polys:Array[0..7] Of IPCB_Polygon;NP,NV,ND,NC,NG,NR,J,NN:Integer;
Begin
 Log:=TStringList.Create;Mark('START');D:=Client.OpenDocument('PCB','@PCB@');If D=Nil Then Exit;Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;If B=Nil Then Exit;
 @INIT@
 NP:=0;NV:=0;ND:=0;NC:=0;NG:=0;NR:=0;For J:=1 To 16 Do HasVia[J]:=False;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject,eViaObject,eRegionObject,eTrackObject,eArcObject));O:=I.FirstPCBObject;
 While O<>Nil Do Begin
 If O.ObjectId=ePadObject Then Begin Pad:=O;For J:=1 To 16 Do If (Abs(Pad.X-OX[J])<4) And (Abs(Pad.Y-OY[J])<4) Then Begin PS[J]:=Pad;Inc(NP);End;End;
 If O.ObjectId=eViaObject Then Begin V:=O;If V.Net<>Nil Then If V.Net.Name='GND' Then Begin Dead[ND]:=O;Inc(ND);Inc(NG);End Else For J:=1 To 16 Do If (Abs(V.X-OX[J])<4) And (Abs(V.Y-OY[J])<4) Then Begin VS[J]:=V;HasVia[J]:=True;Inc(NV);End;End;
 If O.ObjectId=eRegionObject Then Begin Reg:=O;If Pos('SURFACE_MASK_OPEN_',Reg.Name)=1 Then Begin Dead[ND]:=O;Inc(ND);Inc(NR);End;End;
 If (O.ObjectId=eTrackObject) Or (O.ObjectId=eArcObject) Then Begin C:=O.Component;If C=Nil Then If O.Net<>Nil Then If O.Net.Name<>'GND' Then If (O.Layer=eMidLayer1) Or (O.Layer=eMidLayer3) Or (O.Layer=eBottomLayer) Then Begin Dead[ND]:=O;Inc(ND);End;End;
 O:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 Mark('PREFLIGHT='+IntToStr(NP)+','+IntToStr(NV)+','+IntToStr(NG)+','+IntToStr(NR)+','+IntToStr(ND));If (NP<>16) Or (NV<>8) Or (NG<>@OLDGND@) Or (NR<>2) Then Exit;
 PCBServer.PreProcess;Try
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;While C<>Nil Do Begin @MOVES@ C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=1 To 16 Do Begin PS[J].MoveToXY(NX[J],NY[J]);If HasVia[J] Then VS[J].MoveToXY(NX[J],NY[J]);End;
 For J:=0 To ND-1 Do B.RemovePCBObject(Dead[J]);
 @ROUTES@
 @MASK@
 Finally PCBServer.PostProcess;End;
 Mark('MOVED='+IntToStr(NC));B.RebuildPadCaches;NN:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePolyObject));Poly:=I.FirstPCBObject;While Poly<>Nil Do Begin Polys[NN]:=Poly;Inc(NN);Poly:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 For J:=0 To NN-1 Do Begin Polys[J].SetState_CopperPourInvalid;Polys[J].Rebuild;End;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;SaveCurrent;Mark('SAVED');Mark('COMPLETE');Log.Free;
End;
Procedure RunSafely;Begin Try ApplyMove;Except Mark('CAUGHT_NATIVE_FAILURE');End;End;
'''
for key,value in {'OLDGND':str(sum(v['net']=='GND' for v in live['vias'])),'LOG':str(H/'move_native.txt'),'PCB':str(source),'HELPERS':helpers,'INIT':'\n'.join(init),'MOVES':'\n'.join(cmoves),'ROUTES':'\n'.join(routes),'MASK':'\n'.join(masklines)}.items():pas=pas.replace('@'+key+'@',value)
(H/'ApplyMove.pas').write_text(pas,encoding='utf-8');print('Prepared movements,',len(routes),'route primitives, rectangular masks. Expected preflight 16 pads, 8 vias, 413 shields.')

