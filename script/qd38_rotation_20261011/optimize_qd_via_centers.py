"""Offline direct-via feasibility with pad centres contained, not pad resizing."""
import copy,json,math,time
from pathlib import Path
import numpy as np
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from build_rotated_placement import pg
H=Path(__file__).resolve().parent
p=json.loads((H/'placement_candidate.json').read_text())
base=copy.deepcopy(p)
fixedvias=[v for v in p['vias'] if not v['label'].startswith('Q1-')]
qpads={f"Q1-{d['pin']}":d for d in p['physical_pads'] if d['ref']=='Q1'}
vs=[v for v in p['vias'] if v['label'].startswith('Q1-')]
opts={}
for v in vs:
    q=qpads[v['label']];t=math.radians(q['rotation']);u=np.array([math.cos(t),math.sin(t)]);w=np.array([-u[1],u[0]])
    others=unary_union([pg(d) for d in p['physical_pads'] if d['net']!=v['net'] and d['layer'] in (32,74)]+[Point(o['x'],o['y']).buffer(o['diameter']/2,quad_segs=48) for o in fixedvias])
    candidates=[]
    for offset in np.linspace(-.399,.399,81):
        for lateral in np.linspace(-.124,.124,25):
            xy=np.array([q['x'],q['y']])+offset*u+lateral*w
            gap=Point(xy).distance(others)-.2
            if gap>=.151:
                # Prefer outer tips and centered drill where equally feasible.
                score=abs(lateral)*2+abs(offset-.32)+max(0,.2-gap)
                candidates.append(dict(x=float(xy[0]),y=float(xy[1]),offset=float(offset),lateral=float(lateral),gap=gap,score=score,drill_fully_in_original_pad=pg(q).buffer(1e-7).covers(Point(xy).buffer(.1,quad_segs=48))))
    candidates.sort(key=lambda c:c['score']);opts[v['label']]=candidates
    print(v['label'],len(candidates),flush=True)
(H/'qd_via_position_options.json').write_text(json.dumps(opts))
order=sorted(opts,key=lambda key:len(opts[key]));visited=0;chosen={}
def dfs(remaining):
    global visited
    visited+=1
    if visited>200000:return False
    if not remaining:return True
    possible={key:[c for c in opts[key] if all(math.dist([c['x'],c['y']],[other['x'],other['y']])>=.551 for other in chosen.values())] for key in remaining}
    k=min(possible,key=lambda key:len(possible[key]))
    for c in possible[k]:
        chosen[k]=c
        if dfs([key for key in remaining if key!=k]):return True
        chosen.pop(k,None)
    return False
ok=dfs(order)
report=dict(status='OFFLINE_CENTER_CONTAINED_VIA_FEASIBILITY',passed=ok,visited=visited,options={k:len(v) for k,v in opts.items()},chosen=chosen,limitations=['Via centres remain inside original pad rectangles; complete drill containment within the original rectangle is not imposed.','Each drill remains within its annular copper land. The annular land changes total physical pad copper silhouette without changing the bonding-pad primitive.'])
if ok:
    for v in vs:
        c=chosen[v['label']];v.update(x=c['x'],y=c['y'],pad_axis_offset_mm=c['offset'],pad_lateral_offset_mm=c['lateral'],minimum_foreign_pad_gap_mm=c['gap'],drill_fully_in_original_pad=c['drill_fully_in_original_pad'])
        n=str(int(v['label'].split('-')[1]));p['dc_endpoints'][n].update(x=v['x'],y=v['y'])
        for j in p['route_jobs']:
            if j['kind']=='DC' and j['net']==v['net']:j['b']=[v['x'],v['y']]
    report['minimum_via_pair_clearance_mm']=min(math.dist([a['x'],a['y']],[b['x'],b['y']])-(a['diameter']+b['diameter'])/2 for i,a in enumerate(p['vias']) for b in p['vias'][i+1:] if a['net']!=b['net'])
    report['minimum_via_hole_pair_clearance_mm']=min(math.dist([a['x'],a['y']],[b['x'],b['y']])-(a['hole']+b['hole'])/2 for i,a in enumerate(p['vias']) for b in p['vias'][i+1:] if a['net']!=b['net'])
    report['whole_drill_outside_original_rectangle_count']=sum(not c['drill_fully_in_original_pad'] for c in chosen.values())
    (H/'placement_candidate_via_center_contained.json').write_text(json.dumps(p,indent=2))
(H/'qd_via_center_contained_feasibility.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
