"""Plot a dimensioned CAD section using measured geometry, not estimated pixels.

The selected target is 0.300 mm from the pocket floor toward the cavity opening.
Annotations are English; all geometry and reported dimensions are millimetres.
"""
from pathlib import Path
import json, math, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch
import matplotlib.patheffects as effects
from OCP.gp import gp_Trsf,gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepAdaptor import BRepAdaptor_Surface,BRepAdaptor_Curve
from OCP.BRepTools import BRepTools,BRepTools_WireExplorer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_WIRE,TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Line

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'script'/'mechanical_assembly_20260921'))
from inspect_geometry import read,inspect,faces,bounds
MECH=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'
OUT=MECH/'Rod_Holder_Adapter'
fit=json.loads((MECH/'assembly_validation.json').read_text())
data=json.loads((OUT/'pocket_measurement_transforms.json').read_text(encoding='utf-8-sig'))
placements=json.loads((OUT/'inward_placements.json').read_text(encoding='utf-8-sig'))

def matrix(value):
    m=np.array(value,dtype=float);m[:3,3]*=10
    return m

def point(m,p):return (m@np.array([*p,1.0]))[:3]
def transform(shape,m):
    t=gp_Trsf();t.SetValues(*m[:3,:].ravel().tolist())
    return BRepBuilderAPI_Transform(shape,t,True).Shape()

carrier_m=matrix(data['carrier_matrix_cm'])
pcb_m=carrier_m@matrix(data['pcb_matrix_cm'])@matrix(data['board_matrix_cm'])
tube_m=matrix(data['tube_matrix_cm'])
cavity=next(i for i in fit['pcb_items'] if i['name']=='PCB_board')['details']['cavity']
x0,y0,x1,y1=cavity['envelope_mm'];depth=cavity['depth_mm']
local_floor=np.array([(x0+x1)/2,(y0+y1)/2,depth])
local_target=local_floor+np.array([0,0,-0.300])
floor=point(pcb_m,local_floor);target=point(pcb_m,local_target)
axis_origin=point(tube_m,[0,0,0]);axis=tube_m[:3,2];axis/=np.linalg.norm(axis)
centre=axis_origin+axis*np.dot(target-axis_origin,axis)
delta=target-centre;distance=float(np.linalg.norm(delta))
assert abs(np.linalg.norm(target-floor)-0.300)<1e-9
assert abs(delta[1])<1e-8
substrate_local=read(Path(data['board_path']).with_suffix('.step'))
floor_faces=[p for p in inspect(substrate_local)['planes'] if abs(p['normal'][2])>.99 and abs(p['point'][2]-depth)<1e-7]
assert any(p['bounds'][0]<=local_floor[0]<=p['bounds'][3] and p['bounds'][1]<=local_floor[1]<=p['bounds'][4] for p in floor_faces),'Pocket floor not found in STEP.'

part_map={r['name']:r for r in placements}
def placed(name):
    r=part_map[name]
    return transform(read(Path(r['path']).with_suffix('.step')),matrix(r['matrix_cm']))
top_local=np.eye(4);top_local[:3,3]=fit['top_transform']['translation_mm']
solids={
    'Tube':placed('Probe_Tube_ID51_OD54'),
    'Rods':placed('Existing_Probe_H_Frame'),
    'Plate / boss':placed('Solid_Plate_With_Integral_Mounting_Boss'),
    'Holder':transform(read(MECH/'Top_ForFridge_reference.step'),carrier_m@top_local),
    'PCB':transform(substrate_local,pcb_m),
}
colors={'Tube':'#858d9c','Rods':'#96502c','Plate / boss':'#25718e','Holder':'#bd7627','PCB':'#3c845c'}
section_y=float(target[1]);cut=BRepPrimAPI_MakeBox(gp_Pnt(-8,section_y,-31),67,.03,68).Shape()

def ring_points(wire,face):
    result=[];walker=BRepTools_WireExplorer(wire,face)
    while walker.More():
        edge=walker.Current();curve=BRepAdaptor_Curve(edge)
        count=2 if curve.GetType()==GeomAbs_Line else 257
        us=np.linspace(curve.FirstParameter(),curve.LastParameter(),count)
        if edge.Orientation()==TopAbs_REVERSED:us=us[::-1]
        segment=[]
        for u in us:
            p=curve.Value(float(u));segment.append([p.X(),p.Z()])
        result.extend(segment[:-1]);walker.Next()
    return np.array(result)

paths={}
for name,shape in solids.items():
    section=BRepAlgoAPI_Common(shape,cut).Shape();paths[name]=[]
    for face in faces(section):
        surface=BRepAdaptor_Surface(face)
        if surface.GetType()!=GeomAbs_Plane:continue
        plane=surface.Plane()
        if abs(plane.Axis().Direction().Y())<.99 or abs(plane.Location().Y()-section_y)>1e-6:continue
        outer=BRepTools.OuterWire_s(face)
        verts=[];codes=[];ex=TopExp_Explorer(face,TopAbs_WIRE)
        while ex.More():
            wire=TopoDS.Wire(ex.Current());xy=ring_points(wire,face)
            signed=np.sum(xy[:,0]*np.roll(xy[:,1],-1)-np.roll(xy[:,0],-1)*xy[:,1])
            is_outer=wire.IsSame(outer)
            if (signed>0)!=is_outer:xy=xy[::-1]
            verts.extend(xy.tolist()+[xy[0].tolist()]);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(xy)-1)+[PlotPath.CLOSEPOLY])
            ex.Next()
        paths[name].append(PlotPath(verts,codes))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
