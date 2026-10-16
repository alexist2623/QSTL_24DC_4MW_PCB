"""Update the mechanical proposal: actual ZIF clears copper by >=10 mm.

P3/P4 end follows the reference PCB end. A1/A2 are omitted as requested.
Native PCB, reference copper and electrical routes are not modified.
"""
from pathlib import Path
from copy import deepcopy
import ast
import hashlib
import json
import math
import numpy as np
import vtk
from PIL import Image, ImageDraw, ImageFont
import build_fastening_review as cad
from render_plain_cad_overlay import poly_actor
from OCP.gp import gp_Trsf,gp_Ax1,gp_Ax2,gp_Pnt,gp_Dir,gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox,BRepPrimAPI_MakeCylinder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut,BRepAlgoAPI_Common
from OCP.BRepCheck import BRepCheck_Analyzer

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'QSTL_QD4_2SET_38PAD/ZIF10mm_Reference_End_20261016'
REF=ROOT/'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015'
PLAN=ROOT/'QSTL_QD4_2SET_38PAD/Four_End_SMP_Side_Entry_20261015/side_entry_audit.json'
SMP=ROOT/'QSTL_QD4_2SET_38PAD/SMP-FS-SBPCT.stp'
ZIF=HERE/'Current_ZIF_Embedded.step'


def positioned(shape,x,y,z):
    t=gp_Trsf();t.SetTranslation(gp_Vec(x,y,z))
    return BRepBuilderAPI_Transform(shape,t,True).Shape()


def local_model(path,name):
    parts=cad.read_parts(path,name)
    t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(1,0,0)),math.pi/2)
    return [dict(p,shape=BRepBuilderAPI_Transform(p['shape'],t,True).Shape(),category='component') for p in parts]


