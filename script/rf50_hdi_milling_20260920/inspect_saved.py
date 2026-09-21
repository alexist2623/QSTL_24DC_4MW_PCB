"""Inspect saved stack, rules, mechanical labels and shield connections."""
from pathlib import Path
import sys,json,collections,struct
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_rules,read_regions,read_route
from shapely.geometry import Point
from shapely.ops import unary_union
s=snapshot(P/(B+'.PcbDoc'));b=properties(s['Board6/Data'])[0];rules=read_rules(s['Rules6/Data']);rs=read_regions(s['Regions6/Data']);ps=properties(s['Polygons6/Data']);ns=properties(s['Nets6/Data']);ts,ars,vs=read_route(s,ns)
stack={k:v for k,v in b.items() if k.startswith('V9_STACK_LAYER') and k.endswith(('NAME','THICKNESS','DIELCONST','MATERIAL','COPTHICK','DIELHEIGHT'))}
print(json.dumps(stack,indent=2));print('DRILL',[(k,v) for k,v in b.items() if 'DRILL' in k or 'PAIR' in k and not k.startswith('V9_CACHE')])
for r in rules:
    if r['NAME'] in ('RF_CPW_GND_GAP_0P2','Clearance','RF_SHIELD_L5_L6','RF_50OHM_WIDTH'):print('RULE',r)
out=[]
for layer in (5,32):
    ground=[]
    for r in rs:
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535:ni=int(ps[r['polygon_index']]['NET'])
        if r['layer']==layer and ni!=65535 and ns[ni]['NAME']=='GND':ground.append(r['geometry'])
    g=unary_union(ground);vals=[]
    for v in vs:
        if v['net']=='GND':
            disk=Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)
            vals.append(dict(x=v['x'],y=v['y'],overlap_fraction=g.intersection(disk).area/disk.area,center_in_ground=g.covers(Point(v['x'],v['y']))))
    out.append(dict(layer=layer,minimum_ground_land_overlap=min(v['overlap_fraction'] for v in vals),not_fully_covered=[v for v in vals if v['overlap_fraction']<.995]))
print('SOLID',json.dumps(out,indent=2));(H/'saved_inspection.json').write_text(json.dumps(dict(sha256=sha(P/(B+'.PcbDoc')),stack=stack,shield_connections=out),indent=2))
