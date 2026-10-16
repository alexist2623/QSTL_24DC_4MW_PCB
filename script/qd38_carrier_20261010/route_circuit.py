"""Route explicit endpoint jobs on fixed copper layers with geometric obstacles."""
import json,math,time,sys,random
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Point,LineString,Polygon,box
from shapely.ops import unary_union
from skimage.graph import MCP_Geometric
from design_geometry import H,ROOT,DEST,polygon

GRID=.025; NX=781;NY=2717;CLEAR=.155

def pgeom(d):
    return Point(d['x'],d['y']).buffer(d['sx']/2,quad_segs=24) if d['shape']=='round' else polygon([d['x'],d['y']],[d['sx'],d['sy']],d['rotation'])

def paint(draw,g):
    if g.is_empty:return
    if hasattr(g,'geoms'):
        for part in g.geoms:paint(draw,part)
    elif isinstance(g,Polygon):
        draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in g.exterior.coords],fill=1)
        for h in g.interiors:draw.polygon([(round(x/GRID),round(y/GRID)) for x,y in h.coords],fill=0)

def compact(path):
    ans=[path[0]];last=None
    for i in range(1,len(path)):
        d=tuple(np.sign(np.array(path[i])-path[i-1]))
        if last is not None and d!=last:ans.append(path[i-1])
        last=d
    ans.append(path[-1]);return [(float(x*GRID),float(y*GRID)) for y,x in ans]

