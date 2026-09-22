"""Build simplified mechanical solids from the current saved PCB and validate fit.

PCB coordinates: XY as in Altium, Bottom/QD at Z=0, Top/SMP at Z=thickness.
The assembly applies a proper 180-degree Y rotation, never a reflection.
"""
from pathlib import Path
import json, math, statistics
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax1, gp_Dir
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Compound
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.BRepCheck import BRepCheck_Analyzer
from inspect_geometry import read, bounds, volume, inspect

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
PARTS=OUT/'PCB_parts'
PARTS.mkdir(exist_ok=True)
DATA=json.loads((HERE/'pcb_geometry.json').read_text())
SOLIDS=json.loads((HERE/'solid_geometry.json').read_text())
BOARD=DATA['board'][0]
mm=lambda value:float(value.removesuffix('mil'))*.0254
thickness=sum(mm(BOARD[f'V9_STACK_LAYER{i}_'+('COPTHICK' if i%2 else 'DIELHEIGHT')]) for i in range(3,14))
width,height=mm(BOARD['VX1']),mm(BOARD['VY2'])
assert abs(width-19.5)<1e-5 and abs(height-67.9)<1e-5
assert DATA['pcb_sha256']=='84feed018fbaf5cbfa3203201c8771711b00ffec18aa0aadaf20fdeadb99ca63'

def transformed(shape,rot_y=0,rot_z=0,move=(0,0,0)):
    for direction,angle in ((gp_Dir(0,1,0),rot_y),(gp_Dir(0,0,1),rot_z)):
        if angle:
            t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),direction),math.radians(angle))
            shape=BRepBuilderAPI_Transform(shape,t,True).Shape()
    t=gp_Trsf();t.SetTranslation(gp_Vec(*move))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

def box(x,y,z,dx,dy,dz):return BRepPrimAPI_MakeBox(gp_Pnt(x,y,z),dx,dy,dz).Shape()
def cylinder(x,y,z,r,h):return transformed(BRepPrimAPI_MakeCylinder(r,h).Shape(),move=(x,y,z))
def cut(a,b):return BRepAlgoAPI_Cut(a,b).Shape()
def fuse(a,b):return BRepAlgoAPI_Fuse(a,b).Shape()
def compound(shapes):
    builder=BRep_Builder();result=TopoDS_Compound();builder.MakeCompound(result)
    for shape in shapes:builder.Add(result,shape)
    return result
def export(shape,path):
    assert BRepCheck_Analyzer(shape).IsValid(),str(path)
    writer=STEPControl_Writer();writer.Transfer(shape,STEPControl_AsIs)
    assert int(writer.Write(str(path)))==1

# Retain every component drill and mechanical hole; omit tiny electrical vias.
substrate=box(0,0,0,width,height,thickness)
drills=[]
for pad in DATA['pads']:
    x,y,*_=pad['coords_mm'];diameter=pad['coords_mm'][8]
    if diameter>0:
        drills.append(dict(x=x,y=y,diameter=diameter,component=pad['component']))
        substrate=cut(substrate,cylinder(x,y,-.1,diameter/2,thickness+.2))

# The mechanical pocket is explicitly documented but not a through-board cutout.
cavity=json.loads((HERE.parent/'lower_rc_70pct_20260921'/'plan.json').read_text())['cavity']
x0,y0,x1,y1=cavity['envelope_mm'];r=cavity['corner_radius_mm'];depth=cavity['depth_mm']
pocket=fuse(box(x0+r,y0,-.01,x1-x0-2*r,y1-y0,depth+.01),box(x0,y0+r,-.01,x1-x0,y1-y0-2*r,depth+.01))
for x in (x0+r,x1-r):
    for y in (y0+r,y1-r):pocket=fuse(pocket,cylinder(x,y,-.01,r,depth+.01))
substrate=cut(substrate,pocket)
items=[];shapes={}

def add(name,shape,color,kind,details=None):
    path=PARTS/(name+'.step');export(shape,path);shapes[name]=shape
    items.append(dict(name=name,path=str(path.relative_to(OUT)),color=color,kind=kind,bounds_mm=bounds(shape),volume_mm3=volume(shape),details=details or {}))

add('PCB_board',substrate,[42,105,69],'board',dict(outline_mm=[width,height],thickness_mm=thickness,drill_count=len(drills),cavity=cavity|{'geometry':None}))
for body in DATA['bodies']:
    name=body['component'];p=body['props']
    x,y=mm(p['MODEL.2D.X']),mm(p['MODEL.2D.Y'])
    angle=float(p['MODEL.3D.ROTZ'])
    if name.startswith(('R','C')):
        model=next(m for m in DATA['models'] if m['ID']==p['MODELID'])
        b=SOLIDS[Path(model['extracted_file']).name]['bounds']
        # Rounded manufacturer details are replaced by exact size/height envelopes.
        h=b[5]-max(0,b[2]);sx,sy=b[3]-b[0],b[4]-b[1]
        shape=transformed(box(-sx/2,-sy/2,-h,sx,sy,h),rot_z=angle,move=(x,y,0))
        add(name,shape,[50,53,56] if name.startswith('R') else [180,124,68],'passive',dict(size_mm=[sx,sy,h],side='Bottom/QD',centre_xy_mm=[x,y],rotation_deg=angle))
    elif name.startswith('SMP'):
        # Preserve the source connector's envelope, bore, five pin positions and tip depth.
        base=thickness+mm(p['MODEL.3D.DZ'])
        barrel=cut(cylinder(x,y,base,2.75,4.8),cylinder(x,y,base+2.01,1.83,2.80))
        pieces=[barrel]
        for pad in DATA['pads']:
            if pad['component']==name:
                px,py=pad['coords_mm'][:2]
                pieces.append(cylinder(px,py,base-3.81,.3,3.81))
                if pad['number']!='1':pieces.append(cylinder(px,py,thickness,.55,.4))
        add(name,compound(pieces),[190,192,195],'connector',dict(outer_diameter_mm=5.5,height_above_top_mm=5.4,pin_tip_below_top_mm=3.21,side='Top/SMP'))
    elif name=='J1':
        # Source Rx=90 degrees: local Z maps to -Y and local Y maps to Z.
        b=SOLIDS['model_10.step']['bounds'];dz=mm(p['MODEL.3D.DZ'])
        shape=box(x+b[0],y-b[5],thickness+dz+b[1],b[3]-b[0],b[5]-b[2],b[4]-b[1])
        add(name,shape,[220,217,200],'connector',dict(size_mm=[b[3]-b[0],b[5]-b[2],b[4]-b[1]],side='Top/SMP',simplification='conservative closed-actuator outer envelope'))

