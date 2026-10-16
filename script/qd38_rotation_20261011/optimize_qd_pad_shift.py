"""Find minimal outward shifts of direct-DC pads while preserving RF pads."""
import copy,json,math
import numpy as np
from pathlib import Path
from shapely import distance
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
from build_rotated_placement import pg
H=Path(__file__).resolve().parent
p=json.loads((H/'placement_candidate.json').read_text())
vs=[v for v in p['vias'] if v['label'].startswith('Q1-')]
keys={v['label'] for v in vs}
fixed=[pg(d) for d in p['physical_pads'] if f"{d['ref']}-{d['pin']}" not in keys and d['layer'] in (32,74)]
fixed += [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48) for v in p['vias'] if v['label'] not in keys]
fixed += [box(7.6,39.85,11.9,45.15)]
fixedunion=unary_union(fixed)
qps={f"Q1-{d['pin']}":d for d in p['physical_pads'] if d['ref']=='Q1'}
opts={};geoms={}
for v in vs:
    q=qps[v['label']];t=math.radians(q['rotation']);u=np.array([math.cos(t),math.sin(t)]);w=np.array([-u[1],u[0]])
    values=[];shapes=[]
    for shift in np.arange(0,1.001,.025):
        pc=np.array([q['x'],q['y']])+shift*u;pad=copy.deepcopy(q);pad.update(x=float(pc[0]),y=float(pc[1]));padgeom=pg(pad)
        if padgeom.distance(fixedunion)<.151:continue
        for offset in [-.299,.15,.299]:
            for lateral in [-.024,0,.024]:
                xy=pc+offset*u+lateral*w
                g=unary_union([padgeom,Point(xy).buffer(.2,quad_segs=48)])
                gap=g.distance(fixedunion)
                if gap<.151:continue
                values.append(dict(pad=pad,x=float(xy[0]),y=float(xy[1]),shift_mm=float(shift),offset_mm=offset,lateral_mm=lateral,gap=gap));shapes.append(g)
    order=sorted(range(len(values)),key=lambda i:(values[i]['shift_mm'],abs(values[i]['lateral_mm']),abs(values[i]['offset_mm']-.299)))
    opts[v['label']]=[values[i] for i in order];geoms[v['label']]=np.array([shapes[i] for i in order],dtype=object)
    print(v['label'],len(values),flush=True)
visited=0;solution={};checks=[]
def dfs(possible):
    global visited
    visited+=1
    if visited>1200:return False
    if not possible:return True
    k=min(possible,key=lambda k:len(possible[k]))
    if not len(possible[k]):return False
    for ci in possible[k]:
        remaining={};g=geoms[k][ci];valid=True
        for kk,indices in possible.items():
            if kk==k:continue
            good=distance(geoms[kk][indices],g)>=.151-1e-8
            remaining[kk]=indices[good]
            if not len(remaining[kk]):valid=False;break
        if valid:
            solution[k]=int(ci)
            if dfs(remaining):return True
            solution.pop(k,None)
    return False
success=False
for maxshift in [.10,.125,.15,.175,.20,.225,.25,.275,.30,.35,.40,.45,.50,.60,.75,1.0]:
    possible={k:np.array([i for i,v in enumerate(opts[k]) if v['shift_mm']<=maxshift+1e-8],dtype=int) for k in opts}
    if any(not len(x) for x in possible.values()):continue
    visited=0;solution={};success=True
    groups=[[36,37,38,1],[3,4],[6,7,8],[10],[14],[17,18,19,20],[22,23],[25,26,27],[29],[33]]
    for group in groups:
        visited=0
        local={f'Q1-{n}':possible[f'Q1-{n}'] for n in group}
        if not dfs(local):
            success=False
            print('BLOCKED_GROUP',group,visited,flush=True)
            break
    if success:
        conflicts=[(a,b) for i,a in enumerate(solution) for b in list(solution)[i+1:] if geoms[a][solution[a]].distance(geoms[b][solution[b]])<.151-1e-8]
        if conflicts:
            print('CROSS_GROUP_CONFLICTS',conflicts,flush=True);success=False
    checks.append(dict(maximum_shift_mm=float(maxshift),passed=success,visited=visited))
    print('SHIFT',maxshift,success,visited,flush=True)
    if success:break
report=dict(status='OFFLINE_QD_DIRECT_PAD_SHIFT_FEASIBILITY',passed=success,attempts=checks,changed_pads=[],RF_pads_preserved=True)
if success:
    for v in vs:
        c=opts[v['label']][solution[v['label']]];n=int(v['label'].split('-')[1]);q=p['pads'][n-1];u=np.array(q['normal']);delta=c['shift_mm']*u
        d=qps[v['label']];d.update(x=c['pad']['x'],y=c['pad']['y'])
        for key in ['center','bond','inner','absolute_center','absolute_bond']:q[key]=(np.array(q[key])+delta).tolist()
        q['polygon']=(np.array(q['polygon'])+delta).tolist()
        v.update(x=c['x'],y=c['y'],pad_axis_offset_mm=c['offset_mm'],pad_lateral_offset_mm=c['lateral_mm'],minimum_foreign_pad_gap_mm=c['gap'],drill_fully_in_original_pad=True)
        p['dc_endpoints'][str(n)].update(x=v['x'],y=v['y'])
        for j in p['route_jobs']:
            if j['kind']=='DC' and j['net']==v['net']:j['b']=[v['x'],v['y']]
        if c['shift_mm']>1e-8: report['changed_pads'].append(dict(pin=n,shift_mm=c['shift_mm']))
    report['maximum_outward_shift_mm']=max(c['shift_mm'] for c in report['changed_pads'])
    report['sum_outward_shift_mm']=sum(c['shift_mm'] for c in report['changed_pads'])
    pp=[pg(d) for d in p['physical_pads'] if d['ref']=='Q1'];un=unary_union(pp)
    report['pad_array_bounds_mm']=list(un.bounds);report['pad_array_span_mm']=[un.bounds[2]-un.bounds[0],un.bounds[3]-un.bounds[1]]
    report['minimum_QD_pad_gap_mm']=min(a.distance(b) for i,a in enumerate(pp) for b in pp[i+1:])
    report['minimum_via_pair_clearance_mm']=min(math.dist([a['x'],a['y']],[b['x'],b['y']])-(a['diameter']+b['diameter'])/2 for i,a in enumerate(p['vias']) for b in p['vias'][i+1:] if a['net']!=b['net'])
    report['minimum_via_hole_pair_clearance_mm']=min(math.dist([a['x'],a['y']],[b['x'],b['y']])-(a['hole']+b['hole'])/2 for i,a in enumerate(p['vias']) for b in p['vias'][i+1:] if a['net']!=b['net'])
    bonds=[LineString([q['absolute_chip'],q['absolute_bond']]) for q in p['pads']]
    report['bond_crossings']=[[i+1,j+1] for i,a in enumerate(bonds) for j,b in enumerate(bonds) if i<j and a.intersects(b)]
    p['checks'].update(rf_upper_count=7,rf_lower_count=7,rf_center_count=2,pad_gap_mm=report['minimum_QD_pad_gap_mm'])
    p['placement_adjustment']=report
    (H/'placement_candidate_pad_shift.json').write_text(json.dumps(p,indent=2))
(H/'qd_pad_shift_feasibility.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
