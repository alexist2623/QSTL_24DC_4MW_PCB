"""Measure saved trace-to-trace and coplanar trace-to-GND copper edge gaps."""
from pathlib import Path
import sys,json,itertools
from shapely.geometry import LineString
from shapely.ops import unary_union,nearest_points

H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,sha
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route,read_regions
from geometry_helpers import Arc,copper_geometry
pcb=P/'QSTL_24DC_4MW_PCB.PcbDoc';original=sha(pcb);s=snapshot(pcb)
ns=properties(s['Nets6/Data']);ps=properties(s['Polygons6/Data'])
ts,ars,vs=read_route(s,ns);rs=read_regions(s['Regions6/Data'])
gnd=next(i for i,n in enumerate(ns) if n['NAME']=='GND')
rows=[]
for layer in (1,2,3,4,5,32):
    traces=[]
    for t in ts:
        if t['layer']!=layer:continue
        axis=LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])])
        traces.append(dict(label='track:'+str(t['index']),net=t['net'],width=t['width'],axis=axis,
                           geom=axis.buffer(t['width']/2,quad_segs=256)))
    for a in ars:
        if a['layer']!=layer:continue
        geom=copper_geometry(Arc((a['cx'],a['cy']),a['radius'],a['start_angle'],
            (a['end_angle']-a['start_angle'])%360,layer,a['width'],a['net']),.0000001)
        traces.append(dict(label='arc:'+str(a['index']),net=a['net'],width=a['width'],axis=None,geom=geom))
    if not traces:continue
    regions=[]
    for r in rs:
        if r['layer']!=layer:continue
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535:ni=int(ps[r['polygon_index']]['NET'])
        if ni==gnd:regions.append(r['geometry'])
    ground=unary_union(regions)
    pair=[]
    for a,b in itertools.combinations(traces,2):
        if a['net']==b['net']:continue
        distance=(a['axis'].distance(b['axis'])-(a['width']+b['width'])/2
                  if a['axis'] is not None and b['axis'] is not None else a['geom'].distance(b['geom']))
        pair.append((distance,a,b))
    result={'layer':'L6' if layer==32 else 'L'+str(layer),'trace_count':len(traces),
            'minimum_trace_width_mm':min(t['width'] for t in traces)}
    if pair:
        distance,a,b=min(pair,key=lambda r:r[0])
        result['trace_to_trace']={'minimum_edge_gap_mm':distance,'nets':[a['net'],b['net']],
                                 'objects':[a['label'],b['label']]}
    if not ground.is_empty:
        distance,t=min(((ground.distance(t['geom']),t) for t in traces if t['net']!='GND'),key=lambda a:a[0])
        points=nearest_points(ground,t['geom'])
        result['trace_to_GND_pour']={'minimum_edge_gap_mm':distance,'net':t['net'],'object':t['label'],
                                    'closest_points_mm':[[p.x,p.y] for p in points]}
    rows.append(result)
report={'pcb_sha256':original,'measurement':'Same-layer copper edge gaps; different-net traces only. Pads/via clearances are separate.',
        'layers':rows,'JLCPCB_HDI_minimum_line_space_mm':.0762,
        'JLCPCB_general_copper_pour_recommendation_mm':.2,
        'sources':['https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq',
                   'https://jlcpcb.com/blog/how-to-avoid-shorts-open-circuits']}
assert sha(pcb)==original
(H/'trace_clearance_audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
