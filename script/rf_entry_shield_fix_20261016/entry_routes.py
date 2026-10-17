"""Provide enough straight radial SMP approach for two uninterrupted via rows."""
from pathlib import Path
import sys,json,inspect
import numpy as np
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1]
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011')]
import finalize_shielded_rf_20261016 as f
data,groups,st=f.load_routes();by={g['row']['smp']:g for g in groups}
for z in json.loads((H/'refined_routes.json').read_text())['groups']:
    g=by[z['row']['smp']]
    if z['row']['smp']=='SMP28':continue  # Retain its saved QD curve: trial approached a foreign QD pad.
    for k in ('qd_to_c2','smp_to_c1'):g[k]=np.array(z[k])
    g['qline']=LineString(g['qd_to_c2']);g['sline']=LineString(g['smp_to_c1']);g['lines']=unary_union([g['qline'],g['sline']])
p=json.loads((H/'baseline/candidate.json').read_text())
dv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2+.258) for v in p['vias']])
src=inspect.getsource(f.m.terminal_routes).replace("for mode in ('qd','smp'):","for mode in ('smp',):").replace("(1.2,1.6,2.,2.4,2.8)","(2.4,2.8,3.2)").replace("selected[:600] if mode=='qd' else selected[:100]","selected")
scope=dict(f.m.__dict__);exec(src,scope)
report=[]
for g in groups:
    pool=scope['terminal_routes'](data,g,groups,st)[0]
    others=unary_union([h['lines'] for h in groups if h is not g])
    valid=[a for a in pool if a['line'].distance(others)>=1.285 and a['line'].distance(g['qline'])>=.26 and a['line'].disjoint(dv)]
    assert valid,g['row']['smp']
    chosen=min(valid,key=lambda a:a['score'])
    g['smp_to_c1']=chosen['points'];g['sline']=chosen['line'];g['lines']=unary_union([g['qline'],g['sline']])
    report.append(dict(channel=g['row']['smp'],straight_radial_entry_mm=float(np.linalg.norm(g['smp_to_c1'][-1]-g['smp_to_c1'][-2])),radius_mm=chosen['radius']))
serial=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in g.items() if k not in ('envelope','capg','resg','lines','tail','qline','sline')} for g in groups]
(H/'entry_routes.json').write_text(json.dumps(dict(groups=serial,entry_report=report),indent=2))
print(json.dumps(report,indent=2))
