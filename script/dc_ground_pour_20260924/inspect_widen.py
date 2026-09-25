"""Inspect exact saved-rule and QD-boundary deltas after the native repour."""
from pathlib import Path
import sys,json
from shapely.geometry import box,Point
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,UNIT,pads_stream
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,read_rules
result={}
for name,path in [('before',H/'before_clearance_0p20.PcbDoc'),('after',R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')]:
 s=snapshot(path);rs=read_regions(s['Regions6/Data']);ps=properties(s['Polygons6/Data']);ns=properties(s['Nets6/Data'])
 gn=next(i for i,n in enumerate(ns) if n['NAME']=='GND');result[name]={'rules':read_rules(s['Rules6/Data']),'layers':{}}
 for layer in (2,4):
  g=unary_union([r['geometry'] for r in rs if r['layer']==layer and (r['net_index']==gn or r['polygon_index']!=65535 and int(ps[r['polygon_index']]['NET'])==gn)])
  keep=box(7.4,40.15,12.1,44.85);over=g.intersection(keep)
  result[name]['layers'][layer]={'area':g.area,'keep_intersection_area':over.area,'intersection_bounds':list(over.bounds),'intersection_wkt':over.wkt[:1000], 'inner_keep_area':g.intersection(keep.buffer(-6*UNIT)).area}
(H/'widen_inspection.json').write_text(json.dumps(result,indent=2))
old=snapshot(H/'before_clearance_0p20.PcbDoc');new=snapshot(R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')
delta={}
for stream in ('Nets6/Data','Polygons6/Data'):
 a,b=properties(old[stream]),properties(new[stream]);delta[stream]=[]
 for i,(r0,r1) in enumerate(zip(a,b)):
  changed={k:[r0.get(k),r1.get(k)] for k in set(r0)|set(r1) if r0.get(k)!=r1.get(k)}
  if changed:delta[stream].append({'index':i,'changes':changed})
print(json.dumps(delta,indent=2))
for radius in (2.50,2.51,2.52,2.55,2.60,2.70):
 ring=Point(3.4249995,18.08999938).buffer(radius,quad_segs=128).difference(Point(3.4249995,18.08999938).buffer(2.49,quad_segs=128))
 print('MOUNT_CHECK',radius,ring.difference(g.buffer(6*UNIT)).area)
