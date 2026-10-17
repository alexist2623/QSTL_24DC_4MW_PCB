"""Select local normal-launch RF curves with wider QD approach corridors."""
from pathlib import Path
import sys,json,pickle
import numpy as np
import shapely
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union,substring
from itertools import combinations
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011'),str(ROOT/'script/native_16rf_apply_20261016')]
import finalize_shielded_rf_20261016 as f
import build_candidate as bc
data,groups,st=f.load_routes();by={g['row']['smp']:g for g in groups}
p=json.loads((H/'baseline/candidate.json').read_text())
pools=pickle.loads((f.OUT/'candidate_segments.pkl').read_bytes())
targets=['SMP11','SMP12','SMP24','SMP28']
zones=[box(4.8,39.8,7.5,42.0),box(13.05,43.1,15.1,45.3)]
dv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2+.258) for v in p['vias']])
choices={}
for name in targets:
    src=next(pool for pool in pools if pool[0]['channel']==name and pool[0]['mode']=='qd')
    # The old cache kept only the shortest 600 corridors. Include longer normal
    # launch curves so the new local spacing objective can actually be met.
    import inspect
    if not (H/(name+'_pool.pkl')).exists():
        code=inspect.getsource(f.m.terminal_routes).replace("for mode in ('qd','smp'):","for mode in ('qd',):").replace("selected[:600] if mode=='qd' else selected[:100]","selected")
        scope=dict(f.m.__dict__);exec(code,scope)
        full=scope['terminal_routes'](data,by[name],groups,st)[0]
        (H/(name+'_pool.pkl')).write_bytes(pickle.dumps(full))
    src=pickle.loads((H/(name+'_pool.pkl')).read_bytes())
    g=by[name];fixed=unary_union([h['lines'] for h in groups if h['row']['smp'] not in targets]+[h['sline'] for h in groups if h['row']['smp'] in targets])
    selected=[]
    for a in src:
        line=a['line']
        if line.distance(fixed)<.567:continue
        if not line.disjoint(dv):continue
        if line.difference(f.m.QD_LAUNCH_ZONE).distance(fixed)<1.285:continue
        selected.append(a)
    choices[name]=selected
    print(name,'valid',len(selected),flush=True)

# Solve left and right independently, requiring all other RF to keep its existing margin.
results={};report=[]
for pair,zone in zip([targets[:2],targets[2:]],zones):
    aa,bb=[choices[n] for n in pair];candidates=[]
    for ia,a in enumerate(aa):
        for ib,b in enumerate(bb):
            la=a['line'];lb=b['line'];d=la.distance(lb)
            if d<.567:continue
            outside=min(la.difference(f.m.QD_LAUNCH_ZONE).distance(lb),lb.difference(f.m.QD_LAUNCH_ZONE).distance(la))
            if outside<1.285:continue
            az=la.intersection(zone);bz=lb.intersection(zone)
            if az.is_empty or bz.is_empty:continue
            gap=min(az.distance(lb),bz.distance(la))
            # Maximise local space up to two-row target, then prefer shorter curves.
            score=100*min(gap,1.30)+20*min(d,.90)-.02*(la.length+lb.length)
            candidates.append((score,ia,ib,gap,d))
    assert candidates,pair
    _,ia,ib,gap,glob=max(candidates)
    results[pair[0]]=aa[ia];results[pair[1]]=bb[ib]
    report.append(dict(channels=pair,marked_zone_edge_gap_mm=gap-.11,global_edge_gap_mm=glob-.11))
for name,a in results.items():
    g=by[name];g['qd_to_c2']=a['points'];g['qline']=a['line'];g['local_radius']=min(g['local_radius'],a['radius'])
    g['lines']=unary_union([g['qline'],g['sline']]);g['tail']=unary_union([g['qline'].difference(f.m.QD_LAUNCH_ZONE),g['sline']])
for a,b in combinations(groups,2):
    if a['row']['smp'] in targets or b['row']['smp'] in targets:
        gap=a['lines'].distance(b['lines'])-.11
        assert gap>=.457-1e-5,(a['row']['smp'],b['row']['smp'],gap)
serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items() if k not in ('envelope','capg','resg','lines','tail','qline','sline')} for g in groups]
(H/'routes.json').write_text(json.dumps(dict(groups=serial,local_changes=report),indent=2))
print(json.dumps(report,indent=2))
