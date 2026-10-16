"""Read-only schema inventory for local endpoint routing preparation."""
from pathlib import Path
import json

H = Path(__file__).resolve().parent
p = json.loads((H/'before_alignment/full_copper_candidate.json').read_text())
n = json.loads((H.parent/'qd38_rotation_20261011/saved_revision_snapshot.json').read_text())
print('Candidate keys', list(p))
for key in ('vias', 'dc_endpoints', 'dc_routed_jobs', 'route_jobs', 'pinmap', 'tracks'):
    data = p.get(key)
    print(key, 'type', type(data).__name__, 'count', len(data) if data is not None else None)
    if isinstance(data, list):
        print(json.dumps(data[:2], indent=2))
    elif isinstance(data, dict):
        print(json.dumps(list(data.items())[:2], indent=2))
print('Native via example', n['vias'][0])
print('Current direct QD endpoints')
for q in (3,4,17,18,20,22,23,36,37,38):
    net=f'DC{q:02}'
    via=[v for v in p['vias'] if v['net']==net and v['y']>30]
    print(q, via)
    for t in p['tracks']:
        if t['net']==net and t['layer'] in (2,4):
            print(t)

