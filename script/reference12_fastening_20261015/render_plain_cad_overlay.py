"""Render the supplied copper mesh with exact SMP STEP models in the latest XY plan."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import vtk
from PIL import Image, ImageDraw, ImageFont
import build_fastening_review as cad
from OCP.gp import gp_Trsf, gp_Ax1, gp_Dir, gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016'
REF=ROOT/'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015'
PLAN=ROOT/'QSTL_QD4_2SET_38PAD/Four_End_SMP_Side_Entry_20261015/side_entry_audit.json'
SMP=ROOT/'QSTL_QD4_2SET_38PAD/SMP-FS-SBPCT.stp'


def poly_actor(points,color,opacity=1,outline=False,width=2):
    pts=vtk.vtkPoints()
    for p in points:pts.InsertNextPoint(*p)
    cells=vtk.vtkCellArray()
    cells.InsertNextCell(len(points)+(1 if outline else 0))
    for i in range(len(points)):cells.InsertCellPoint(i)
    if outline:cells.InsertCellPoint(0)
    mesh=vtk.vtkPolyData();mesh.SetPoints(pts)
    if outline:mesh.SetLines(cells)
    else:mesh.SetPolys(cells)
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputData(mesh)
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color);actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().SetLineWidth(width);actor.GetProperty().LightingOff()
    return actor


def main():
    data=json.loads(PLAN.read_text());cx,cy=data['qd_centre_mm']
    sources=[PLAN,SMP,REF/'SMP_Side_Shell.vtp',REF/'Component_Side_Shell.vtp',
             ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    actors=[]
    for name,opacity in [('SMP_Side_Shell',1.),('Component_Side_Shell',.12)]:
        r=vtk.vtkXMLPolyDataReader();r.SetFileName(str(REF/(name+'.vtp')));r.Update()
        actor=cad.mesh_actor(r.GetOutput(),(.77,.45,.24));actor.SetPosition(cx,cy,0)
        actor.GetProperty().SetOpacity(opacity);actors.append(actor)
    board=[(-6.55,0,.03),(26.05,0,.03),(26.05,77.5,.03),(-6.55,77.5,.03)]
    actors.append(poly_actor(board,(.08,.58,.35),.18))
    actors.append(poly_actor(board,(.02,.50,.30),1.,True,3))
    raw=cad.read_parts(SMP,'SMP')
    rot=gp_Trsf();rot.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.pi/2)
    prototypes=[]
    for p in raw:
        shape=BRepBuilderAPI_Transform(p['shape'],rot,True).Shape()
        prototypes.append(dict(p,shape=shape,category='component'))
    for row in data['rows']:
        for p in prototypes:
            actor=cad.actor_from_part(p)
            actor.SetPosition(row['start'][0],row['start'][1],.6)
            actor.GetProperty().SetSpecular(.25);actor.GetProperty().SetSpecularPower(25)
            actors.append(actor)
    for row in data['pads']:
        p=row['after'];a=np.deg2rad(p['rotation']);c=np.cos(a);s=np.sin(a)
        xy=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],float)*[p['size_x']/2,p['size_y']/2]
        xy=xy@np.array([[c,s],[-s,c]])+[p['x'],p['y']]
        actors.append(poly_actor([(x,y,.08) for x,y in xy],(.86,.69,.25)))
    actors.append(poly_actor([(cx-2.15,cy-2.65,.08),(cx+2.15,cy-2.65,.08),
                             (cx+2.15,cy+2.65,.08),(cx-2.15,cy+2.65,.08)],(.10,.21,.24)))
    # These are co-projected parts, not an asserted solid mating arrangement.
    path=OUT/'Copper_CAD_Current_PCB_SMP_Overlay.png'
    cad.render(path,actors,(cx,40.8,220),(cx,40.8,0),48.0,size=(1200,1900))
    im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    d.text((35,24),'Copper CAD + current PCB / 16 SMPs',font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',26),fill='#29464a')
    d.text((35,1860),'Original CAD orientation | XY overlay only; native files unchanged',font=font,fill='#536c70')
    im.save(path)
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    (OUT/'plain_3d_overlay.json').write_text(json.dumps(dict(source_hashes=hashes,
        native_changed=False,reference_rotation_degrees=0,reference_xy_translation_mm=[cx,cy],
        current_SMP_coordinates_unchanged=True,SMP_geometry='Exact saved SMP-FS-SBPCT.stp',
        copper_geometry='Supplied Assembly1.stl derived registered meshes',
        display_only_XY_overlay=True,solid_seating_or_interference_validated=False),indent=2)+'\n')
    print(str(path))


if __name__=='__main__':main()
