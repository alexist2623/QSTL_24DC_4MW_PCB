"""Measure centralization and clearances from saved native copper, not the plan."""
from pathlib import Path
import json,sys,math,hashlib,collections
from shapely.geometry import LineString,Point,Polygon,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];D=ROOT/'QSTL_QD4_2SET_38PAD';B=H/'before_dc_centralization'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/rf_redline_review_20261011')]
from audit_saved_revision_surface import read_snapshot
import dc_shielded_plan_20261016 as dc
pcb=D/'QSTL_QD4_2SET_38PAD.PcbDoc';sch=json.loads((D/'schematic_validation.json').read_text())
pads,regions,tracks,vias,outline=read_snapshot(pcb,sch)
old=read_snapshot(B/pcb.name,json.loads((B/'schematic_validation.json').read_text()))
plan=json.loads((H/'candidate.json').read_text());routes=json.loads((D/'DC_Centralized_20261016/dc_routed_plan.json').read_text())
data,groups,st,_,_,_=dc.load();errors=[];minimums={};banks={}
objects,bodies=dc.obstacles(routes,data,groups,st)
def check(ok,name,detail=None):
    if not ok:errors.append(dict(issue=name,detail=detail))
def record(name,gap,required,net,other):
    if name not in minimums or gap<minimums[name]['gap_mm']:minimums[name]=dict(gap_mm=gap,required_mm=required,net=net,other=other)
    check(gap>=required-0.000006,name,[net,other,gap])
for r in routes['routes']:
    ts=[t for t in tracks if t['net']==r['net'] and t['layer']==r['layer']]
    line=unary_union([t['geometry'] for t in ts]);copper=unary_union([t['geometry'].buffer(t['width']/2,quad_segs=64) for t in ts])
    banks[r['net']]=dict(line=line,copper=copper,layer=r['layer'])
    for v in vias:
        if v['low']<=r['layer']<=v['high'] and v['net']!=r['net']:
            gap=copper.distance(Point(v['x'],v['y']))
            record('trace_to_foreign_via_land',gap-v['diameter']/2,.1,r['net'],v['net'])
            record('trace_to_foreign_drill_edge',gap-v['hole']/2,.2,r['net'],v['net'])
    record('normalized_static_clearance',copper.distance(dc.own_obstacles(objects,bodies,groups,{r['source'],r['port']})),.1,r['net'],'static')
    for name in {n for n,_,_ in st['smp_pads']}:
        hull=unary_union([g for n,_,g in st['smp_pads'] if n==name]).convex_hull
        record('SMP_pad_hull_clearance',copper.distance(hull),.2,r['net'],name)
    for g in groups:
        ref=g['resistor']['ref'];hull=bodies[ref]
        if r['source']==ref+'-2':hull=hull.difference(Polygon(g['resistor']['pads'][1]['polygon_mm']))
        record('resistor_body_envelope_clearance',copper.distance(hull),.15,r['net'],ref)
    record('pocket_clearance',copper.distance(st['cavity']),.15,r['net'],'blind pocket')
    ground=unary_union([g['geometry'] for g in regions if g['net']=='GND' and g['layer']==r['layer']])
    record('DC_to_GND',copper.distance(ground),.2,r['net'],'GND')
items=list(banks.items())
for i,(a,ga) in enumerate(items):
    for b,gb in items[:i]:
        if ga['layer']==gb['layer']:record('DC_trace_to_trace',ga['copper'].distance(gb['copper']),.1,a,b)
spans=[]
for ll in (2,3):
    for y in (2,10,20):
        xs=[]
        for g in banks.values():
            if g['layer']==ll:
                q=g['line'].intersection(LineString([(-7,y),(27,y)]))
                check(q.geom_type=='Point','central_corridor_not_single_crossing',[ll,y,q.geom_type])
                if q.geom_type=='Point':xs.append(q.x)
        row=dict(layer=ll,y_mm=y,lanes=len(xs),min_x=min(xs),max_x=max(xs),copper_width_mm=max(xs)-min(xs)+.125,centre_x_mm=(min(xs)+max(xs))/2)
        check(len(xs)==19 and abs(row['centre_x_mm']-9.75)<.000005 and row['copper_width_mm']<4.806,'central_corridor',row);spans.append(row)
rf=lambda ts:collections.Counter((t['net'],t['layer'],t['width'],t['geometry'].wkb_hex) for t in ts if t['net'] and t['net'].startswith(('MW','S')))
check(rf(tracks)==rf(old[2]),'RF_geometry_changed')
for ll in (1,4,5,32,37,38):
    a=unary_union([r['geometry'] for r in regions if r['layer']==ll]);b=unary_union([r['geometry'] for r in old[1] if r['layer']==ll]);check(a.equals(b),'retained_surface_changed',ll)
vp=lambda vs:collections.Counter((v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in vs)
check(vp(vias)==vp(old[3]),'via_geometry_changed')
check(outline.equals(old[4]),'outline_changed')
out=dict(passed=not errors,errors=errors,source_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),cross_sections=spans,minimums=minimums,RF_and_mask_and_fixed_geometry_preserved=True)
(H/'central_saved_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
