"""Compute RF assignment from shortest paths around resistor body keepouts.

The output changes net assignment only and preserves the passed DC geometry.
It is an offline proposal; a subsequent RF router must verify all clearances.
"""
import copy,hashlib,json,math,re,time,itertools
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.optimize import linear_sum_assignment
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
from skimage.graph import MCP_Geometric
from build_rotated_placement import pg
H=Path(__file__).resolve().parent
GRID=.025;NX=781;NY=2717;RADIUS=.232
def mask(g):
    image=Image.new('1',(NX,NY));draw=ImageDraw.Draw(image)
    def paint(g):
        if g.is_empty:return
        if hasattr(g,'geoms'):
            for v in g.geoms:paint(v)
        elif isinstance(g,Polygon):
            draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in g.exterior.coords],fill=1)
            for hole in g.interiors:draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in hole.coords],fill=0)
    paint(g);return np.asarray(image,dtype=bool).copy()
def remap(plan,mapping):
    def walk(value):
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,dict):return {walk(k):walk(v) for k,v in value.items()}
        if isinstance(value,str) and re.fullmatch('DC[0-9]{2}',value) and int(value[2:]) in mapping:return f'DC{mapping[int(value[2:])]:02}'
        return value
    p=walk(plan);old_end=copy.deepcopy(plan['dc_endpoints']);old_pin={r['qd_pad']:copy.deepcopy(r) for r in plan['pinmap']}
    inverse={q:g for g,q in mapping.items()}
    for d in p['physical_pads']:
        if d['ref'] and d['ref'].startswith(('R','C')):
            group=int(d['ref'][1:]);q=mapping[group]
            if d['ref'].startswith('R'):d['net']=f'MW{q:02}' if d['pin']=='1' else f'DC{q:02}'
            elif d['pin']=='2':d['net']=f'MW{q:02}'
    for job in p['route_jobs']:
        if job['net'].startswith('MW'):
            group=int(job['net'][2:]);q=mapping[group];job['net']=f'MW{q:02}'
            if job['kind']=='RF_QD':
                pad=p['pads'][q-1];job['a']=[x+.15*u for x,u in zip(pad['absolute_center'],pad['normal'])]
    for s in p['smp']:
        group=int(s['ref'][3:]);s.update(q=mapping[group],channel_id=group,qd_pad=mapping[group])
    for c in p['components']:
        if c['ref'].startswith('SMP'):
            group=int(c['ref'][3:]);c.update(q=mapping[group],channel_id=group,qd_pad=mapping[group])
    for index,row in enumerate(p['pinmap']):
        q=row['qd_pad']
        if q not in inverse:continue
        group=inverse[q];p['pinmap'][index]=dict(old_pin[group],qd_pad=q,chip_net=p['pads'][q-1]['net'],dc_net=f'DC{q:02}',rf_net=f'MW{q:02}',smp=f'SMP{group:02}',resistor=f'R{group:02}',capacitor=f'C{group:02}')
        p['dc_endpoints'][str(q)]=old_end[str(group)]
    p['nets']={}
    for d in p['physical_pads']:
        if d['ref'] and d['net']:p['nets'].setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
    p['rf_physical_group_to_qd_assignment']={str(g):q for g,q in mapping.items()}
    p['status']='GEODESIC_RF_ASSIGNMENT_PROPOSAL_DC_GEOMETRY_PRESERVED'
    p.pop('placement_validation',None)
    return p
