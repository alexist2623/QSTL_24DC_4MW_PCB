"""Plan RF shielding on L6/L5 without obstacles on unrelated DC layers."""
from pathlib import Path
import json, math, sys
from collections import defaultdict
from shapely.geometry import Point, LineString, Polygon, box, mapping
from shapely.ops import unary_union
from shapely.geometry.polygon import orient
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=H.parents[1]/'QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions
n=json.loads((H/'before_native.json').read_text());old_plan=json.loads((H.parent/'mask_ground_20260920/mask_plan.json').read_text())
from shapely.geometry import shape
UNIT=2.54e-6;WIDTH=.11;DRILL=.1;LAND=.25;OFFSET=WIDTH/2+3*WIDTH+LAND/2
pad_moves=[]
for p in n['pads']:
    if p['component']!='Q1':continue
    number=int(p['number']);dx,dy=((0,.2) if number in (1,24) else ((.2,0) if 2<=number<=8 else ((0,-.2) if 9<=number<=16 else (-.2,0))))
    old=(p['x'],p['y']);new=(round((old[0]+dx)/UNIT)*UNIT,round((old[1]+dy)/UNIT)*UNIT)
    pad_moves.append(dict(number=p['number'],old=list(old),new=list(new),net=p['net']))
    p['x'],p['y']=new
    for v in n['vias']:
        if math.dist((v['x'],v['y']),old)<.00001:v['x'],v['y']=new
    for t in n['tracks']:
        for end in (1,2):
            if math.dist((t[f'x{end}'],t[f'y{end}']),old)<.00001:t[f'x{end}'],t[f'y{end}']=new
for t in n['tracks']:
    if t['layer']==32:t['width']=WIDTH
for a in n['arcs']:
    if a['layer']==32:a['width']=WIDTH
dc_moves=[]
for net,x,y,dx,dy in [('ZIF23',12.9999994,46.10000178,.1,-.1),('ZIF23',12.9999994,33.64999874,.1,.1),('ZIF26',6.4499998,46.04999934,-.05,-.05),('ZIF26',6.4499998,35.59999992,-.05,.05)]:
    target=(round((x+dx)/UNIT)*UNIT,round((y+dy)/UNIT)*UNIT)
    dc_moves.append(dict(net=net,old=[x,y],new=list(target)))
    for t in n['tracks']:
        if t['net']!=net:continue
        for end in (1,2):
            if math.dist((t[f'x{end}'],t[f'y{end}']),(x,y))<.00001:t[f'x{end}'],t[f'y{end}']=target
(H/'planned_native.json').write_text(json.dumps(n,indent=2))

def padshape(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=48)
    a=math.radians(p['rotation']);co,si=math.cos(a),math.sin(a)
    return Polygon([(p['x']+x*co-y*si,p['y']+x*si+y*co) for x,y in [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),(p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]])

edges=defaultdict(list)
for t in n['tracks']:
    if t['layer']==32:edges[t['net']].append([(t['x1'],t['y1']),(t['x2'],t['y2'])])
for a in n['arcs']:
    if a['layer']!=32:continue
    sweep=(a['end_angle']-a['start_angle'])%360;count=max(8,math.ceil(sweep/.25))
    edges[a['net']].append([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/count)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/count))) for j in range(count+1)])
paths={}
for net,items in edges.items():
    endpoints=[p for item in items for p in (item[0],item[-1])]
    start=next(p for p in endpoints if sum(math.dist(p,q)<.00005 for q in endpoints)==1)
    out=[start];left=items.copy()
    while left:
        choices=[(math.dist(out[-1],e[0]),i,False) for i,e in enumerate(left)]+[(math.dist(out[-1],e[-1]),i,True) for i,e in enumerate(left)]
        distance,index,reverse=min(choices);assert distance<.00005,(net,distance)
        edge=left.pop(index);out.extend((edge[::-1] if reverse else edge)[1:])
    paths[net]=LineString(out)
center=unary_union(list(paths.values()));rf_copper=center.buffer(WIDTH/2,quad_segs=48)
signals=unary_union([padshape(p) for p in n['pads'] if p['net']!='GND' and p['layer'] in (32,74)])
signals=unary_union([signals]+[Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32) for v in n['vias'] if v['net']!='GND'])
holes=[(p['x'],p['y'],p['hole']/2) for p in n['pads'] if p['hole']>0]+[(v['x'],v['y'],v['hole']/2) for v in n['vias']]
ground=unary_union([r['geometry'] for r in read_regions(snapshot(H/'before.PcbDoc')['Regions6/Data']) if r['layer']==5 and r['props'].get('KIND')=='0'])
board=box(.2,.2,19.3,67.7);keepout=box(7.4,40.15,12.1,44.85)
vias=[];rejected=defaultdict(int)

def valid(x,y,spacing=.505):
    pt=Point(x,y);disk=pt.buffer(LAND/2,quad_segs=24)
    if not board.covers(disk) or keepout.intersects(disk):return False
    if pt.distance(signals)<LAND/2+.20001:return False
    if pt.distance(center)<OFFSET-.000015:return False
    # Old thermal voids are repoured after adding solid GND lands.
    if any(math.hypot(x-hx,y-hy)<hr+DRILL/2+.25401 for hx,hy,hr in holes):return False
    if any(math.hypot(x-v['x'],y-v['y'])<spacing for v in vias):return False
    return True

