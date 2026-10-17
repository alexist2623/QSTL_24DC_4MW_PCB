"""Alternate the two local pair members while retaining the fixed terminals."""
from refine_routes import *
for z in json.loads((H/'refined_routes.json').read_text())['groups']:
    g=by[z['row']['smp']];g['qd_to_c2']=np.array(z['qd_to_c2']);g['qline']=LineString(g['qd_to_c2']);g['lines']=unary_union([g['qline'],g['sline']])
solve('SMP11','SMP12',zones[0],[(4.9,6),(40,43.7),(-2,-1),(.2,2),(.2,2),(.2,3),(.2,2)])
solve('SMP28','SMP24',zones[1],[(13.3,14.3),(41,44.5),(-1.9,-1.2),(.2,2),(.2,2),(.2,3),(.2,3)])
serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items() if k not in ('envelope','capg','resg','lines','tail','qline','sline')} for g in groups]
(H/'refined_routes.json').write_text(json.dumps(dict(groups=serial),indent=2))
