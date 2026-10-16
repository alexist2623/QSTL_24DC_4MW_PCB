"""Rip up and negotiate single-layer routes; never declare overlapping routes valid."""
import json,math,time,random,sys
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Point,LineString,box
from skimage.graph import MCP_Geometric
from route_circuit import GRID,NX,NY,CLEAR,paint,pgeom,compact
from design_geometry import H,DEST

def mask(g):
 im=Image.new('1',(NX,NY));paint(ImageDraw.Draw(im),g);return np.asarray(im,dtype=bool).copy()

def main():
 p=json.loads((DEST/'circuit_plan.json').read_text());old=json.loads((DEST/'routed_plan.json').read_text())
 fixedjobs=[r for r in old['routed_jobs'] if r['job']['kind'] in ('RF','RF_BIAS','QD_FANOUT')]
 assert len(fixedjobs)==54,len(fixedjobs)
 fixedtracks=list(p['tracks'])
 for r in fixedjobs:
  j=r['job']
  fixedtracks.extend(dict(net=j['net'],layer=j['layer'],width=j['width'],a=a,b=b) for a,b in zip(r['points'],r['points'][1:]))
 jobs=[j for j in p['route_jobs'] if j['kind'] in ('RF_QD','DC')]
 surface_only='--surface-only' in sys.argv
 completed=list(p.get('dc_routed_jobs',[])) if surface_only else [];failure=[]
 for layer in ((32,) if surface_only else (32,2,4)):
  jj=[j for j in jobs if j['layer']==layer];static=[]
  for d in p['physical_pads']:
   if d['layer'] in (layer,74):static.append((d['net'],pgeom(d)))
  for d in p['vias']:
   if d['low']<=layer<=d['high']:static.append((d['net'],Point(d['x'],d['y']).buffer(d['diameter']/2,quad_segs=20)))
  if layer==32:
   for s in p['smp']:
    direction=90 if s['y']<42.5 else 270
    for k in range(16):
     offset=k*22.5
     if min(offset,360-offset)<=45:continue
     angle=math.radians(direction+offset)
     static.append(('GND',Point(s['x']+1.05*math.cos(angle),s['y']+1.05*math.sin(angle)).buffer(.125,quad_segs=24)))
  for t in fixedtracks:
   if t['layer']==layer:static.append((t['net'],LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=12)))
  static.append((None,box(7.05,40.3,12.45,44.7)))
  hard=[];starts=[];ends=[]
  for j in jj:
   im=Image.new('1',(NX,NY));draw=ImageDraw.Draw(im)
   for net,g in static:
    if net!=j['net']:paint(draw,g.buffer(CLEAR+j['width']/2+.018,quad_segs=8))
   a=np.asarray(im,dtype=bool).copy();a[:10]=True;a[-10:]=True;a[:,:10]=True;a[:,-10:]=True
   hard.append(a);starts.append((round(j['a'][1]/GRID),round(j['a'][0]/GRID)));ends.append((round(j['b'][1]/GRID),round(j['b'][0]/GRID)))
   assert not a[starts[-1]] and not a[ends[-1]],(layer,j['net'],'blocked fixed geometry')
  occ=np.zeros((NY,NX),dtype=np.int16);history=np.zeros((NY,NX),dtype=np.float32)
  paths=[None]*len(jj);soft=[None]*len(jj);geoms=[None]*len(jj);todo=list(range(len(jj)))
  random.seed(37+layer)
  for iteration in range(35):
   random.shuffle(todo);factor=5+iteration*4
   for ix in todo:
    if soft[ix] is not None:occ-=soft[ix]
    costs=1.+occ.astype(float)*factor+history*(2+iteration*.3);costs[hard[ix]]=np.inf
    solver=MCP_Geometric(costs,fully_connected=True);result,_=solver.find_costs([starts[ix]],[ends[ix]],find_all_ends=False)
    if not math.isfinite(result[ends[ix]]):raise ValueError((layer,jj[ix]['net'],'no path through fixed geometry'))
    path=compact(solver.traceback(ends[ix]));paths[ix]=path
    geoms[ix]=LineString(path).buffer(jj[ix]['width']/2,quad_segs=12)
    soft[ix]=mask(LineString(path).buffer(.125+CLEAR+.018,quad_segs=8));occ+=soft[ix]
   conflicts=[];conflict_region=[]
   for a,g in enumerate(geoms):
    for b in range(a+1,len(geoms)):
     d=g.distance(geoms[b])
     if d<.15-1e-7:
      conflicts.append((a,b,d));conflict_region.append(g.buffer(.16).intersection(geoms[b].buffer(.16)))
   print('LAYER',layer,'ITER',iteration,'CONFLICTS',len(conflicts),'MIN',min([d for a,b,d in conflicts],default=.15),flush=True)
   if not conflicts:break
   for g in conflict_region:history+=mask(g)*.8
   todo=sorted({i for a,b,d in conflicts for i in (a,b)})
   if iteration%5==4:todo=list(range(len(jj)))
   snapshot=dict(layer=layer,iteration=iteration,conflicts=conflicts,jobs=jj,paths=paths)
   (H/f'negotiated_L{layer}_progress.json').write_text(json.dumps(snapshot,indent=2))
  for ix,j in enumerate(jj):
   minimum=min(g.distance(geoms[ix]) for net,g in static if net!=j['net'])
   assert minimum>=.15-1e-6,(layer,j['net'],minimum)
   completed.append(dict(job=j,points=paths[ix],minimum_gap=minimum))
  failure.extend(dict(layer=layer,net_a=jj[a]['net'],net_b=jj[b]['net'],gap_mm=d) for a,b,d in conflicts)
  (H/f'negotiated_L{layer}.json').write_text(json.dumps(dict(jobs=jj,paths=paths,conflicts=conflicts),indent=2))
 tracks=list(fixedtracks)
 for r in completed:
  j=r['job'];tracks.extend(dict(net=j['net'],layer=j['layer'],width=j['width'],a=a,b=b) for a,b in zip(r['points'],r['points'][1:]))
 # DC tracks are already present in p['tracks'] during a surface-only run.
 seen=set();unique=[]
 for t in tracks:
  key=(t['net'],t['layer'],t['width'],tuple(t['a']),tuple(t['b']))
  if key not in seen:unique.append(t);seen.add(key)
 tracks=unique
 p.update(tracks=tracks,routed_jobs=fixedjobs+completed,unrouted_jobs=[],clearance_conflicts=failure,routing_complete=not failure)
 (DEST/'negotiated_plan.json').write_text(json.dumps(p,indent=2))
 print('FINAL_CLEARANCE_CONFLICTS',len(failure),flush=True)

if __name__=='__main__':main()
