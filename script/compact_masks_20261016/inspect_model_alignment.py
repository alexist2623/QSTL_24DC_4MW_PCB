"""Compare native model XY outlines with physical R/C pad axes."""
from pathlib import Path
import sys,json,math,hashlib
from shapely.geometry import Polygon,box
from shapely.affinity import rotate,translate
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path[:0]=[str(ROOT/'script/qd38_carrier_20261010'),str(ROOT/'script/qd38_rotation_20261011')]
from audit_source_model_transforms import inspect
from audit_saved_revision_surface import read_snapshot
pcb=P/(P.name+'.PcbDoc');sch=json.loads((P/'schematic_validation.json').read_text());snap=read_snapshot(pcb,sch);models=inspect(pcb);uid={v:k for k,v in sch['components'].items()};rows=[]
for b in models['bodies']:
    ref=uid.get(b['component_fields'].get('SOURCEUNIQUEID','').strip('\\'),b['component'])
    if ref[0] not in 'RC':continue
    pp=[p for p in snap[0] if p['ref']==ref];a,z=pp;cx=(a['x']+z['x'])/2;cy=(a['y']+z['y'])/2
    angle=math.degrees(math.atan2(z['y']-a['y'],z['x']-a['x']))%180
    w,h=(3.5,1.8) if ref[0]=='C' else (1.6,.8)
    expected=translate(rotate(box(-w/2,-h/2,w/2,h/2),angle,origin=(0,0)),cx,cy)
    g=Polygon(b['outline_mm']);rect=g.minimum_rotated_rectangle;xy=list(rect.exterior.coords);edges=[(math.dist(p,q),math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))%180) for p,q in zip(xy[:-1],xy[1:])];axis=max(edges)[1]
    rows.append(dict(ref=ref,pad_axis_deg=angle,native_model_axis_deg=axis,axis_error_deg=abs((axis-angle+90)%180-90),centre_error_mm=math.dist((cx,cy),(g.centroid.x,g.centroid.y)),native_model_rotation=b['rotation_xyz_deg'],native_bounds=list(g.bounds),expected_bounds=list(expected.bounds),hausdorff_mm=g.hausdorff_distance(expected),outline=b['outline_mm']))
(H/'model_alignment_before.json').write_text(json.dumps(dict(source_sha256=models['source_sha256'],rows=rows),indent=2))
print(json.dumps([{k:v for k,v in r.items() if k not in ('outline','native_bounds','expected_bounds')} for r in rows],indent=2))
