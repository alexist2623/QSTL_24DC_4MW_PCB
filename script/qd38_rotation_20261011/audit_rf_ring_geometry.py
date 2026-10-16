"""Independently audit RF copper spacing and reserved active-SMP ring lands."""
from pathlib import Path
import argparse
import hashlib
import json
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
from audit_rf_topology import audit, arc_points, pgeom

H = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('candidate', type=Path)
parser.add_argument('--output', type=Path, default=H / 'rf_ring_geometry_audit.json')
args = parser.parse_args()
p = json.loads(args.candidate.read_text())
nets = {pad['net'] for pad in p['physical_pads'] if pad['net'] and pad['net'].startswith(('S', 'MW'))}
signals = {}
for net in sorted(nets):
    pieces = [LineString([t['a'], t['b']]).buffer(t['width']/2, quad_segs=64)
              for t in p['tracks'] if t['net'] == net and t['layer'] == 32]
    pieces += [LineString(arc_points(a)).buffer(a['width']/2+.000001, quad_segs=64)
               for a in p.get('arcs', []) if a['net'] == net and a['layer'] == 32]
    signals[net] = unary_union(pieces)
static = [(pad['net'], f"{pad['ref']}-{pad['pin']}", pgeom(pad))
          for pad in p['physical_pads'] if pad['layer'] in (32, 74)]
static += [(via['net'], via['label'], Point(via['x'],via['y']).buffer(via['diameter']/2, quad_segs=96))
           for via in p['vias'] if via['low'] <= 32 <= via['high']]
cx,cy=p['sample_center'];cw,ch=p['cavity_mm']
static.append((None,'cavity',box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)))
ring_gaps=[];static_gaps=[];pair_gaps=[];hull_gaps=[];failures=[]
for net,g in signals.items():
    for other,label,geom in static:
        if other==net:continue
        gap=g.distance(geom);static_gaps.append((gap,net,label))
        if gap < .15-1e-6:failures.append(dict(kind='foreign_static_gap',net=net,obstacle=label,gap_mm=gap))
    for smp in p['smp']:
        own=f"S{int(smp['ref'][3:]):02}"
        if net==own:continue
        reserved=Point(smp['x'],smp['y']).buffer(1.175,quad_segs=128)
        gap=g.distance(reserved);ring_gaps.append((gap,net,smp['ref']))
        if gap < .15-1e-6:failures.append(dict(kind='reserved_SMP_ring_gap',net=net,SMP=smp['ref'],gap_mm=gap))
    for ref in sorted({pad['ref'] for pad in p['physical_pads'] if pad['ref'] and pad['ref'].startswith('R')}):
        pads=[pad for pad in p['physical_pads'] if pad['ref']==ref]
        hull=unary_union([pgeom(pad) for pad in pads]).convex_hull
        own=unary_union([pgeom(pad) for pad in pads if pad['net']==net])
        gap=g.distance(hull.difference(own));hull_gaps.append((gap,net,ref))
        if gap < .15-1e-6:failures.append(dict(kind='resistor_body_gap',net=net,R=ref,gap_mm=gap))
items=list(signals.items())
for a,(net,g) in enumerate(items):
    for other,h in items[:a]:
        gap=g.distance(h);pair_gaps.append((gap,net,other))
        if gap < .15-1e-6:failures.append(dict(kind='RF_pair_gap',net=net,other=other,gap_mm=gap))
topology=audit(p)
report=dict(passed=not failures and topology['passed'],candidate=str(args.candidate.resolve()),
            sha256=hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
            minimum_foreign_static_gap=min(static_gaps),minimum_RF_pair_gap=min(pair_gaps),
            minimum_reserved_ring_gap=min(ring_gaps),minimum_resistor_body_gap=min(hull_gaps),
            failures=failures,topology_passed=topology['passed'],topology_failures=topology['failures'],
            quality_flags=topology['quality_flags'],ring_radius_mm=1.05,ring_land_diameter_mm=.25)
args.output.write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(0 if report['passed'] else 2)
