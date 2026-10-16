"""Position actual M2 screws in the read-only 12-RF PCB/mesh carrier review.

The STL is a geometry fallback because native SolidWorks translation returned
no solids. Smooth 3 mm shell bores do not prove M2 thread engagement.
"""
from pathlib import Path
import ast
import hashlib
import json
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015'
REF=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC')
PCB=REF/'PCB/Sample_Holder/Sample_Holder.step'
SCREW=ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/RC_Filter_Standalone_Holder_Concept/Standard_Fasteners/ISO_7045_H_M2x6.step'
# Reuse pure geometry/render functions without executing the previous build.
source=ROOT/'script/rc_filter_model_20261007/build_model.py'
tree=ast.parse(source.read_text())
nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in ('actor_from_part','bounds','volume')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),globals())
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label
source=ROOT/'script/rc_filter_plate_mount_20261008/build_combined_device.py'
tree=ast.parse(source.read_text())
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='read_parts']
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),globals())
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

MOUNTS=[(-12.8,37.8),(12.8,37.8),(-12.8,-37.8),(12.8,-37.8)]
SMALL=[(-12.8,-45.3),(12.8,-45.3),(-14.3,.7),(14.3,.7)]


def mesh_transform(region,matrix):
    reader=vtk.vtkXMLPolyDataReader();reader.SetFileName(str(HERE/f'mesh_region_{region}.vtp'));reader.Update()
    transform=vtk.vtkTransform();transform.SetMatrix(np.asarray(matrix).ravel())
    filt=vtk.vtkTransformPolyDataFilter();filt.SetInputConnection(reader.GetOutputPort());filt.SetTransform(transform);filt.Update()
    result=vtk.vtkPolyData();result.DeepCopy(filt.GetOutput())
    return result


def mesh_actor(mesh,color):
    normals=vtk.vtkPolyDataNormals();normals.SetInputData(mesh);normals.SetFeatureAngle(45);normals.Update()
    mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort());mapper.ScalarVisibilityOff()
    actor=vtk.vtkActor();actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color);actor.GetProperty().SetAmbient(.3);actor.GetProperty().SetDiffuse(.7)
    return actor


def image_title(path,title,subtitle,footer):
    raw=Image.open(path).convert('RGB');im=Image.new('RGB',(raw.width,raw.height+185),'white');im.paste(raw,(0,105))
    d=ImageDraw.Draw(im)
    f=lambda name,size:ImageFont.truetype('C:/Windows/Fonts/'+name,size)
    d.text((35,16),title,font=f('arialbd.ttf',30),fill='#21454d')
    d.text((35,59),subtitle,font=f('arial.ttf',22),fill='#51656b')
    d.text((35,raw.height+125),footer,font=f('arial.ttf',22),fill='#a14f2a')
    im.save(path)


