"""Measure QD terminal-via land protrusion before and after pad widening."""
from pathlib import Path
import json,sys,math,hashlib,csv
from shapely.geometry import Point
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,pad_shape
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/(P.name+'.PcbDoc')
pads,regions,tracks,vias,outline=read_snapshot(H/'baseline'/(P.name+'.PcbDoc'),sch)
saved=read_snapshot(pcb,sch);actual={p['pin']:p for p in saved[0] if p['ref']=='Q1'}
assert len(actual)==38 and all(abs(p['sy']-.26)<.000003 for p in actual.values())
assert sorted((v['net'],v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in vias if v['net']!='GND')==sorted((v['net'],v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in saved[3] if v['net']!='GND')
rows=[]
for p in pads:
    if p['ref']!='Q1':continue
    for v in vias:
        if v['net']!=p['net'] or v['net']=='GND' or v['high']!=32:continue
        if p['geometry'].distance(Point(v['x'],v['y']))>.001:continue
        angle=math.radians(p['rotation']);dx=v['x']-p['x'];dy=v['y']-p['y']
        u=dx*math.cos(angle)+dy*math.sin(angle);w=-dx*math.sin(angle)+dy*math.cos(angle);r=v['diameter']/2
        before=max(0,abs(u)+r-p['sx']/2,abs(w)+r-p['sy']/2)
        after=max(0,abs(u)+r-actual[p['pin']]['sx']/2,abs(w)+r-actual[p['pin']]['sy']/2)
        rows.append(dict(pad=p['pin'],net=p['net'],via_diameter_mm=v['diameter'],drill_mm=v['hole'],local_offset_mm=[u,w],before_protrusion_mm=before,after_protrusion_mm=after,required_width_mm=2*(abs(w)+r),long_axis_protrusion_mm=max(0,abs(u)+r-p['sx']/2)))
rows.sort(key=lambda r:int(r['pad']))
result=dict(scope='Verified saved 0.260 mm pads and unchanged native terminal via positions',source_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),count=len(rows),still_protruding=sum(r['after_protrusion_mm']>2.54e-6 for r in rows),rows=rows)
(H/'via_protrusion.json').write_text(json.dumps(result,indent=2))
with (P/'Bond_Pad_Width_20261017/Via_Protrusion.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=[k for k in rows[0] if k!='local_offset_mm']);writer.writeheader();writer.writerows({k:v for k,v in r.items() if k!='local_offset_mm'} for r in rows)
print(json.dumps(result,indent=2))
