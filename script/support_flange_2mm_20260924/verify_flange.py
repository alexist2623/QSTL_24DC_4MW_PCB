"""Independent STEP cut geometry, bevel and screw-bearing verification."""
from pathlib import Path
import sys,json,hashlib,math,random
from OCP.gp import gp_Pnt,gp_Vec,gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace,BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism,BRepPrimAPI_MakeBox
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
H=Path(__file__).resolve().parent;R=H.parents[1];M=R/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
sys.path.insert(0,str(H.parent/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,bounds,volume,faces
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def area(shape):
    p=GProp_GProps();BRepGProp.SurfaceProperties_s(shape,p);return p.Mass()
def cut(a,b):
    op=BRepAlgoAPI_Cut(a,b);op.SetFuzzyValue(1e-5);op.Build()
    assert op.IsDone()
    return op.Shape()
def solid(shape):
    it=TopExp_Explorer(shape,TopAbs_SOLID);assert it.More()
    out=it.Current();it.Next();assert not it.More()
    return out
def plane_faces(shape,z):
    for f in faces(shape):
        a=BRepAdaptor_Surface(f)
        if a.GetType()==GeomAbs_Plane and abs(abs(a.Plane().Axis().Direction().Z())-1)<1e-7 and abs(a.Plane().Location().Z()-z)<1e-7:yield f
reports=[]
for side in ('Left','Right'):
    old=solid(read(H/'before'/(side+'_Rod_Support.step')));new=solid(read(M/(side+'_Rod_Support.step')))
    assert inspect(new)['valid']
    thin=BRepPrimAPI_MakeBox(gp_Pnt(0 if side=='Left' else 45,0,8.5),6,80,2).Shape()
    xx=(0,2,0) if side=='Left' else (51,49,51)
    poly=BRepBuilderAPI_MakePolygon()
    for x,z in zip(xx,(10.5,10.5,12.5)):poly.Add(gp_Pnt(x,0,z))
    poly.Close();wedge=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(poly.Wire()).Face(),gp_Vec(0,80,0)).Shape()
    expected=cut(cut(old,thin),wedge)
    assert inspect(expected)['valid']
    delta=abs(volume(new)-volume(expected));assert delta<1e-5,delta
    assert max(abs(a-b) for a,b in zip(bounds(new),bounds(expected)))<1e-6
    # Boolean subtraction of the coincident exported cylindrical faces produces
    # invalid kernel results. Compare valid cut solids by volume and independently
    # classified deterministic samples instead; do not accept that invalid result.
    rng=random.Random(20260924);a=BRepClass3d_SolidClassifier(new);b=BRepClass3d_SolidClassifier(expected)
    bbox=bounds(new);count=20000
    for _ in range(count):
        p=gp_Pnt(*(rng.uniform(bbox[i]-.1,bbox[i+3]+.1) for i in range(3)))
        a.Perform(p,1e-7);b.Perform(p,1e-7);assert a.State()==b.State(),(p.X(),p.Y(),p.Z())
    oldarea=sum(area(f) for f in plane_faces(old,12.5));newarea=sum(area(f) for f in plane_faces(new,12.5));assert abs(newarea-oldarea)<1e-6
    bevels=[p for p in inspect(new)['planes'] if abs(abs(p['normal'][0])-math.sqrt(.5))<1e-7 and abs(abs(p['normal'][2])-math.sqrt(.5))<1e-7]
    assert len(bevels)==1 and abs(bevels[0]['bounds'][5]-bevels[0]['bounds'][2]-2)<1e-6
    reports.append(dict(part=side,flange_thickness_mm=2,chamfer_leg_mm=2,chamfer_angle_deg=45,volume_difference_from_requested_cut_mm3=delta,matching_point_classifications=count,rod_side_face_area_before_mm2=oldarea,rod_side_face_area_after_mm2=newarea,removed_volume_mm3=volume(old)-volume(new),bevel_bounds_mm=bevels[0]['bounds']))
def transform(s,rows):
    rows=[list(r) for r in rows]
    for r in rows[:3]:r[3]*=10
    t=gp_Trsf();t.SetValues(*[v for r in rows[:3] for v in r]);return BRepBuilderAPI_Transform(s,t,True).Shape()
placements=load(M/'inward_placements.json');bearings=[]
for r in placements:
    if not r['name'].startswith('Rod_Clamp_M3_'):continue
    screw=transform(read(Path(r['path']).with_suffix('.step')),r['matrix_cm']);left='X3_' in r['name'];support=next(p for p in placements if p['name']==('Left' if left else 'Right')+'_Rod_Support');solid=transform(read(Path(support['path']).with_suffix('.step')),support['matrix_cm'])
    sf=list(plane_faces(screw,-2));pf=list(plane_faces(solid,-2));available=sum(area(f) for f in sf);contact=sum(area(BRepAlgoAPI_Common(a,b).Shape()) for a in sf for b in pf)
    assert available>1 and contact>0
    bearings.append(dict(screw=r['name'],underhead_plane_z_mm=-2,bearing_face_area_mm2=available,support_contact_area_mm2=contact,contact_fraction=contact/available))
base=load(H/'before/baseline_hashes.json')
assert all(hashlib.sha256((M/f).read_bytes()).hexdigest().upper()==base[f] for f in ['Centre_Plate.ipt','Centre_Plate.step','Standard_Fasteners/ISO_4762_M3x8.ipt'.replace('/',chr(92)),'Standard_Fasteners/DIN_7991_M3x10.ipt'.replace('/',chr(92))])
report=dict(passed=True,parts=reports,central_plate_and_standard_hardware_unchanged=True,rod_screw_bearing=bearings,comment='C2 bevel preserves the full rod contact plane but removes part of each rod-screw head bearing footprint. This report describes geometry, not preload or structural qualification.')
(H/'flange_validation.json').write_text(json.dumps(report,indent=2));(M/'support_flange_2mm_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
