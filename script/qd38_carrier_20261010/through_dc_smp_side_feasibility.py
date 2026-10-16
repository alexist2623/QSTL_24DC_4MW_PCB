"""Read-only pad/hole feasibility of the corrected seven-row 3/2/2/2/2/2/3 SMP grid."""
from pathlib import Path
import collections
import hashlib
import json
import math
from functools import lru_cache
from shapely.geometry import Point, box, Polygon
from shapely.affinity import rotate, translate

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
PCB=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
S=json.loads((H/'through_dc_saved_native_snapshot.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=sha(PCB)
assert before==S['source_sha256']
template=[p for p in S['pads'] if p['component']=='SMP02']
origin=next(c for c in S['components'] if c['designator']=='SMP02')
QD=[p for p in S['pads'] if p['component']=='Q1']
mounts=[p for p in S['pads'] if p['component'] is None]
dc_vias=[v for v in S['vias'] if v['net'] and v['net'].startswith('DC')]
cavity=box(7.1,40.35,12.4,44.65)
board=Polygon(S['board_outline'])
body_template=Polygon(next(b for b in S['bodies'] if b['component']=='SMP02')['points'])

def geom(p,hole=False):
 return cached_geom(p['x'],p['y'],p['hole'] if hole else p['size_x'],p['size_y'],p['rotation'],1 if hole else p['shape'])

@lru_cache(None)
def cached_geom(x,y,sx,sy,rotation,shape):
 if shape==1:return Point(x,y).buffer(sx/2,quad_segs=128)
 return translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),rotation,origin=(0,0)),x,y)

def via_geom(v):
 return cached_geom(v['x'],v['y'],v['diameter'],v['diameter'],0,1)

def evaluate():
 positions=[]
 for row,y in enumerate([24.5,30.5,36.5,42.5,48.5,54.5,60.5]):
  for x in ((3.75,9.75,15.75) if row in (0,6) else (3.75,15.75)):
   positions.append(dict(ref=f'SMP_R{row}_{x}',x=x,y=y))
 pads=[]
 for c in positions:
  for old in template:
   p=dict(old,component=c['ref'],x=c['x']+old['x']-origin['x'],y=c['y']+old['y']-origin['y'])
   p['net']='GND' if old['net']=='GND' else c['ref']+'_SIGNAL'
   pads.append(p)
 def minpair(aa,bb,ga=geom,gb=geom):
  out=None
  for a in aa:
   for b in bb:
    val=ga(a).distance(gb(b))
    if out is None or val<out['gap_mm']:
     out=dict(gap_mm=val,a=[a.get('component',a.get('net')),a.get('number'),a['x'],a['y']],b=[b.get('component',b.get('net')),b.get('number'),b['x'],b['y']],overlap_mm2=ga(a).intersection(gb(b)).area)
  return out
 qd=minpair(pads,QD)
 qdcavity=min((geom(p).distance(cavity),p['component'],p['number']) for p in pads)
 qdcavityholes=min((geom(p,True).distance(cavity),p['component'],p['number']) for p in pads)
 min_other_holes=None
 min_other_copper=None
 for i,p in enumerate(pads):
  for q in pads[i+1:]:
   if p['component']==q['component']:continue
   d=geom(p,True).distance(geom(q,True))
   if min_other_holes is None or d<min_other_holes[0]:min_other_holes=(d,p['component'],p['number'],q['component'],q['number'])
   if p['net']==q['net']:continue
   d=geom(p).distance(geom(q))
   if min_other_copper is None or d<min_other_copper[0]:min_other_copper=(d,p['component'],p['number'],q['component'],q['number'])
 clashes=[]
 for p in pads:
  for v in dc_vias:
   g=via_geom(v)
   gap=geom(p).distance(g)
   if gap<.15:
    clashes.append(dict(smp=p['component'],pin=p['number'],dc_net=v['net'],via_xy=[v['x'],v['y']],gap_mm=gap,overlap_mm2=geom(p).intersection(g).area))
 bodies=[(c['ref'],translate(body_template,c['x']-origin['x'],c['y']-origin['y'])) for c in positions]
 return dict(positions=positions,count=len(positions),upper_count=sum(c['y']>42.5 for c in positions),center_count=sum(c['y']==42.5 for c in positions),lower_count=sum(c['y']<42.5 for c in positions),
  minimum_SMP_land_to_QD_pad=qd,minimum_SMP_land_to_cavity=qdcavity,minimum_SMP_hole_to_cavity=qdcavityholes,
  minimum_cross_SMP_hole_gap=min_other_holes,minimum_cross_SMP_foreign_copper_gap=min_other_copper,
  minimum_SMP_to_mounting_hole=minpair(pads,mounts,lambda p:geom(p,True),lambda p:geom(p,True)),
  minimum_SMP_land_board_edge_mm=min(board.boundary.distance(geom(p)) for p in pads),
  minimum_SMP_hole_board_edge_mm=min(board.boundary.distance(geom(p,True)) for p in pads),
  minimum_SMP_to_existing_DC_via=minpair(pads,dc_vias,geom,via_geom),
  minimum_body_to_body_mm=min(a.distance(b) for i,(_,a) in enumerate(bodies) for _,b in bodies[i+1:]),
  minimum_body_to_board_edge_mm=min(board.boundary.distance(b) for _,b in bodies),
  minimum_body_projection_to_cavity_mm=min(b.distance(cavity) for _,b in bodies),
  minimum_body_projection_to_QD_pad_mm=min(b.distance(geom(p)) for _,b in bodies for p in QD),
  body_projection_QD_pad_overlap_mm2=sum(b.intersection(geom(p)).area for _,b in bodies for p in QD),
  existing_DC_via_clearance_conflicts=clashes)

if __name__=='__main__':
 report=dict(native_sha256=before,board_bounds_mm=list(board.bounds),row_counts=[3,2,2,2,2,2,3],nominal=evaluate(),
  fixed_geometry='Saved QD rotated bonding pads, 5.3x4.3 mm cavity and original mounting holes retained. Other SMP, RF tracks, masks, shields and bias components must be reassigned/rerouted separately.',
  layer_note='SMP components are on Top, but all five pads and 0.75 mm drills are multilayer; their lands and holes must clear Bottom QD copper and the Bottom pocket despite opposite component faces.',
  source_unchanged=sha(PCB)==before)
 (H/'seven_rows_3222223_feasibility.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
