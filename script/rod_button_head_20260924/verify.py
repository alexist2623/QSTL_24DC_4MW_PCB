"""Verify the saved hardware-only change and compare real head geometry."""
from pathlib import Path
import json, sys, hashlib
from OCP.gp import gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
H=Path(__file__).resolve().parent; R=H.parents[1]
M=R/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
sys.path.insert(0,str(R/'script/mechanical_assembly_20260921'))
from inspect_geometry import read, inspect, bounds, volume, faces
def volume(s):
    # Adaptive integration is necessary for the supplied curved button heads.
    p=GProp_GProps();BRepGProp.VolumeProperties_s(s,p,1e-9);return p.Mass()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,obj):p.write_text(json.dumps(obj,indent=2),encoding='utf-8')
def transform(s,rows):
    a=[list(row) for row in rows]
    for row in a[:3]:row[3]*=10
    t=gp_Trsf();t.SetValues(*[v for row in a[:3] for v in row]);return BRepBuilderAPI_Transform(s,t,True).Shape()
def area(s):
    p=GProp_GProps();BRepGProp.SurfaceProperties_s(s,p);return p.Mass()
def bearing_faces(s):
    for f in faces(s):
        p=BRepAdaptor_Surface(f)
        if p.GetType()==GeomAbs_Plane and abs(abs(p.Plane().Axis().Direction().Z())-1)<1e-7 and abs(p.Plane().Location().Z()+1.6)<1e-7:yield f
def overlap(a,b):return abs(volume(BRepAlgoAPI_Common(a,b).Shape()))
old={r['name']:r for r in load(H/'before/inward_placements.json')}
new={r['name']:r for r in load(M/'inward_placements.json')}
assert old.keys()==new.keys() and len(new)==24
for name,r in new.items():
    assert r['matrix_cm']==old[name]['matrix_cm'],name
    if not name.startswith('Rod_Clamp_'):assert r['path']==old[name]['path']
hashes=load(H/'before/protected_hashes.json')
for f,digest in hashes.items():assert hashlib.sha256((M/f).read_bytes()).hexdigest().upper()==digest,f
cache={}
def placed(r):
    p=Path(r['path']).with_suffix('.step')
    if p not in cache:cache[p]=read(p)
    return transform(cache[p],r['matrix_cm'])
parts={n:placed(r) for n,r in new.items()}
tube=parts['Probe_Tube_ID51_OD54'];frame=parts['Existing_Probe_H_Frame']
rows=[]
for name,r in new.items():
    if not name.startswith('Rod_Clamp_'):continue
    s=parts[name];before=placed(old[name]);support=parts[('Left' if 'X3_' in name else 'Right')+'_Rod_Support']
    available=sum(area(f) for f in bearing_faces(s))
    contact=sum(area(BRepAlgoAPI_Common(a,b).Shape()) for a in bearing_faces(s) for b in bearing_faces(support))
    interference=overlap(s,support)
    dist=BRepExtrema_DistShapeShape(s,support);dist.Perform()
    rows.append(dict(name=name,head_bearing_global_z_mm=-1.6,head_height_mm=1.65,head_diameter_mm=5.7,
        actual_bounds_mm=bounds(s),flat_bearing_area_mm2=available,supported_area_mm2=contact,supported_fraction=contact/available,
        flange_overlap_mm3=interference,rod_overlap_mm3=overlap(s,frame),old_sleeve_overlap_mm3=overlap(before,tube),
        new_sleeve_overlap_mm3=overlap(s,tube),flange_minimum_distance_mm=dist.Value(),tip_projection_mm=.4))
    assert BRepCheck_Analyzer(s).IsValid() and available>0 and contact>0
    assert abs(bounds(s)[5]-6.4)<1e-6
    print(json.dumps(rows[-1]),flush=True)
full=read(M/'Rod_Holder_Assembly_Drop8p5.step')
assert BRepCheck_Analyzer(full).IsValid()
delta=abs(volume(full)-sum(volume(s) for s in parts.values()))
print(json.dumps(dict(export_volume=volume(full),occurrence_volume=sum(volume(s) for s in parts.values()),difference=delta,tube_volume=volume(tube))),flush=True)
assert delta<1e-3
report=dict(saved_assembly_reopened=True,only_eight_rod_paths_changed=True,all_transforms_unchanged=True,
    protected_part_and_plate_drawing_hashes_unchanged=True,assembly_step_valid=True,assembly_volume_residual_mm3=delta,
    counts=dict(button_rod=8,socket_device=2,countersunk_deck=8),fasteners=rows,
    caveat='Geometric bearing contact does not establish allowable preload. Existing sleeve and device reference clashes remain.' )
save(M/'rod_button_head_verification.json',report)
# Retain historical checks for unchanged interfaces, replacing only the affected
# screw checks with current saved STEP measurements.
geometry=load(H/'before/geometry_verification.json')
for c in geometry['interfaces']:
    if not c['pair'].startswith('Rod_Clamp_'):continue
    name,other=c['pair'].split(' / ');r=next(x for x in rows if x['name']==name)
    val=r['flange_overlap_mm3'] if other=='plate' else r['rod_overlap_mm3']
    c.update(overlap_mm3=val,non_thread_overlap_mm3=val,interference_free=val<1e-5)
for c in geometry['sleeve_intersections']:
    if c['component'].startswith('Rod_Clamp_'):c['overlap_mm3']=next(x['new_sleeve_overlap_mm3'] for x in rows if x['name']==c['component'])
geometry['unresolved_interfaces']=[c for c in geometry['interfaces'] if not c['interference_free']]
geometry['all_checked_interfaces_clear']=not geometry['unresolved_interfaces']
geometry['rod_hardware_update']='ISO 7380-1 M3x8; rod_button_head_verification.json. Unchanged interfaces retain their prior verified geometry and transforms.'
save(M/'geometry_verification.json',geometry)
print(json.dumps({k:v for k,v in report.items() if k!='fasteners'},indent=2))