def main():
    OUT.mkdir(exist_ok=True)
    data=json.loads(PLAN.read_text());cx,cy=data['qd_centre_mm']
    zmeta=json.loads((HERE/'saved_zif_geometry.json').read_text())
    holes=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016/pa_pattern.json').read_text())['holes']
    source=[PLAN,SMP,ZIF,REF/'SMP_Side_Shell.vtp',REF/'Component_Side_Shell.vtp',
            ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc',
            ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.SchDoc']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    meshes={};copper_bounds={}
    for name in ('SMP_Side_Shell','Component_Side_Shell'):
        r=vtk.vtkXMLPolyDataReader();r.SetFileName(str(REF/(name+'.vtp')));r.Update()
        t=vtk.vtkTransform();t.Translate(cx,cy,0);t.RotateZ(180)
        f=vtk.vtkTransformPolyDataFilter();f.SetInputConnection(r.GetOutputPort());f.SetTransform(t);f.Update()
        m=vtk.vtkPolyData();m.DeepCopy(f.GetOutput());meshes[name]=m;copper_bounds[name]=list(m.GetBounds())
    copper_end=min(b[2] for b in copper_bounds.values())
    old_record=zmeta['saved_model_record'];old_x,old_y=old_record['origin_mm']
    old_max_y=old_y+zmeta['rotated_local_bounds_mm'][4]
    dy=math.floor((copper_end-10.0-old_max_y)*1000)/1000
    new_y=old_y+dy
    ymin=dy; ymax=cy+41.3; thickness=1.6
    active=[]
    for h in holes:
        if h['name'] in ('A1','A2'):continue
        active.append(dict(h,xy_mm=[cx-h['source_xy_mm'][0],cy-h['source_xy_mm'][1]]))
    assert len(active)==6
    # Build a review-only substrate and preserve the nominal blind QD pocket.
    board=BRepPrimAPI_MakeBox(gp_Pnt(-6.55,ymin,-thickness),32.6,ymax-ymin,thickness).Shape()
    for h in active:
        x,y=h['xy_mm'];r=h['measured_diameter_mm']/2
        tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,-2),gp_Dir(0,0,1)),r,3).Shape()
        board=BRepAlgoAPI_Cut(board,tool).Shape()
    # Rounded 4.3 x 5.3 mm pocket, depth 1.2 mm from the QD/Bottom face.
    pockets=[BRepPrimAPI_MakeBox(gp_Pnt(cx-1.65,cy-2.65,-1.601),3.3,5.3,1.201).Shape(),
             BRepPrimAPI_MakeBox(gp_Pnt(cx-2.15,cy-2.15,-1.601),4.3,4.3,1.201).Shape()]
    for x in (cx-1.65,cx+1.65):
        for y in (cy-2.15,cy+2.15):
            pockets.append(BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,-1.601),gp_Dir(0,0,1)),.5,1.201).Shape())
    for tool in pockets:board=BRepAlgoAPI_Cut(board,tool).Shape()
    assert BRepCheck_Analyzer(board).IsValid()
    # Add the component-pin drills from the saved footprint to this CAD envelope.
    snapshot=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
    template=[p for p in snapshot['pads'] if p['component']=='SMP35'];sc=next(p for p in template if p['number']=='1')
    component_drill_count=0
    for row in data['rows']:
        for p in template:
            if p['hole']<=0:continue
            x=row['start'][0]+p['x']-sc['x'];y=row['start'][1]+p['y']-sc['y']
            tool=BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,-2),gp_Dir(0,0,1)),p['hole']/2,3).Shape()
            board=BRepAlgoAPI_Cut(board,tool).Shape();component_drill_count+=1
    assert BRepCheck_Analyzer(board).IsValid()
    parts=[dict(name='Proposed_PCB_Envelope',shape=board,color=(.06,.40,.25),category='board')]
    actors=[]
    for name,opacity in [('SMP_Side_Shell',1.),('Component_Side_Shell',.10)]:
        a=cad.mesh_actor(meshes[name],(.77,.45,.24));a.GetProperty().SetOpacity(opacity);actors.append(a)
    a=cad.actor_from_part(parts[0]);a.GetProperty().SetOpacity(.22);actors.append(a)
    frame=[(-6.55,ymin,.03),(26.05,ymin,.03),(26.05,ymax,.03),(-6.55,ymax,.03)]
    actors.append(poly_actor(frame,(.02,.50,.30),1,True,3))
    for row in data['rows']:
        for p in local_model_cache:
            q=dict(p,name=row['smp'],shape=positioned(p['shape'],*row['start'],.6))
            parts.append(q);actors.append(cad.actor_from_part(q))
    zif_parts=[]
    for p in local_model(ZIF,'J1'):
        q=dict(p,name='J1_actual_saved_ZIF',shape=positioned(p['shape'],old_x,new_y,old_record['dz_mm']))
        parts.append(q);zif_parts.append(q);actors.append(cad.actor_from_part(q))
    zb=[cad.bounds(p['shape']) for p in zif_parts]
    zif_bounds=[min(b[i] for b in zb) if i<3 else max(b[i] for b in zb) for i in range(6)]
    gaps={name:b[2]-zif_bounds[4] for name,b in copper_bounds.items()}
    assert min(gaps.values())>=10.0
    for row in data['pads']:
        p=row['after'];a=np.deg2rad(p['rotation']);c=np.cos(a);s=np.sin(a)
        xy=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],float)*[p['size_x']/2,p['size_y']/2]
        xy=xy@np.array([[c,s],[-s,c]])+[p['x'],p['y']]
        actors.append(poly_actor([(x,y,.08) for x,y in xy],(.86,.69,.25)))
    actors.append(poly_actor([(cx-2.15,cy-2.65,.08),(cx+2.15,cy-2.65,.08),
                             (cx+2.15,cy+2.65,.08),(cx-2.15,cy+2.65,.08)],(.10,.21,.24)))
    # Excluded CAD A1/A2 may remain visible above the new PCB boundary.
    target_y=(ymin+max(b[3] for b in copper_bounds.values()))/2
    scale=(max(b[3] for b in copper_bounds.values())-ymin)/2+7
    size=(1450,2300);path=OUT/'Copper_PCB_ZIF_10mm_Overlay.png'
    cad.render(path,actors,(cx,target_y,220),(cx,target_y,0),scale,size=size)
    im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im)
    font=lambda n:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
    def pixel(x,y):return (size[0]/2+(x-cx)*size[1]/(2*scale),size[1]/2-(y-target_y)*size[1]/(2*scale))
    d.rectangle((0,0,size[0],62),fill='white')
    d.text((28,16),'ZIF clearance 10 mm | P3/P4 end matched to reference PCB',font=font(27),fill='#29464a')
    # Exact Y-separation dimension from copper near edge to real ZIF body.
    xdim=29.0;p=pixel(xdim,copper_end);q=pixel(xdim,zif_bounds[4]);col='#a03e23'
    d.line([p,q],fill=col,width=3)
    for point,direction in [(p,1),(q,-1)]:
        d.polygon([point,(point[0]-7,point[1]+13*direction),(point[0]+7,point[1]+13*direction)],fill=col)
    d.text((p[0]+12,(p[1]+q[1])/2-13),'10.00 mm',font=font(25),fill=col)
    for y,xstart in [(copper_end,26.05),(zif_bounds[4],zif_bounds[3])]:
        d.line([pixel(xstart,y),pixel(xdim,y)],fill=col,width=2)
    px,py=pixel(26.05,ymax)
    d.line([(px,py),(px+90,py)],fill='#176444',width=2)
    d.text((px+12,py-62),'Reference\nPCB end',font=font(23),fill='#176444')
    for h in active:
        x,y=h['xy_mm'];px,py=pixel(x,y)
        d.text((px+(28 if x<cx else -65),py-13),h['name'],font=font(22),fill='#234b65')
    d.text((30,size[1]-65),'PCB envelope: 32.600 x 99.025 mm | A1/A2 excluded',font=font(24),fill='#29464a')
    d.text((30,size[1]-31),'Mechanical proposal; native PCB/DC routing unchanged. Copper shown from supplied STL.',font=font(20),fill='#60777a')
    im.save(path)
    # Save an editable STEP mechanical preview (copper remains the original mesh).
    util=ROOT/'script/rc_filter_model_20261007/build_model.py';tree=ast.parse(util.read_text())
    env=dict(cad.__dict__)
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('compound','export_colored')]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(util),'exec'),env)
    step=OUT/'Proposed_PCB_SMP_ZIF_Envelope.step'
    env['export_colored'](parts,step,'Proposed_PCB_SMP_ZIF_ZIF10mm')
    reopened=cad.read_parts(step,'verify')
    assert len(reopened)==len(parts)
    for saved,original in zip(reopened,parts):
        assert max(abs(a-b) for a,b in zip(cad.bounds(saved['shape']),cad.bounds(original['shape'])))<1e-5
    # Retain geometry, not stale pass/fail assertions tied to the old mounts.
    proposal={key:deepcopy(data[key]) for key in ('rows','pads','routes','qd_centre_mm')}
    proposal.update(status='MECHANICAL_PROPOSAL_ZIF10MM_REFERENCE_END',board_bounds_xy_mm=[-6.55,ymin,26.05,ymax],
        board_size_mm=[32.6,ymax-ymin,thickness],mounts=active,excluded_mount_ids=['A1','A2'],
        reference_rotation_degrees=180,reference_translation_mm=[cx,cy],
        ZIF=dict(model_sha256=zmeta['model_sha256'],old_origin_mm=[old_x,old_y],new_origin_mm=[old_x,new_y],
                 delta_y_mm=dy,bounds_mm=zif_bounds,copper_Y_gap_mm=gaps,
                 translated_pads=[dict(p,y=p['y']+dy) for p in snapshot['pads'] if p['component']=='J1']),
        all_SMP_QD_RF_coordinates_unchanged=True,component_pin_drill_count=component_drill_count,
        source_hashes=hashes,source_files_unchanged=True,native_electrical_implementation=False,
        DC_routing_masks_fences_and_DRC_not_updated=True,
        mounting_diameter_scope='Measured P3.2/A2.0 diameters retained in mechanical preview; final A PCB clearance specification not released',
        ZIF_distance_basis='Positive 10 mm Y separating-plane gap proves >=10 mm Euclidean distance to both full copper meshes; no solid seating claim',
        step_path=str(step),step_reopened_geometry_checked=True)
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    assert proposal['rows']==data['rows'] and proposal['pads']==data['pads'] and proposal['routes']==data['routes']
    (OUT/'updated_mechanical_plan.json').write_text(json.dumps(proposal,indent=2)+'\n')
    print(json.dumps(dict(size_mm=proposal['board_size_mm'],zif_delta_y_mm=dy,zif_copper_gap_mm=gaps,
         board_end_y_mm=ymax,active_holes=[h['name'] for h in active],native_changed=False,output=str(OUT)),indent=2))


if __name__=='__main__':
    local_model_cache=local_model(SMP,'SMP')
    main()
