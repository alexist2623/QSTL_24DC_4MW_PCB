"""Choose ZIF contacts by unobstructed path cost, keeping each DC on one layer."""
import json,math,csv
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import Point,box
from skimage.graph import MCP_Geometric
from scipy.optimize import linear_sum_assignment
from route_circuit import GRID,NX,NY,paint,pgeom
from design_geometry import DEST,H

def main():
 p=json.loads((DEST/'circuit_plan.json').read_text());mapping={}
 for layer in (2,4):
  jobs=[j for j in p['route_jobs'] if j['kind']=='DC' and j['layer']==layer]
  ports=sorted([v for v in p['vias'] if v['label'].startswith('J1-') and v['high']==layer],key=lambda d:d['x'])
  goals=[(round(d['y']/GRID),round(d['x']/GRID)) for d in ports];matrix=np.empty((len(jobs),len(ports)))
  for k,j in enumerate(jobs):
   im=Image.new('1',(NX,NY));draw=ImageDraw.Draw(im);r=.155+.125/2+.018
   for d in p['physical_pads']:
    if d['layer']==74 and d['net']!=j['net']:paint(draw,pgeom(d).buffer(r))
   for v in p['vias']:
    if v['net']!=j['net'] and v['low']<=layer<=v['high'] and not (v['label'].startswith('J1-') and v['high']==layer):paint(draw,Point(v['x'],v['y']).buffer(v['diameter']/2+r))
   paint(draw,box(7.05,40.3,12.45,44.7).buffer(r));a=np.asarray(im,dtype=bool).copy();a[:10]=True;a[-10:]=True;a[:,:10]=True;a[:,-10:]=True
   costs=np.ones((NY,NX));costs[a]=np.inf;start=(round(j['b'][1]/GRID),round(j['b'][0]/GRID))
   solver=MCP_Geometric(costs,fully_connected=True);c,_=solver.find_costs([start],goals,find_all_ends=True)
   matrix[k]=[c[g] for g in goals]
   print('ASSIGN_COST',layer,j['net'],flush=True)
  matrix+=np.array([[.02*(i-j)**2 for j in range(len(ports))] for i in range(len(jobs))])
  rows,cols=linear_sum_assignment(matrix)
  for i,j in zip(rows,cols):mapping[ports[j]['label'].split('-')[1]]=jobs[i]['net']
 inv={net:int(pin) for pin,net in mapping.items()}
 assert len(mapping)==38 and len(inv)==38
 oldtop={v['net']:v['label'].split('-')[1] for v in p['vias'] if v['label'].startswith('J1-')}
 for v in p['vias']:
  if v['label'].startswith('J1-'):v['net']=mapping[v['label'].split('-')[1]]
 for d in p['physical_pads']:
  if d['ref']=='J1':d['net']=mapping.get(d['pin'])
 for t in p['tracks']:
  if t['layer']==1:t['net']=mapping[oldtop[t['net']]]
 for j in p['route_jobs']:
  if j['kind']=='DC':
   v=next(v for v in p['vias'] if v['label']==f"J1-{inv[j['net']]}");j['a']=[v['x'],v['y']]
 for n,e in p['dc_endpoints'].items():e['zif_pin']=inv['DC'+str(n).zfill(2)]
 for row in p['pinmap']:row['zif_pin']=inv[row['dc_net']]
 p['nets']={}
 for d in p['physical_pads']:
  if d['ref'] and d['net']:p['nets'].setdefault(d['net'],[]).append(d['ref']+'-'+d['pin'])
 (DEST/'circuit_plan.json').write_text(json.dumps(p,indent=2))
 with (DEST/'pin_mapping.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(p['pinmap'][0]));w.writeheader();w.writerows(p['pinmap'])
 print('REASSIGNED_38_DC',mapping,flush=True)

if __name__=='__main__':main()
