"""Synchronize the copied electrical plan with verified disjoint DC routes."""
import csv
import json
from shapely.geometry import LineString, Point, box
from route_circuit import pgeom
from design_geometry import DEST


def main():
    plan = json.loads((DEST / 'circuit_plan.json').read_text())
    result = json.loads((DEST / 'dc_flow_candidate.json').read_text())
    assert result['passed']
    routes = [r for layer in result['layers'] for r in layer['routes']]
    assert len(routes) == 38
    mapping = {r['port'].split('-')[1]: r['net'] for r in routes}
    assert len(mapping) == 38 and '50' not in mapping
    for p in plan['physical_pads']:
        if p['ref'] == 'J1':
            p['net'] = mapping.get(p['pin'])
    for v in plan['vias']:
        if v['label'].startswith('J1-'):
            v['net'] = mapping[v['label'].split('-')[1]]
    # Top fanout segments connect exactly one selected contact to its via.
    top_tracks = []
    for v in plan['vias']:
        if not v['label'].startswith('J1-'):
            continue
        pin = v['label'].split('-')[1]
        pad = next(p for p in plan['physical_pads'] if p['ref']=='J1' and p['pin']==pin)
        top_tracks.append(dict(net=v['net'], layer=1, width=.15,
                               a=[pad['x'],pad['y']], b=[v['x'],v['y']]))
    plan['tracks'] = top_tracks
    plan['dc_routed_jobs'] = []
    for r in routes:
        pin = int(r['port'].split('-')[1])
        qd = int(r['net'][2:])
        row = next(p for p in plan['pinmap'] if p['qd_pad']==qd)
        row['zif_pin'] = pin
        endpoint = plan['dc_endpoints'][str(qd)]
        endpoint['zif_pin'] = pin
        job = next(j for j in plan['route_jobs'] if j['kind']=='DC' and j['net']==r['net'])
        job['a'] = r['points'][-1]
        job['b'] = r['points'][0]
        plan['tracks'].extend(dict(net=r['net'], layer=r['layer'], width=r['width'], a=a, b=b)
                              for a,b in zip(r['points'],r['points'][1:]))
        plan['dc_routed_jobs'].append(dict(job=job, points=list(reversed(r['points']))))
    plan['nets'] = {}
    for p in plan['physical_pads']:
        if p['ref'] and p['net']:
            plan['nets'].setdefault(p['net'], []).append(p['ref']+'-'+p['pin'])

    # Recheck with the FINAL assignment, without old same-net exemptions.
    failures = []
    copper = [LineString(r['points']).buffer(r['width']/2, quad_segs=32) for r in routes]
    minimum = 100.
    for i,r in enumerate(routes):
        g = copper[i]
        assert g.disjoint(box(7.05,40.3,12.45,44.7))
        objects = [(f"{p['ref']}-{p['pin']}",p['net'],pgeom(p)) for p in plan['physical_pads']
                   if p['layer'] in (r['layer'],74)]
        objects += [(v['label'],v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32))
                    for v in plan['vias'] if v['low']<=r['layer']<=v['high']]
        objects += [(routes[j]['net'],routes[j]['net'],copper[j]) for j in range(i)
                    if routes[j]['layer']==r['layer']]
        for label,net,other in objects:
            if net == r['net']:
                continue
            gap = g.distance(other)
            minimum = min(minimum,gap)
            if gap < .15-1e-7:
                failures.append(dict(a=r['net'],b=label,layer=r['layer'],gap=gap))
        vias = [v for v in plan['vias'] if v['net']==r['net']]
        assert len(vias)==2
        assert all(g.intersects(Point(v['x'],v['y'])) for v in vias)
    assert not failures, failures
    plan['dc_routing_validation'] = dict(routes=38, layers=[2,4], minimum_clearance_mm=minimum,
        crossings=0, intermediate_transition_vias=0, status='OFFLINE_GEOMETRY_VERIFIED_NATIVE_PENDING')
    (DEST/'circuit_plan.json').write_text(json.dumps(plan,indent=2))
    with (DEST/'pin_mapping.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(plan['pinmap'][0]))
        w.writeheader();w.writerows(plan['pinmap'])
    print(json.dumps(plan['dc_routing_validation'],indent=2))


if __name__=='__main__':
    main()
