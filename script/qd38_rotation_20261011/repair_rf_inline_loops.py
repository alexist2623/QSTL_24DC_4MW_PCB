"""Repair RF inline chains while preserving every physical placement."""
from pathlib import Path
import json
import math
import copy
import hashlib
import argparse
import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from skimage.graph import MCP_Geometric
import route_rf_rotated as router
from audit_rf_topology import audit

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=HERE / 'rf_corner_candidate.json')
parser.add_argument('--output', type=Path, default=HERE / 'rf_corner_repaired_candidate.json')
parser.add_argument('--report', type=Path, default=HERE / 'rf_corner_repaired_audit.json')
args = parser.parse_args()
source = args.source
plan = json.loads(source.read_text())
initial_audit = audit(plan)
repair_nets = {failure['net'] for failure in initial_audit['failures']
               if failure['kind'] == 'RF_inline_chain_topology'}
routes = copy.deepcopy(plan['rf_routed_jobs'])
static = [(pad['net'], router.pgeom(pad), f"{pad['ref']}-{pad['pin']}")
          for pad in plan['physical_pads'] if pad['layer'] in (32, 74)]
static += [(via['net'], Point(via['x'], via['y']).buffer(via['diameter']/2, quad_segs=64), via['label'])
           for via in plan['vias'] if via['low'] <= 32 <= via['high']]
cx, cy = plan['sample_center']
cw, ch = plan['cavity_mm']
static.append((None, box(cx-cw/2, cy-ch/2, cx+cw/2, cy+ch/2), 'cavity'))
edge = router.mask(box(-1, -1, 21, 70).difference(Polygon(plan['board_outline']).buffer(-.22)))
geometry = [router.copper(r['tracks'], r['arcs']) for r in routes]
repairs = []
for index, route in enumerate(routes):
    job = route['job']
    net = job['net']
    if job['kind'] != 'RF_QD' or net not in repair_nets:
        continue
    rpad = unary_union([router.pgeom(pad) for pad in plan['physical_pads']
                       if pad['ref'] and pad['ref'].startswith('R') and pad['pin'] == '1' and pad['net'] == net])
    cpad = unary_union([router.pgeom(pad) for pad in plan['physical_pads']
                       if pad['ref'] and pad['ref'].startswith('C') and pad['pin'] == '2' and pad['net'] == net])
    keepouts = [g for n, g, label in static if n != net] + [cpad]
    for ref in {p['ref'] for p in plan['physical_pads'] if p['ref'] and p['ref'].startswith('R')}:
        pads = [p for p in plan['physical_pads'] if p['ref'] == ref]
        hull = unary_union([router.pgeom(p) for p in pads]).convex_hull
        own = unary_union([router.pgeom(p) for p in pads if p['net'] == net])
        keepouts.append(hull.difference(own))
    other = []
    for k, geom in enumerate(geometry):
        if k == index:
            continue
        other.append(geom.difference(rpad) if routes[k]['job']['net'] == net else geom)
    forbidden = unary_union(keepouts + other)
    start = tuple(round(v/router.GRID) for v in reversed(job['a']))
    stop = tuple(round(v/router.GRID) for v in reversed(job['b']))
    selected = None
    for guard in (.027, .015, .007):
        hard = router.mask(forbidden.buffer(.15+.055+guard, quad_segs=32)) | edge
        if hard[start] or hard[stop]:
            print('BLOCKED', net, guard, hard[start], hard[stop], flush=True)
            continue
        costs = np.ones((router.NY, router.NX), dtype=float)
        costs[hard] = np.inf
        solver = MCP_Geometric(costs, fully_connected=True)
        distance, _ = solver.find_costs([start], [stop], find_all_ends=False)
        if not math.isfinite(distance[stop]):
            print('NO PATH', net, guard, flush=True)
            continue
        points = router.compact(solver.traceback(stop))
        points = router.shortcuts(points, forbidden, [])
        for radius in (.18, .12, .08, .04, .02, .01):
            tracks, arcs = router.fillet(points, net, radius)
            for actual, snapped in ((job['a'], points[0]), (job['b'], points[-1])):
                if math.dist(actual, snapped) > 1e-8:
                    tracks.append(dict(net=net, layer=32, a=list(actual), b=list(snapped), width=.11))
            geom = router.copper(tracks, arcs)
            gap = geom.distance(forbidden)
            if gap >= .151:
                selected = dict(job=job, points=points, tracks=tracks, arcs=arcs,
                                minimum_static_gap=gap, nominal_fillet_radius=radius)
                break
        if selected:
            break
    if not selected:
        raise RuntimeError(f'Could not repair {net}')
    routes[index] = selected
    geometry[index] = router.copper(selected['tracks'], selected['arcs'])
    repairs.append(dict(net=net, gap_mm=gap, bends=len(selected['arcs'])))
    print('REPAIRED', net, gap, len(selected['arcs']), flush=True)

plan['tracks'] = [t for t in plan['tracks'] if t['layer'] != 32] + [t for r in routes for t in r['tracks']]
plan['arcs'] = [a for r in routes for a in r['arcs']]
plan['rf_routed_jobs'] = routes
report = audit(plan)
pair_gaps = [(a, b, geometry[a].distance(geometry[b]))
             for a in range(len(routes)) for b in range(a)
             if routes[a]['job']['net'] != routes[b]['job']['net']]
conflicts = [(a, b, gap) for a, b, gap in pair_gaps if gap < .15-1e-7]
plan['rf_routing_validation'] = dict(passed=not conflicts, conflicts=conflicts, routes=len(routes),
                                   min_static_gap_mm=min(r['minimum_static_gap'] for r in routes),
                                   minimum_RF_pair_gap_mm=min(gap for a, b, gap in pair_gaps),
                                   arcs=len(plan['arcs']), minimum_arc_radius_mm=min(a['radius'] for a in plan['arcs']))
out = args.output
out.write_text(json.dumps(plan, indent=2))
report.update(candidate=str(out), candidate_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
              repairs=repairs, routing=plan['rf_routing_validation'])
args.report.write_text(json.dumps(report, indent=2))
print(json.dumps({k: v for k, v in report.items() if k not in ('net_reports', 'quality_flags')}, indent=2))
raise SystemExit(0 if report['passed'] and not conflicts else 2)
