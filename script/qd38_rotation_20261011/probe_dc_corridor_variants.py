"""Private routing capacity diagnostics, never a native design artifact."""
import copy
import json
import math
import sys
from pathlib import Path
from shapely.geometry import Point

sys.argv = [sys.argv[0], '.23', '.115', '.115', '--pooled', '--central', '--capacity-only']
import route_dc_rotated as router

H = Path(__file__).resolve().parent
base = json.loads((H / 'placement_corridor_candidate.json').read_text())


def move(plan, ref, x, y, angle):
    component = next(c for c in plan['components'] if c['ref'] == ref)
    ox, oy, oa = component['x'], component['y'], component['rotation']
    a = math.radians(angle - oa)
    def transform(px, py):
        dx, dy = px - ox, py - oy
        return x + math.cos(a)*dx-math.sin(a)*dy, y+math.sin(a)*dx+math.cos(a)*dy
    component.update(x=x, y=y, rotation=angle)
    for p in plan['physical_pads']:
        if p['ref'] == ref:
            p['x'], p['y'] = transform(p['x'], p['y'])
            p['rotation'] = (p['rotation'] + angle - oa) % 360
    for v in plan['vias']:
        if v['label'].split('-')[0] == ref:
            v['x'], v['y'] = transform(v['x'], v['y'])


def static(plan, refs):
    pads=plan['physical_pads']; fail=[]; mingap=100
    for i,p in enumerate(pads):
        if p['ref'] not in refs:
            continue
        g=router.pgeom(p)
        for q in pads:
            if q['ref']==p['ref'] or str(q['ref']).startswith('J1'):
                continue
            gap=g.distance(router.pgeom(q))
            mingap=min(mingap,gap)
            if gap < .14999:
                fail.append([p['ref'],p['pin'],q['ref'],q['pin'],gap])
    return dict(min_pad_gap=mingap, failures=fail)


variants={
    'lower_over_smp': [('R15',3.75,28.05,0),('R21',15.75,28.05,180),('C15',3.75,26.55,90),('C21',15.75,26.55,90)],
    'lower_outboard': [('R15',1.1,27.3,90),('R21',18.4,27.3,270)],
}
reports={}
for name,moves in variants.items():
    p=copy.deepcopy(base)
    for args in moves: move(p,*args)
    report=static(p,{m[0] for m in moves})
    print(name,'STATIC',json.dumps(report),flush=True)
    p['status']='PRIVATE_CAPACITY_DIAGNOSTIC_METADATA_NOT_FULLY_TRANSFORMED'
    (H/f'dc_probe_{name}.json').write_text(json.dumps(p,indent=2))
    source_vias=sorted([v for v in p['vias'] if not v['label'].startswith('J1-')],key=lambda v:(v['x'],v['y']))
    for i,v in enumerate(source_vias):
        layer=2 if i<19 else 4
        v['assigned_dc_layer']=v['routing_layer']=layer
        next(j for j in p['route_jobs'] if j['kind']=='DC' and j['net']==v['net'])['layer']=layer
    report['layers']=[router.run_layer(p,layer) for layer in (2,4)]
    reports[name]=report
    (H/'dc_corridor_variant_capacity.json').write_text(json.dumps(reports,indent=2))
