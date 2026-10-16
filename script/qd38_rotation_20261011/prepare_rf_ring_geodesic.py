"""Re-evaluate RF assignment with protected rings and true inline terminals."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = (HERE / 'geodesic_rf_assignment.py').read_text()
source = source.replace('rf_geodesic', 'rf_ring_geodesic')
source = source.replace("    static.append((None,box(7.6,39.85,11.9,45.15),'cavity'))", """    static += [(None,Point(s['x'],s['y']).buffer(1.175,quad_segs=96),s['ref']+'-ring') for s in plan['smp']]
    from route_rf_rotated import copper
    routed=json.loads((H/'rf_ordered_candidate.json').read_text())
    stems={}
    for route in routed['rf_routed_jobs']:
        if route['job']['kind']!='RF_BIAS':continue
        xy=route['job']['b']
        r=next(d for d in plan['physical_pads'] if d['ref'] and d['ref'].startswith('R') and d['pin']=='1' and math.dist(xy,(d['x'],d['y']))<1e-5)
        group=int(r['ref'][1:]);g=copper(route['tracks'],route['arcs'])
        stems[group]=g.difference(pg(r))
        static.append((f'MW{group:02}',g,'STEM'+str(group)))
    static.append((None,box(7.6,39.85,11.9,45.15),'cavity'))""")
source = source.replace("keepouts=[g for n,g,label in static if n!=net or label.startswith('Q1-')]", "keepouts=[g for n,g,label in static if n!=net or label.startswith(('Q1-','C'))]+[stems[group]]")
(HERE / 'ring_geodesic_rf_assignment.py').write_text(source)
print('Prepared ring-constrained assignment analyzer.')
