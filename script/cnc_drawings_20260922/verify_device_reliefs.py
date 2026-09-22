"""Independently verify the STEP reliefs, retained interfaces and machining envelope."""
from pathlib import Path
import json, sys, math, hashlib
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.gp import gp_Pnt
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
MODEL=ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
sys.path.insert(0,str(ROOT/'script/mechanical_assembly_20260921'))
from inspect_geometry import read, inspect, volume
measurement=json.loads((HERE/'tmp/device_lip_measurement.json').read_text())
contact=measurement['deck_contact_faces'][0]['bounds']
thickness=contact[3]-contact[0];width=thickness+.3
new=read(MODEL/'Centre_Plate.step');old=read(HERE/'tmp/before_device_relief/Centre_Plate.step')
info=inspect(new);assert info['valid']
ex=TopExp_Explorer(new,TopAbs_SOLID);count=0
while ex.More(): count+=1;ex.Next()
assert count==1
expected=2*(width*72-(4-math.pi)*.5**2)*.5
before_hardware=read(HERE/'tmp/before_standard_hardware/Centre_Plate.step')
# The later Content Center correction enlarges eight countersinks from 6.2 to
# 6.6 mm. Check groove removal separately, then verify the additional change.
removed=volume(old)-volume(before_hardware)
assert abs(removed-expected)<1e-5
def countersink_excess(radius):
    return math.pi/3*(radius**3-1.7**3)-math.pi*1.7**2*(radius-1.7)
countersink_delta=8*(countersink_excess(3.3)-countersink_excess(3.1))
assert abs(volume(before_hardware)-volume(new)-countersink_delta)<1e-5
ranges=[[19.933375831081217-width,19.933375831081217],
        [33.433375831081217,33.433375831081217+width]]
floors=[p for p in info['planes'] if abs(p['normal'][2])>.99 and abs(p['point'][2]-3.5)<1e-7]
assert len(floors)==2
for p,span in zip(sorted(floors,key=lambda p:p['bounds'][0]),ranges):
    expected_bounds=[span[0],4,3.5,span[1],76,3.5]
    assert max(abs(a-b) for a,b in zip(p['bounds'],expected_bounds))<1e-7
    assert abs(p['area']-(width*72-(4-math.pi)*.5**2))<1e-6
corners=[c for c in info['cylinders'] if abs(c['radius']-.5)<1e-7 and abs(c['axis'][2])>.99]
assert len(corners)==8
old_holes=[c for c in inspect(old)['cylinders'] if abs(c['axis'][0])>.99]
new_holes=[c for c in info['cylinders'] if abs(c['axis'][0])>.99]
assert len(old_holes)==len(new_holes)==10
for a,b in zip(old_holes,new_holes):
    assert max(abs(x-y) for x,y in zip(a['bounds'],b['bounds']))<1e-7
    assert abs(a['radius']-b['radius'])<1e-7
boss_box=BRepPrimAPI_MakeBox(gp_Pnt(19.933375831081217,4,4),13.5,72,6).Shape()
assert abs(volume(BRepAlgoAPI_Common(new,boss_box).Shape())-volume(BRepAlgoAPI_Common(old,boss_box).Shape()))<1e-6
preserved=json.loads((MODEL/'source_preservation.json').read_text(encoding='utf-8-sig'))
for r in preserved:
    assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest().upper()==r['before_sha256']
result=dict(lip_thickness_mm=thickness,groove_width_mm=width,groove_allowance_mm=.3,
            groove_depth_mm=.5,groove_length_mm=72,corner_radius_mm=.5,
            groove_x_ranges_mm=ranges,groove_y_range_mm=[4,76],groove_z_range_mm=[3.5,4],
            removed_volume_mm3=removed,expected_removed_volume_mm3=expected,thread_count=10,
            single_solid=True,source_device_unchanged=True,boss_and_thread_locations_unchanged=True,
            countersink_diameter_mm=6.6,countersink_correction_removed_mm3=countersink_delta)
(MODEL/'device_relief_grooves.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
