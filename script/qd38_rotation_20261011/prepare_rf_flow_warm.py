"""Prepare a free-assignment RF flow as an explicitly unverified warm start."""
from pathlib import Path
import copy,json,math
from shapely.geometry import Point,box
from shapely.ops import unary_union
import route_rf_corridor_bounded as rr
from geodesic_rf_assignment import remap

H=Path(__file__).resolve().parent
flow=json.loads((H/'rf_multi_flow_0.266_0.16.json').read_text())
p=remap(json.loads((H/'placement_lower_over_smp_candidate.json').read_text()),{int(k):v for k,v in flow['mapping'].items()})
reference=json.loads(Path(flow['reference_snapshot']).read_text())
fixed=copy.deepcopy([r for r in reference['routes'] if r['job']['kind']!='RF_QD'])
for r in fixed:
    old=r['job']['net']
    if old.startswith('MW'):
        net=f"MW{flow['mapping'][str(int(old[2:]))]:02}"
        r['job']['net']=net
        for piece in r['tracks']+r['arcs']:piece['net']=net
static=[(d['net'],rr.pgeom(d)) for d in p['physical_pads'] if d['layer'] in (32,74)]
static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=64)) for v in p['vias'] if v['low']<=32<=v['high']]
static += [(f'S{int(s["ref"][3:]):02}',Point(s['x'],s['y']).buffer(1.175,quad_segs=96)) for s in p['smp']]
cx,cy=p['sample_center'];cw,ch=p['cavity_mm'];static.append((None,box(cx-cw/2,cy-ch/2,cx+cw/2,cy+ch/2)))
raw=[]
for item in flow['routes']:
    net=f'MW{item["target"]:02}';job=next(j for j in p['route_jobs'] if j['kind']=='RF_QD' and j['net']==net)
    points=list(reversed(item['points']));blocked=[g for n,g in static if n!=net];ownr=[]
    for ref in sorted({d['ref'] for d in p['physical_pads'] if d['ref'] and d['ref'].startswith('R')}):
        pads=[d for d in p['physical_pads'] if d['ref']==ref]
        own=unary_union([rr.pgeom(d) for d in pads if d['net']==net]);ownr.append(own)
        blocked.append(unary_union([rr.pgeom(d) for d in pads]).convex_hull.difference(own))
    ownr=unary_union(ownr)
    for r in fixed:
        g=rr.copper(r['tracks'],r['arcs']);blocked.append(g.difference(ownr) if r['job']['net']==net else g)
    blocked += [rr.pgeom(d) for d in p['physical_pads'] if d['ref'] and d['ref'].startswith('C') and str(d['pin'])=='2' and d['net']==net]
    blocked=unary_union(blocked)
    for radius in (.18,.12,.08,.04,.02,.01,.005,.001):
        tracks,arcs=rr.fillet(points,net,radius);gap=rr.copper(tracks,arcs).distance(blocked)
        if gap>=.1505:break
    assert gap>=.1505,(net,gap)
    raw.append(dict(job=job,points=points,tracks=tracks,arcs=arcs,minimum_static_gap=gap,nominal_fillet_radius=radius))
(H/'placement_rf_flow_mapping_candidate.json').write_text(json.dumps(p,indent=2))
(H/'rf_flow_mapping_warm.json').write_text(json.dumps(dict(routes=fixed+raw,verified=False),indent=2))
source=(H/'route_rf_corridor_bounded.py').read_text()
source=source.replace('candidates=[[[x,y],[x+sx*d,y+sy*d],[xx,yy]],','candidates=[[[x,y],[xx,yy]], [[x,y],[x+sx*d,y+sy*d],[xx,yy]],')
source=source.replace("if iteration%4==3:\n            todo=list(range(len(jobs)))","if iteration%4==3:\n            todo=[i for i,j in enumerate(jobs) if j['kind']=='RF_QD']")
(H/'route_rf_flow_repair.py').write_text(source)
print('Warm paths prepared with preserved fixed RF stems; raw RF-to-RF conflicts are unresolved.')