def main():
    plan=json.loads((DEST/'circuit_plan.json').read_text());tracks=list(plan['tracks']);objects={1:[],2:[],4:[],32:[]}
    for d in plan['physical_pads']:
        for layer in objects:
            if d['layer'] in (layer,74):objects[layer].append((d['net'],pgeom(d),f"{d['ref']}-{d['pin']}"))
    for d in plan['vias']:
        for layer in objects:
            if d['low']<=layer<=d['high']:objects[layer].append((d['net'],Point(d['x'],d['y']).buffer(d['diameter']/2,quad_segs=24),d['label']))
    for s in plan['smp']:
        direction=90 if s['y']<42.5 else 270
        for k in range(16):
            offset=k*22.5
            if min(offset,360-offset)<=45:continue
            angle=math.radians(direction+offset)
            x=s['x']+1.05*math.cos(angle);y=s['y']+1.05*math.sin(angle)
            objects[32].append(('GND',Point(x,y).buffer(.125,quad_segs=24),s['ref']+'-reserved-ring'))
    for d in tracks:objects[d['layer']].append((d['net'],LineString([d['a'],d['b']]).buffer(d['width']/2,quad_segs=12),'track'))
    attempt=int(sys.argv[1]) if len(sys.argv)>1 else 0
    old=json.loads((DEST/'routed_plan.json').read_text()) if (DEST/'routed_plan.json').exists() else {}
    failed={f['job']['net'] for f in old.get('unrouted_jobs',[])}
    random.seed(attempt)
    surface_only='--surface-only' in sys.argv
    shuffled=[j for j in plan['route_jobs'] if not surface_only or j['kind']!='DC'];random.shuffle(shuffled)
    jobs=sorted(shuffled,key=lambda j:({'RF':0,'RF_BIAS':1,'QD_FANOUT':2,'RF_QD':3,'DC':4}[j['kind']],0 if j['net'] in failed and attempt else 1, -math.dist(j['a'],j['b']) if attempt==1 else random.random() if attempt else math.dist(j['a'],j['b'])))
    failures=[];completed=list(plan.get('dc_routed_jobs',[])) if surface_only else [];bounds=box(.20,.20,19.30,67.70)
    freeports={l:[d for d in plan['vias'] if d['label'].startswith('J1-') and d['high']==l] for l in (2,4)}
    assignments={}
    for k,j in enumerate(jobs):
        t0=time.monotonic();w=j['width'];layer=j['layer'];net=j['net']
        dynamic=j['kind']=='DC'
        portlabels={d['label'] for d in freeports.get(layer,[])} if dynamic else set()
        obs=[g for n,g,label in objects[layer] if n!=net and label not in portlabels]
        # No routed signal crosses the non-through sample pocket projection.
        obs.append(box(9.75-2.70,42.5-2.20,9.75+2.70,42.5+2.20))
        im=Image.new('1',(NX,NY));draw=ImageDraw.Draw(im)
        for g in obs:paint(draw,g.buffer(CLEAR+w/2+.018,quad_segs=8))
        a=np.asarray(im,dtype=bool).copy();a[:10,:]=True;a[-10:,:]=True;a[:,:10]=True;a[:,-10:]=True
        costs=np.ones(a.shape,dtype=np.float64);costs[a]=np.inf
        start=(round(j['a'][1]/GRID),round(j['a'][0]/GRID));end=(round(j['b'][1]/GRID),round(j['b'][0]/GRID))
        goals=[end]
        if dynamic:
            start=end
            a[:round(9.5/GRID),:]=True;costs[a]=np.inf
            goals=[(round(9.5/GRID),round(d['x']/GRID)) for d in freeports[layer]]
            goals=[g for g in goals if not a[g]]
            end=goals[0] if goals else start
        # Endpoints are explicitly required to be in legal copper, not carved out.
        if a[start] or a[end]:
            failures.append(dict(job=j,reason='blocked endpoint',start_blocked=bool(a[start]),end_blocked=bool(a[end])))
            print(k,net,j['kind'],'BLOCKED_ENDPOINT',flush=True);continue
        solver=MCP_Geometric(costs,fully_connected=True)
        result,_=solver.find_costs([start],goals,find_all_ends=False)
        if dynamic:end=min(goals,key=lambda q:result[q]) if goals else start
        if not math.isfinite(result[end]):
            failures.append(dict(job=j,reason='no legal path'));print(k,net,j['kind'],'NO_PATH',flush=True);continue
        points=compact(solver.traceback(end))
        chosen=None
        if dynamic:
            chosen=min(freeports[layer],key=lambda d:abs(d['x']/GRID-end[1]))
            obs.extend(Point(d['x'],d['y']).buffer(d['diameter']/2,quad_segs=24) for d in freeports[layer] if d is not chosen)
        copper=LineString(points).buffer(w/2,quad_segs=16)
        mingap=min(copper.distance(g) for g in obs)
        if mingap<.15-1e-7:
            failures.append(dict(job=j,reason='continuous geometry clearance',gap=mingap));print(k,net,'FAILED_GAP',mingap,flush=True);continue
        for x,y in zip(points,points[1:]):tracks.append(dict(net=net,layer=layer,a=x,b=y,width=w))
        objects[layer].append((net,copper,'route'));completed.append(dict(job=j,points=points,minimum_gap=mingap))
        if chosen:
            freeports[layer].remove(chosen);assignments[chosen['label'].split('-')[1]]=net
            tail=LineString([points[-1],[chosen['x'],chosen['y']]]).buffer(w/2,quad_segs=16)
            tracks.append(dict(net=net,layer=layer,a=points[-1],b=[points[-1][0],chosen['y']],width=w))
            objects[layer].append((net,tail,'route'))
            for ll in objects:objects[ll]=[(net if label==chosen['label'] else nn,g,label) for nn,g,label in objects[ll]]
        print(k,net,j['kind'],'OK',len(points),f'{mingap:.4f}',f'{time.monotonic()-t0:.2f}s',flush=True)
        plan.update(tracks=tracks,routed_jobs=completed,unrouted_jobs=failures+jobs[k+1:])
        (H/'routing_progress.json').write_text(json.dumps(plan,indent=2))
    plan.update(tracks=tracks,routed_jobs=completed,unrouted_jobs=failures,routing_complete=not failures,dynamic_zif_assignment=assignments)
    (DEST/'routed_plan.json').write_text(json.dumps(plan,indent=2))
    print('ROUTING_RESULT',len(completed),'/',len(jobs),'FAILURES',len(failures),flush=True)

if __name__=='__main__':main()
