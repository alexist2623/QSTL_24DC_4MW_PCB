"""Widen two exterior RF runs while preserving terminals and physical placement."""
from pathlib import Path
import copy,json,hashlib
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr

H=Path(__file__).resolve().parent
source=H/'rf_planar_fullpad_curved_candidate.json'
p=json.loads(source.read_text())
audit=json.loads((H/'rf_planar_fullpad_curved_audit.json').read_text())
assert audit['passed'] and audit['sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
p['rf_routing_validation'].update(passed=True,status='Offline full-copper geometry, topology and tangent-curve audits passed; native save/reopen checks remain.',min_static_gap_mm=audit['minimum_foreign_static_gap'][0],min_RF_pair_gap_mm=audit['minimum_RF_pair_gap'][0],arcs=len(p['arcs']))
(H/'rf_baseline_64arc_candidate.json').write_text(json.dumps(p,indent=2))
static=[(d['net'],rr.pgeom(d)) for d in p['physical_pads'] if d['layer'] in (32,74)]
static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)) for v in p['vias'] if v['low']<=32<=v['high']]
static += [(f'S{int(s["ref"][3:]):02}',Point(s['x'],s['y']).buffer(1.175,quad_segs=96)) for s in p['smp']]
cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];static.append((None,box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)))
rrefs=sorted({d['ref'] for d in p['physical_pads'] if d['ref'] and d['ref'].startswith('R')})
boundary=Polygon(p['board_outline']).buffer(-.2)
report=[]
for net in ('MW12','MW31'):
    route=next(r for r in p['rf_routed_jobs'] if r['job']['net']==net and r['job']['kind']=='RF_QD')
    points=copy.deepcopy(route['points'])
    if net=='MW12':
        points=points[:4]+[[.99,45.962000000000174],[.99,56.602000000000245]]+points[8:]
    else:
        points[4][0]+=.5;points[5][0]+=.5
    blocked=[g for n,g in static if n!=net];own_r=[]
    for ref in rrefs:
        pads=[d for d in p['physical_pads'] if d['ref']==ref]
        own=unary_union([rr.pgeom(d) for d in pads if d['net']==net]);own_r.append(own)
        blocked.append(unary_union([rr.pgeom(d) for d in pads]).convex_hull.difference(own))
    own_r=unary_union(own_r)
    for other in p['rf_routed_jobs']:
        if other is route:continue
        geom=rr.copper(other['tracks'],other['arcs'])
        blocked.append(geom.difference(own_r) if other['job']['net']==net else geom)
    blocked += [rr.pgeom(d) for d in p['physical_pads'] if d['ref'] and d['ref'].startswith('C') and str(d['pin'])=='2' and d['net']==net]
    blocked=unary_union(blocked);accepted=None
    for radius in (.25,.18,.12,.08):
        tracks,arcs=rr.fillet(points,net,radius);geom=rr.copper(tracks,arcs);gap=geom.distance(blocked)
        if gap>=.1505 and boundary.covers(geom):accepted=(tracks,arcs,gap,radius);break
    if accepted is None:raise ValueError((net,'widening blocked',gap,points))
    tracks,arcs,gap,radius=accepted
    route.update(points=points,tracks=tracks,arcs=arcs,minimum_static_gap=gap,nominal_fillet_radius=radius)
    report.append(dict(net=net,minimum_gap_mm=gap,points=points,arcs=len(arcs),radius_mm=radius))
p['tracks']=[t for t in p['tracks'] if t['layer']!=32]+[t for r in p['rf_routed_jobs'] for t in r['tracks']]
p['arcs']=[a for r in p['rf_routed_jobs'] for a in r['arcs']]
p['rf_routing_validation'].update(passed=False,status='Exterior pair widening awaits independent audit',arcs=len(p['arcs']))
p['rf_exterior_widening']=report
(H/'rf_widened_candidate.json').write_text(json.dumps(p,indent=2))
(H/'rf_exterior_widening_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