# Preserve a thin, separately selectable visual wire-bond pad field.
qd=[]
for pad in DATA['pads']:
    if pad['component']=='Q1':
        x,y,sx,sy=pad['coords_mm'][:4]
        qd.append(transformed(box(-sx/2,-sy/2,-.005,sx,sy,.005),rot_z=pad['rotation'],move=(x,y,0)))
add('QD_bond_pads',compound(qd),[207,170,51],'visual',dict(visual_thickness_mm=.005,excluded_from_mechanical_interference=True))

# Recover X/Y registration from independent mounting/SMP hole centre patterns.
mounts=[p for p in DATA['pads'] if p['component'] is None and p['coords_mm'][8]>0]
bcyl=SOLIDS['Bottom_reference.step']['cylinders']
bottom_smp=[c for c in bcyl if abs(c['radius']-2.85)<1e-6]
dx=statistics.mean(c['point'][0] for c in bottom_smp)-width/2
smp_pads=[p for p in DATA['pads'] if (p['component'] or '').startswith('SMP') and p['number']=='1']
dy=statistics.mean(c['point'][1] for c in bottom_smp)-statistics.mean(p['coords_mm'][1] for p in smp_pads)
# Bottom's PCB seating pads are at Z=2; Top_ForFridge seats at native Z=-4.6.
seat_z=2.0;pcb_transform=dict(rot_y_deg=180,translation_mm=[dx+width,dy,seat_z+thickness])
top_transform=dict(rot_y_deg=0,translation_mm=[0,0,seat_z+thickness+4.6])
placed={n:transformed(s,rot_y=180,move=pcb_transform['translation_mm']) for n,s in shapes.items()}
mechanical={'Bottom':read(OUT/'Bottom_reference.step'),'Top_ForFridge':transformed(read(OUT/'Top_ForFridge_reference.step'),move=top_transform['translation_mm'])}
alignment=[]
for p in smp_pads:
    x,y=p['coords_mm'][:2];point=[dx+width-x,dy+y]
    error=min(math.dist(point,c['point'][:2]) for c in bottom_smp)
    alignment.append(dict(feature=p['component'],error_mm=error))
for p in mounts:
    x,y=p['coords_mm'][:2];point=[dx+width-x,dy+y]
    candidates=[c for c in bcyl if abs(c['radius']-(.8 if p['coords_mm'][8]<3 else 1.7))<1e-5]
    alignment.append(dict(feature='mount_'+str([x,y]),error_mm=min(math.dist(point,c['point'][:2]) for c in candidates)))
assert max(a['error_mm'] for a in alignment)<1e-4

checks=[]
for side,mech in mechanical.items():
    for name,shape in placed.items():
        if name=='QD_bond_pads':continue
        common=BRepAlgoAPI_Common(mech,shape).Shape();overlap=abs(volume(common))
        dist=BRepExtrema_DistShapeShape(mech,shape);dist.Perform()
        result=dict(mechanical=side,component=name,overlap_mm3=overlap,minimum_distance_mm=dist.Value())
        if overlap>1e-6:
            result['overlap_bounds_mm']=bounds(common)
            export(common,OUT/f'Interference_{side}_{name}.step')
        checks.append(result)
common=BRepAlgoAPI_Common(mechanical['Bottom'],mechanical['Top_ForFridge']).Shape()
checks.append(dict(mechanical='Top_ForFridge',component='Bottom',overlap_mm3=abs(volume(common))))
all_pcb=compound(shapes.values());export(all_pcb,OUT/'PCB_simplified.step')
export(compound([*mechanical.values(),*placed.values()]),OUT/'Carrier_with_PCB_geometry.step')
report=dict(source_pcb_sha256=DATA['pcb_sha256'],top_source='Top_ForFridge.SLDPRT',pcb_thickness_mm=thickness,pcb_items=items,pcb_transform=pcb_transform,top_transform=top_transform,registration=alignment,interference_checks=checks,interferences=[c for c in checks if c['overlap_mm3']>1e-5],assumptions=['Bottom PCB seat at native Z=2 mm','Top_ForFridge PCB seat at native Z=-4.6 mm','Component envelopes preserve source model nominal size and height; solder fillets and manufacturing tolerance are not added','Copper tracks, masks and tiny vias omitted; 24 QD pads are visual only','SMP overlaps are accepted by the user for this assembly pass and have not been corrected'])
(OUT/'assembly_validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(thickness_mm=thickness,components=len(items),alignment_max_mm=max(a['error_mm'] for a in alignment),pcb_transform=pcb_transform,top_transform=top_transform,interferences=report['interferences']),indent=2))