fig=plt.figure(figsize=(14,9),facecolor='#f6f8fb')
main=fig.add_axes([.025,.13,.62,.80]);inset=fig.add_axes([.68,.40,.295,.31])
def draw_geometry(ax):
    ax.set_facecolor('#f6f8fb')
    for name,parts in paths.items():
        for path in parts:ax.add_patch(PathPatch(path,facecolor=colors[name],edgecolor='none'))
    ax.set_aspect('equal')
draw_geometry(main);draw_geometry(inset)
main.set_xlim(-8,59);main.set_ylim(-30.5,36.5);main.axis('off')
red='#bf2354';cyan='#007f99';dark='#233348'
ox,oz=centre[0],centre[2];px,pz=target[0],target[2];fx,fz=floor[0],floor[2]
main.axvline(ox,color=red,ls=(0,(4,5)),lw=.8,alpha=.4)
main.plot(ox,oz,'o',color=red,ms=7,mec='white',mew=1.2,zorder=10)
main.plot(px,pz,'o',color=cyan,ms=7,mec='white',mew=1.2,zorder=10)
main.annotate('',xy=(px,pz),xytext=(ox,oz),arrowprops=dict(arrowstyle='<->',color=red,lw=1.8,shrinkA=6,shrinkB=6))
main.annotate('O  Tube centre',xy=(ox,oz),xytext=(4,oz-6),color=red,weight='bold',arrowprops=dict(arrowstyle='-',color=red,lw=1.2))
main.annotate('P  300 µm from pocket floor',xy=(px,pz),xytext=(8,21),color=cyan,weight='bold',arrowprops=dict(arrowstyle='-',color=cyan,lw=1.2,connectionstyle='angle,angleA=0,angleB=90,rad=5'))
main.text(36,17.3,f'OP = {distance:.3f} mm',fontsize=13,weight='bold',color=red,ha='center',bbox=dict(boxstyle='round,pad=.45',fc='white',ec=red,lw=1))
main.annotate('',xy=(px,pz),xytext=(36,15.5),arrowprops=dict(arrowstyle='-',color=red,lw=.9))

inset.set_xlim(px-3.5,px+3.5);inset.set_ylim(10.2,12.8)
inset.set_title('Pocket detail',loc='left',fontweight='bold',pad=12,color=dark)
inset.axvline(ox,color=red,ls=(0,(4,4)),lw=.9,alpha=.7)
inset.plot([fx],[fz],'s',ms=5,color=dark,zorder=10)
inset.plot([px],[pz],'o',ms=7,color=cyan,mec='white',mew=1,zorder=11)
inset.plot([fx-1.4,fx],[fz,fz],color=dark,lw=.9)
inset.plot([px-1.4,px],[pz,pz],color=cyan,lw=.9)
inset.annotate('',xy=(px-1.1,fz),xytext=(px-1.1,pz),arrowprops=dict(arrowstyle='<->',lw=1.2,color=dark,shrinkA=0,shrinkB=0))
inset.text(px-1.35,(fz+pz)/2,'0.300 mm',ha='right',va='center',fontsize=10,color=dark)
inset.annotate('Pocket floor',xy=(fx,fz),xytext=(px+.65,12.45),fontsize=10,color=dark,arrowprops=dict(arrowstyle='-',lw=.9,color=dark))
inset.text(px+.25,pz-.13,'P',weight='bold',color=cyan)
inset.text(px,10.35,'Cavity opening / QD side',ha='center',fontsize=10,color=dark)
inset.set_xticks([]);inset.set_yticks([])
for spine in inset.spines.values():spine.set_color('#c9d1dc')

fig.text(.69,.88,'CENTRE DISTANCE',fontsize=11,weight='bold',color=dark)
fig.text(.69,.817,f'{distance:.3f} mm',fontsize=30,weight='bold',color=red)
fig.text(.69,.765,f'ΔX = {delta[0]:+.3f} mm    ΔZ = {delta[2]:+.3f} mm',fontsize=11,color=dark)
fig.text(.69,.315,'Target definition',fontsize=12,weight='bold',color=dark)
fig.text(.69,.263,'Pocket-floor centre, offset 0.300 mm\ntoward the cavity opening (−Z here).',fontsize=11,linespacing=1.6,color=dark)
fig.text(.69,.19,f'O: X={ox:.3f}, Z={oz:.3f} mm\nP: X={px:.3f}, Z={pz:.3f} mm',fontsize=11,linespacing=1.7,color=dark)
fig.text(.045,.957,'Tube centre to the pocket reference point',fontsize=19,weight='bold',color=dark)
fig.text(.045,.035,'Actual CAD section through pocket centre • Distance is radial to the tube axis • Dimensions in mm',fontsize=10,color='#516174')
for i,(name,color) in enumerate(colors.items()):
    fig.text(.045+i*.123,.082,'■',fontsize=13,color=color)
    fig.text(.061+i*.123,.083,name,fontsize=10,color=dark)
png=OUT/'Pocket_centre_distance.png';svg=OUT/'Pocket_centre_distance.svg'
fig.savefig(png,dpi=160,facecolor=fig.get_facecolor());fig.savefig(svg,facecolor=fig.get_facecolor());plt.close(fig)
result=dict(reference='Pocket floor centre + 0.300 mm toward cavity opening',offset_mm=.3,local_floor_mm=local_floor.tolist(),local_target_mm=local_target.tolist(),floor_global_mm=floor.tolist(),target_global_mm=target.tolist(),tube_axis_at_target_y_mm=centre.tolist(),delta_xz_mm=[float(delta[0]),float(delta[2])],radial_distance_mm=distance,section_y_mm=section_y,pcb_to_assembly_matrix_mm=pcb_m.tolist(),native_floor_verified=True,output_png=str(png),output_svg=str(svg))
(OUT/'pocket_centre_distance.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