def render(path,actors,position,target,scale,size=(1500,1450),labels=()):
    renderer=vtk.vtkRenderer();renderer.SetBackground(1,1,1)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetMultiSamples(0)
    window.SetAlphaBitPlanes(1);window.SetSize(*size);window.AddRenderer(renderer)
    renderer.SetUseDepthPeeling(True);renderer.SetMaximumNumberOfPeels(100);renderer.SetOcclusionRatio(.05)
    for actor in actors:renderer.AddActor(actor)
    camera=renderer.GetActiveCamera();camera.SetPosition(*position);camera.SetFocalPoint(*target)
    camera.SetViewUp(0,1,0);camera.ParallelProjectionOn();camera.SetParallelScale(scale)
    renderer.ResetCameraClippingRange();window.Render()
    points=[]
    for text,world,offset in labels:
        renderer.SetWorldPoint(*world,1);renderer.WorldToDisplay();p=renderer.GetDisplayPoint()
        points.append((text,(p[0],size[1]-p[1]),offset))
    pixels=vtk.vtkWindowToImageFilter();pixels.SetInput(window);pixels.ReadFrontBufferOff();pixels.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(pixels.GetOutputPort());writer.Write()
    window.Finalize()
    if points:
        im=Image.open(path).convert('RGB');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',24)
        for text,p,off in points:
            q=(p[0]+off[0],p[1]+off[1]);d.line([p,q],fill='#934922',width=3)
            bb=d.textbbox(q,text,font=font);d.rectangle((bb[0]-5,bb[1]-3,bb[2]+5,bb[3]+3),fill='white')
            d.text(q,text,font=font,fill='#934922')
        im.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    sources=[PCB,SCREW,REF/'Mechanical/Assembly1.stl',REF/'Mechanical/CuBoxTop_12MW_72DC.sldprt',REF/'Mechanical/CuBoxBottom_12MW_72DC.sldprt']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    # Regions are shifted/rotated only. Uniform 1000x STL scale was established
    # by the matching 75.6 x 25.6 mm PCB pattern and twelve SMP positions.
    mats={
      'upper':[[0,1,0,19.1199985743],[1,0,0,-4.05668354],[0,0,-1,5.9751763344],[0,0,0,1]],
      'lower':[[0,1,0,-18.5184959173],[1,0,0,-4.0568763733],[0,0,-1,-2.0251074466],[0,0,0,1]],
    }
    upper=mesh_transform(0,mats['upper']);lower=mesh_transform(1,mats['lower'])
    for name,mesh in [('Component_Side_Shell',upper),('SMP_Side_Shell',lower)]:
        w=vtk.vtkXMLPolyDataWriter();w.SetFileName(str(OUT/(name+'.vtp')));w.SetInputData(mesh);w.Write()
    upper_actor=mesh_actor(upper,(.74,.44,.27));lower_actor=mesh_actor(lower,(.70,.39,.22))
    print('Reading reference PCB STEP',flush=True)
    pcbparts=read_parts(PCB,'pcb')
    pcbactors=[]
    for i,p in enumerate(pcbparts):
        bb=bounds(p['shape'])
        if bb[3]-bb[0]>32 and bb[4]-bb[1]>100:
            p['color']=(.12,.36,.25)
        p['category']='component'
        pcbactors.append(actor_from_part(p))
    print(f'PCB parts: {len(pcbparts)}; generating standard screw instances',flush=True)
    screwparts=read_parts(SCREW,'M2')
    screws=[];screw_records=[]
    for index,(x,y) in enumerate(MOUNTS,1):
        tr=gp_Trsf();tr.SetValues(0,0,1,x,0,1,0,y,-1,0,0,0)
        for p in screwparts:
            shape=BRepBuilderAPI_Transform(p['shape'],tr,True).Shape()
            screws.append(actor_from_part(dict(name=f'M2x6_{index}',shape=shape,color=(.63,.69,.74),category='component')))
            screw_records.append(dict(index=index,axis_xy_mm=[x,y],under_head_z_mm=0,tip_z_mm=-6,bounds_mm=bounds(shape)))
    print('Rendering assembly views',flush=True)
    baseactors=[lower_actor]+pcbactors+screws
    render(OUT/'PCB_M2_Placement_Lid_Removed.png',baseactors,(110,-150,160),(0,10,0),61,
           labels=[('M2 x 6 (trial)',(-12.8,37.8,1.5),(-170,-75)),('PCB mounting screw',(12.8,-37.8,1.5),(40,55))])
    image_title(OUT/'PCB_M2_Placement_Lid_Removed.png','12-RF reference / M2 screw placement',
        'Upper shell hidden to expose four screws through the original PCB holes.',
        'Positioning trial only: 3.00 mm shell bores do not verify M2 thread engagement.')
    upper_actor.GetProperty().SetOpacity(.20)
    render(OUT/'Complete_Carrier_Xray_M2.png',[upper_actor]+baseactors,(110,-150,160),(0,10,0),61)
    image_title(OUT/'Complete_Carrier_Xray_M2.png','12-RF reference / complete carrier (transparent upper shell)',
        'Actual supplied PCB STEP + supplied assembly mesh + Inventor ISO 7045 H M2 x 6.',
        'Reference geometry retained; screw seating is illustrative, not a verified threaded assembly.')
    upper_actor.GetProperty().SetOpacity(1)
    render(OUT/'Complete_Carrier_Closed.png',[upper_actor]+baseactors,(110,-150,160),(0,10,0),61)
    image_title(OUT/'Complete_Carrier_Closed.png','12-RF reference / closed copper carrier',
        'Four M2 placement candidates are enclosed by the component-side shell.',
        'Thread designation is unavailable in the mesh. Mechanical compatibility remains unverified.')
    # Draw exact reference PCB outline and measured CAD hole centres separately.
    fig,ax=plt.subplots(figsize=(8,12),dpi=220)
    ax.add_patch(Rectangle((-16.3,-41.3),32.6,107.1,fc='#ecf3ee',ec='#447761',lw=1.5,label='PCB outline'))
    # Lower shell outline after registration.
    ax.add_patch(Rectangle((-16.3,-48.8),32.6,90.1,fill=False,ec='#b77040',lw=1.5,ls='--',label='SMP-side shell'))
    for i,(x,y) in enumerate(MOUNTS,1):
        ax.add_patch(Circle((x,y),1.6,fc='white',ec='#315e84',lw=1.5))
        ax.add_patch(Circle((x,y),1.0,fc='#9caab5',ec='#52646e',lw=1))
        ax.text(x+(2.7 if x<0 else -2.7),y,f'P{i}',ha='left' if x<0 else 'right',va='center',fontsize=10)
    for i,(x,y) in enumerate(SMALL,1):
        ax.add_patch(Circle((x,y),1.,fill=False,ec='#d34f34',lw=2))
        ax.annotate(f'A{i}: CAD dia. 2.0',xy=(x,y),xytext=(-25 if x<0 else 25,y+4),
                    ha='right' if x<0 else 'left',fontsize=9,color='#b53b27',arrowprops=dict(arrowstyle='-',color='#b53b27'))
    ax.text(0,53,'ZIF end',ha='center',color='#5b7365',fontsize=13)
    ax.text(0,29,'P1-P4: PCB dia. 3.2\nSMP-side shell dia. 3.0\nM2 shafts shown for comparison',ha='center',fontsize=10,linespacing=1.5)
    ax.text(0,-15,'A3/A4 lie over solid PCB:\nno matching PCB drills at these axes.',ha='center',fontsize=10,color='#b53b27',linespacing=1.5)
    ax.set(xlim=(-47,47),ylim=(-55,70),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    ax.set_title('PCB holes vs. additional copper-shell holes',pad=18,fontsize=15)
    ax.grid(alpha=.15);ax.legend(loc='upper right',fontsize=9)
    fig.text(.5,.025,'CAD axes from Assembly1.stl; nominal diameters rounded from fitted mesh sections.\nNo source PCB/CAD modifications.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.98));fig.savefig(OUT/'Additional_CAD_Holes_Map.png');plt.close(fig)
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report=dict(source_hashes=hashes,reference_files_unchanged=True,
        native_sldprt_import='Failed: zero solid bodies from both reference import and direct translator; STL fallback used',
        mesh_scale=1000,mesh_scale_basis='Matching 25.6 x 75.6 mm PCB mount pattern and twelve SMP locations',
        mesh_transforms_to_pcb_step_mm=mats,pcb_mount_axes_mm=MOUNTS,additional_cad_hole_axes_mm=SMALL,
        screws=screw_records,hardware_source='Existing unmodified Inventor Content Center ISO 7045 H M2 x 6',
        validated_threaded_assembly=False,
        findings=['PCB has diameter 3.2 mm holes; corresponding SMP-side shell has nominal diameter 3.0 mm bores.',
          'M2 has 0.5 mm radial clearance in the 3.0 mm bore; direct M2 engagement cannot be claimed.',
          'Additional nominal 2.0 mm shell axes at X +/-14.3, Y0.7 have no matching PCB drill.',
          'Two additional shell axes at X +/-12.8, Y-45.3 are beyond the PCB lower edge.',
          'Upper/lower shell mating positions inferred from matching hole and SMP patterns; no manufacturing fit or thread validation.'])
    (OUT/'fastening_review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(output=str(OUT),pcb_parts=len(pcbparts),screws=len(screw_records),validated_threaded_assembly=False,source_files_unchanged=True)),flush=True)


if __name__=='__main__':main()
