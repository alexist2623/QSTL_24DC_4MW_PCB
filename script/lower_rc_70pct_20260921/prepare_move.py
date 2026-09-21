"""Plan rigid lower-pair moves and remove six unused QD RF through vias."""
from pathlib import Path
import sys,json,math,shutil,importlib.util,copy
from shapely.geometry import Point,LineString,Polygon,box,shape,mapping
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
OLD=H.parent/'remove_resistor_rf_vias_20260921';RC=H.parent/'rc_mask_clearance_20260921'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha,UNIT
from geometry_helpers import fillet_polyline,primitive_to_altium_dict,validate_path
source=P/(B+'.PcbDoc')
if not (H/'before.PcbDoc').exists():shutil.copy2(source,H/'before.PcbDoc')
assert sha(H/'before.PcbDoc')=='b173b9c072e841f28fbcb25979e917d688061a3a3b2fa08889f660b3afcafd10'
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.SOURCE=H/'before.PcbDoc';n=m.read_native();before=copy.deepcopy(n);live=before
(H/'before_native.json').write_text(json.dumps(n,indent=2))
q=lambda x:round(x/UNIT);snap=lambda x:q(x)*UNIT
def padshape(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=64)
    return Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
def pad(c,num):return next(p for p in n['pads'] if p['component']==c and p['number']==str(num))
def xy(p):return (p['x'],p['y'])
xmoves={};centres={}
for ch in (1,5):
    names=(f'R{ch}',f'C{ch}')
    xmin,_,xmax,_=unary_union([padshape(p) for p in n['pads'] if p['component'] in names]).bounds
    old=(xmin+xmax)/2;dx=snap((9.75+.7*(old-9.75))-old)
    centres[f'R{ch}/C{ch}']=dict(before_x_mm=old,after_x_mm=old+dx,dx_mm=dx,ratio=(old+dx-9.75)/(old-9.75))
    xmoves.update({name:dx for name in names})
moves={name:0 for name in xmoves};pmoves=[]
for c in n['components']:
    if c['designator'] in xmoves:c['x']=snap(c['x']+xmoves[c['designator']])
for p in n['pads']:
    if p['component'] not in xmoves:continue
    old=xy(p);p['x']=snap(p['x']+xmoves[p['component']]);pmoves.append(dict(component=p['component'],number=p['number'],old=list(old),new=list(xy(p))))
removed_qd=[];kept=[]
for v in n['vias']:
    if v['net']=='GND':continue
    if v['net'].startswith('MW'):
        match=[p for p in before['pads'] if p['component']=='Q1' and p['net']==v['net'] and math.dist(xy(p),xy(v))<4*UNIT]
        assert len(match)==1
        assert all(t['layer']==32 for t in before['tracks']+before['arcs'] if t['net']==v['net'])
        removed_qd.append(dict(via=v,pad=match[0]['number']));continue
    for z in pmoves:
        if math.dist(xy(v),z['old'])<4*UNIT:v['x'],v['y']=z['new'];break
    kept.append(v)
n['vias']=kept
assert len(removed_qd)==6 and len(kept)==48
n['tracks']=[t for t in n['tracks'] if t['net'] not in ('S1','MW1','S5','MW5')]
n['arcs']=[a for a in n['arcs'] if a['net'] not in ('S1','MW1','S5','MW5')]
paths={}
def route(net,points,r):
    path=fillet_polyline(points,r,layer=32,width=snap(.11),net=net);assert not validate_path(path)
    paths[net]=dict(vertices=points,radius_mm=r)
    for p in path:
        d=primitive_to_altium_dict(p);kind=d.pop('kind');d.pop('length_mm',None)
        if kind=='arc':
            d['start_angle']=round(d['start_angle'],10)%360
            d['end_angle']=round(d['end_angle'],10)%360
        for key in ('x1','y1','x2','y2','cx','cy','radius','width'):
            if key in d:d[key]=snap(d[key])
        if kind=='track':d['native_layer_code']=16842751
        n['tracks' if kind=='track' else 'arcs'].append(d)
for ch in (1,5):
    smp=pad(f'SMP{ch}',1);c=pad(f'C{ch}',1)
    route(f'S{ch}',[xy(smp),(c['x'],smp['y']),xy(c)],.3)
c=pad('C1',2);end=pad('Q1',9);delta=end['x']-c['x'];assert 0<delta<.2
route('MW1',[xy(c),(c['x'],33),(end['x'],33+delta),xy(end)],.15)
c=pad('C5',2);end=pad('Q1',12);delta=end['x']-c['x']
route('MW5',[xy(c),(c['x'],32),(end['x'],32+delta),xy(end)],.3)
for net,rname,trunk in [('ZIF21','R1',12.95),('ZIF02','R5',6.35)]:
    p=pad(rname,2);x=snap(trunk);y=snap(p['y']-abs(x-p['x']));trunks=[];kept_tracks=[]
    for t in n['tracks']:
        if t['net']!=net or t['layer']!=4:kept_tracks.append(t);continue
        if min(t['y1'],t['y2'])>30:continue
        if max(t['y1'],t['y2'])>30:
            for k in (1,2):
                if t[f'y{k}']>30:assert abs(t[f'x{k}']-x)<4*UNIT;t[f'y{k}']=y
            trunks.append(t)
        kept_tracks.append(t)
    assert len(trunks)==1
    kept_tracks.append(dict(net=net,layer=4,native_layer_code=16777220,x1=x,y1=y,x2=p['x'],y2=p['y'],width=snap(.125)))
    n['tracks']=kept_tracks
# Reuse the established exact rectangular mask construction.
src=(RC/'prepare_move.py').read_text()
mask=src[src.index('def bounds_rect'):src.index("(H/'plan.json').write_text")]
mask=mask.replace("component_x_moves_mm={'R1':dx,'C1':dx}","component_x_moves_mm=xmoves")
exec(compile(mask,'rectangular_mask_geometry','exec'))
plan.update(pair_centres=centres,removed_QD_RF_vias=removed_qd,RF_changed_paths=paths,shield_vias=[],signal_vias=48)
(H/'plan.json').write_text(json.dumps(plan,indent=2));(H/'planned_native.json').write_text(json.dumps(n,indent=2))
# Use the proven native geometry writer with strict object-count guards.
native=src[src.index("src=(H.parent/'rf_six_inward_20260920/ApplyRF6.pas')"):]
native=native.replace('Array[1..16]','Array[1..8]').replace('1 To 16','1 To 8')
native=native.replace('NP<>16','NP<>8').replace('NV<>8','NV<>2')
native=native.replace('NP,NV,ND,NC,NG,NR,J,NN:Integer','NP,NV,ND,NC,NG,NR,NQ,J,NN:Integer').replace('NP:=0;NV:=0;','NP:=0;NV:=0;NQ:=0;')
native=native.replace('End Else For J:=1 To 8','End Else If Pos(\'MW\',V.Net.Name)=1 Then Begin Dead[ND]:=O;Inc(ND);Inc(NQ);End Else For J:=1 To 8')
native=native.replace('(NP<>8) Or (NV<>2)','(NQ<>6) Or (NP<>8) Or (NV<>2)')
native=native.replace("16 pads, 8 vias, 413 shields.","8 pads, 2 DC vias, 6 QD RF vias removed, 470 shields.")
exec(compile(native,'native_move_writer','exec'))
shutil.copy2(RC/'preflight_plan.py',H/'preflight_plan.py')
print(json.dumps(centres,indent=2))