def add(x,y,kind,**extra):
    x=round(x/UNIT)*UNIT;y=round(y/UNIT)*UNIT
    if valid(x,y):
        vias.append(dict(x=x,y=y,net='GND',start_layer=5,end_layer=32,diameter=LAND,hole=DRILL,kind=kind,rf_copper_edge_gap_mm=Point(x,y).distance(rf_copper)-LAND/2,**extra));return True
    return False

# Four diagonal locations make a ring and leave cardinal RF escape corridors.
for k in range(1,7):
    p=next(p for p in n['pads'] if p['component']==f'SMP{k}' and p['number']=='1')
    radius=p['size_x']/2+3*WIDTH+LAND/2
    for angle in (45,135,225,315):
        a=math.radians(angle);ok=add(p['x']+radius*math.cos(a),p['y']+radius*math.sin(a),'SMP_RING',component=f'SMP{k}',angle=angle,radius_mm=radius)
        if not ok:
            q=Point(p['x']+radius*math.cos(a),p['y']+radius*math.sin(a))
            print('BLOCKED_RING',k,angle,'signal',q.distance(signals),'center',q.distance(center),'ground',ground.covers(q.buffer(LAND/2)), 'hole_gap',min(math.hypot(q.x-x,q.y-y)-r-DRILL/2 for x,y,r in holes))
        assert ok,('Ring blocked',k,angle)

fences=[]
for net,path in sorted(paths.items()):
    for side in (-1,1):
        fence=path.offset_curve(side*OFFSET,quad_segs=32,join_style='round')
        parts=list(fence.geoms) if hasattr(fence,'geoms') else [fence]
        for part_id,line in enumerate(parts):
            valid_positions=[]
            for i in range(math.ceil(line.length/.025)+1):
                d=min(i*.025,line.length);pt=line.interpolate(d)
                if valid(pt.x,pt.y):valid_positions.append((d,pt.x,pt.y))
            selected=[]
            if valid_positions:
                cursor=valid_positions[0][0]
                while cursor<=line.length+.001:
                    choices=[v for v in valid_positions if v[0]>=cursor-.4 and v[0]<=cursor+.4 and (not selected or v[0]>selected[-1][0]+.65)]
                    if not choices:
                        later=[v for v in valid_positions if v[0]>cursor]
                        if not later:break
                        target=later[0]
                    else:target=min(choices,key=lambda v:abs(v[0]-cursor))
                    d,x,y=target
                    if add(x,y,'RF_FENCE',net_along=net,side=side,path_distance_mm=d):selected.append(target)
                    cursor=d+2
                tail=valid_positions[-1]
                if selected and tail[0]-selected[-1][0]>1.6 and add(tail[1],tail[2],'RF_FENCE',net_along=net,side=side,path_distance_mm=tail[0]):selected.append(tail)
            fences.append(dict(net=net,side=side,part=part_id,path_length_mm=line.length,via_distances_mm=[x[0] for x in selected]))

# Expose the QD pad field on Bottom, while maintaining coated RF immediately outside.
qd_field=unary_union([padshape(p) for p in n['pads'] if p['component']=='Q1']).convex_hull.buffer(.05,join_style='mitre')
protected_top=shape(old_plan['protected']['37'])
protected_bottom=shape(old_plan['protected']['38']).union(center.buffer(.71,quad_segs=32)).difference(qd_field)
opening=box(-.05,-.05,19.55,67.95).difference(protected_bottom).simplify(.0005,preserve_topology=True)
# Nominal CNC corner radius 0.5 mm; the full envelope stays 3.9 x 3.9 mm.
cavity=box(8.1,40.85,11.4,44.15).buffer(.5,quad_segs=32)
assert max(abs(a-b) for a,b in zip(cavity.bounds,(7.6,40.35,11.9,44.65)))<1e-8
plan=dict(source_sha256=n['source_sha256'],pad_moves=pad_moves,dc_moves=dc_moves,QD_exclusion=mapping(keepout),RF_width_mm=WIDTH,CPW_gap_mm=.2,shield_land_mm=LAND,shield_drill_mm=DRILL,shield_center_offset_mm=OFFSET,shield_edge_gap_mm=3*WIDTH,nominal_pitch_mm=2,shield_vias=vias,fences=fences,Bottom_mask_opening=mapping(opening),QD_mask_field=mapping(qd_field),cavity=dict(envelope_mm=[7.6,40.35,11.9,44.65],size_mm=[4.3,4.3],corner_radius_mm=.5,depth_mm=1.2,entry='Bottom L6 / QD side',plated=False,geometry=mapping(cavity)),stack=dict(code='JLCH06161HN1-1078',dielectric_mm=[.0784,.55,.2008,.55,.0784],copper_mm=[.035,.0152,.0152,.0152,.0152,.035]))
(H/'plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(shield_vias=len(vias),rings=sum(v['kind']=='SMP_RING' for v in vias),fences=sum(v['kind']=='RF_FENCE' for v in vias),min_edge_gap=min(v['rf_copper_edge_gap_mm'] for v in vias),max_along_gap=max((b-a for f in fences for a,b in zip(f['via_distances_mm'],f['via_distances_mm'][1:])),default=0),cavity=plan['cavity']['size_mm']),indent=2))