def main():
    source=H/'dc_routed_candidate.json';plan=json.loads(source.read_text())
    rf=sorted(s['q'] for s in plan['smp']);qp={int(d['pin']):d for d in plan['physical_pads'] if d['ref']=='Q1' and int(d['pin']) in rf}
    static=[(d['net'],pg(d),f"{d['ref']}-{d['pin']}") for d in plan['physical_pads'] if d['layer'] in (32,74)]
    static += [(v['net'],Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48),v['label']) for v in plan['vias']]
    static.append((None,box(7.6,39.85,11.9,45.15),'cavity'))
    hulls={}
    for group in rf:
        pads=[d for d in plan['physical_pads'] if d['ref']==f'R{group:02}'];hulls[group]=unary_union([pg(d) for d in pads]).convex_hull
    common=unary_union([g for _,g,_ in static]+list(hulls.values()))
    commonmask=mask(common.buffer(RADIUS,quad_segs=12))
    goals=[];goaldata=[]
    for q in rf:
        pad=plan['pads'][q-1];center=np.array(pad['absolute_center']);normal=np.array(pad['normal']);inner=center+.15*normal
        obstacles=unary_union([g for _,g,label in static if label!=f'Q1-{q}']+list(hulls.values()))
        candidates=[]
        for offset in np.linspace(.65,1.6,39):
            xy=center+offset*normal;goal=tuple(round(v/GRID) for v in reversed(xy));xy=np.array(goal[::-1])*GRID
            if commonmask[goal]:continue
            gap=LineString([inner,xy]).buffer(.055,quad_segs=32).distance(obstacles)
            if gap>=.152:candidates.append((offset,goal,xy,gap))
        if not candidates:raise ValueError(('No exterior QD port',q))
        offset,goal,xy,gap=candidates[0];goals.append(goal);goaldata.append(dict(qd_pad=q,xy=xy.tolist(),offset=float(offset),neck_gap_mm=gap))
    edge=mask(box(-1,-1,21,70).difference(Polygon(plan['board_outline']).buffer(-.22)))
    matrix=np.zeros((16,16));paths={}
    for i,group in enumerate(rf):
        net=f'MW{group:02}';keepouts=[g for n,g,label in static if n!=net or label.startswith('Q1-')]
        for g,hull in hulls.items():
            own=unary_union([pg(d) for d in plan['physical_pads'] if d['ref']==f'R{g:02}' and d['net']==net])
            keepouts.append(hull.difference(own))
        hard=mask(unary_union(keepouts).buffer(RADIUS,quad_segs=12))|edge
        r=next(d for d in plan['physical_pads'] if d['ref']==f'R{group:02}' and d['pin']=='1')
        start=tuple(round(v/GRID) for v in (r['y'],r['x']))
        if hard[start]:raise ValueError(('Blocked resistor RF endpoint',group))
        costs=np.ones((NY,NX),dtype=float);costs[hard]=np.inf
        solver=MCP_Geometric(costs,fully_connected=True);dist,_=solver.find_costs([start],goals,find_all_ends=True)
        for j,goal in enumerate(goals):
            matrix[i,j]=dist[goal]*GRID
            if math.isfinite(matrix[i,j]):paths[f'{group}:{rf[j]}']=[[float(x*GRID),float(y*GRID)] for y,x in solver.traceback(goal)]
        print('GEODESIC',group,'reachable',sum(np.isfinite(matrix[i])),flush=True)
    rows,cols=linear_sum_assignment(matrix)
    assignment={rf[i]:rf[j] for i,j in zip(rows,cols)}
    variants=[]
    for flags in itertools.product([False,True],repeat=2):
        amap=dict(assignment)
        for use,(a,b) in zip(flags,[(11,15),(34,35)]):
            if use:amap[a],amap[b]=amap[b],amap[a]
        crossings=[]
        for i,a in enumerate(rf):
            for b in rf[i+1:]:
                gap=LineString(paths[f'{a}:{amap[a]}']).distance(LineString(paths[f'{b}:{amap[b]}']))-.11
                if gap<.15:crossings.append(dict(a=a,b=b,gap_mm=gap))
        length=sum(matrix[rf.index(g),rf.index(q)] for g,q in amap.items())
        variants.append(dict(mapping=amap,conflicts=crossings,length_mm=float(length)))
    best=min(variants,key=lambda v:(len(v['conflicts']),v['length_mm']))
    best_candidate=remap(plan,best['mapping']);best_out=H/'placement_rf_geodesic_uncrossed.json';best_out.write_text(json.dumps(best_candidate,indent=2))
    (H/'rf_geodesic_uncrossing_variants.json').write_text(json.dumps(dict(variants=variants,best=best,candidate=str(best_out),candidate_sha256=hashlib.sha256(best_out.read_bytes()).hexdigest()),indent=2))
    candidate=remap(plan,assignment)
    out=H/'placement_rf_geodesic_assignment.json';out.write_text(json.dumps(candidate,indent=2))
    chosen={str(g):paths[f'{g}:{q}'] for g,q in assignment.items()}
    conflicts=[]
    for ia,(a,aa) in enumerate(chosen.items()):
        for b,bb in list(chosen.items())[ia+1:]:
            gap=LineString(aa).distance(LineString(bb))-.11
            if gap<.15:conflicts.append(dict(a=a,b=b,gap_mm=gap))
    report=dict(status=candidate['status'],source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate=str(out),candidate_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),rf_group_to_qd_pad=assignment,total_path_length_mm=float(matrix[rows,cols].sum()),diagonal_original_assignment_mm=float(np.trace(matrix)),RF_terminals=rf,cost_matrix_mm=matrix.tolist(),exterior_QD_ports=goaldata,selected_shortest_paths=chosen,shortest_path_conflicts=conflicts,physical_positions_changed=False,DC_track_coordinates_preserved=True,RF_vias_added=0,limitations=['This is minimum individual geodesic cost assignment, not a completed concurrent RF routing solution.','QD exterior ports avoid walking through unrelated bonding pads; RF router must still connect the actual interior QD endpoints.','All resistor inter-pad convex hulls were blocked; only the source RF pad itself is excluded from its own keepout.'])
    (H/'rf_geodesic_assignment_report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k not in ('cost_matrix_mm','selected_shortest_paths','exterior_QD_ports')},indent=2))
if __name__=='__main__':main()
