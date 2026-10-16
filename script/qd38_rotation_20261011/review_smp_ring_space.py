"""Inspect legal symmetric GND microvia ring candidates around actual SMPs."""
import json
import math
from pathlib import Path
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from route_rf_rotated import pgeom, arc_line
from shapely.geometry import LineString, box

HERE = Path(__file__).resolve().parent
plan = json.loads((HERE / 'merged_candidate.json').read_text())
pads = plan['physical_pads']
field = unary_union([pgeom(p) for p in pads if p['ref'] == 'Q1']).bounds
field = box(field[0]-.15,field[1]-.15,field[2]+.15,field[3]+.15)
body = unary_union([unary_union([pgeom(p) for p in pads if p['ref']==ref]).convex_hull for ref in {p['ref'] for p in pads if p['ref'] and p['ref'].startswith(('R','C'))}]).buffer(.001)
forbidden = unary_union([pgeom(p) for p in pads if p['layer'] in (32,74) and p['net']!='GND'] + [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32) for v in plan['vias']] + [LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=24) for t in plan['tracks'] if t['layer']==32] + [arc_line(a).buffer(a['width']/2+.00001,quad_segs=32) for a in plan.get('arcs',[])])
holes = [(p['x'],p['y'],p['hole']/2) for p in pads if p['hole']>0] + [(v['x'],v['y'],v['hole']/2) for v in plan['vias']]
boundary = Polygon(plan['board_outline']).buffer(-.15)

def reason(x,y):
    land=Point(x,y).buffer(.125,quad_segs=24)
    if any(math.hypot(x-hx,y-hy)-r-.05<.255 for hx,hy,r in holes):return 'drill'
    if not boundary.covers(land):return 'edge'
    if land.intersects(field) or land.intersects(body):return 'body'
    if land.distance(forbidden)<.15-1e-7:return 'signal'
    return None

rows=[]
for s in plan['smp']:
    choices=[]
    for radius,n in [(1.05,16),(.9,12),(.95,12),(1.0,12),(1.1,16),(1.2,16)]:
        angle=s['escape_angle_deg'];count=0;rejections=[]
        for k in range(1,n//2+1):
            offset=360*k/n
            if offset<=45:continue
            aa=[angle+offset] if k==n//2 else [angle+offset,angle-offset]
            reasons=[reason(s['x']+radius*math.cos(math.radians(a)),s['y']+radius*math.sin(math.radians(a))) for a in aa]
            if all(r is None for r in reasons):count+=len(aa)
            else:rejections.append([offset,reasons])
        choices.append(dict(radius_mm=radius,angular_grid=n,count=count,rejections=rejections))
    rows.append(dict(smp=s['ref'],choices=choices))
(HERE/'smp_ring_space_review.json').write_text(json.dumps(rows,indent=2))
print(json.dumps([{r['smp']:[(c['radius_mm'],c['angular_grid'],c['count']) for c in r['choices']]} for r in rows],indent=2))
