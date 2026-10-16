"""M2-registered 16-SMP mechanical review; never modify electrical/source CAD."""
from pathlib import Path
import ast
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT/'QSTL_QD4_2SET_38PAD/Mechanical_Review_20261014'
OUT.mkdir(exist_ok=True)
MECH = ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'
BASE = '9607d5bfbdd962c49c9a6d4ecce671a4de9f5552322f134225bcbadf5796e351'

# Reuse only reviewed pure geometry/render functions, not model-building code.
util = ROOT/'script/rc_filter_model_20261007/build_model.py'
tree = ast.parse(util.read_text())
names = {'box','compound','bounds','volume','count_solids','actor_from_part','export_colored'}
nodes = [n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) or
         isinstance(n,ast.FunctionDef) and n.name in names]
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(util),'exec'),globals())
from OCP.gp import gp_Ax1, gp_Vec
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    r=STEPControl_Reader();assert int(r.ReadFile(str(path)))==1
    assert r.TransferRoots()>0
    return r.OneShape()


def transform(s, rx=0, ry=0, rz=0, move=(0,0,0)):
    for axis,deg in (((1,0,0),rx),((0,1,0),ry),((0,0,1),rz)):
        if deg:
            t=gp_Trsf();t.SetRotation(gp_Ax1(gp_Pnt(0,0,0),gp_Dir(*axis)),math.radians(deg))
            s=BRepBuilderAPI_Transform(s,t,True).Shape()
    t=gp_Trsf();t.SetTranslation(gp_Vec(*move))
    return BRepBuilderAPI_Transform(s,t,True).Shape()


def cut(a,b):
    op=BRepAlgoAPI_Cut(a,b);op.Build();assert op.IsDone()
    return op.Shape()


def common(a,b):
    op=BRepAlgoAPI_Common(a,b);op.Build();assert op.IsDone()
    return op.Shape()


def cylinder(x,y,z,r,h):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z),gp_Dir(0,0,1)),r,h).Shape()


def cylinders(s):
    rows=[];e=TopExp_Explorer(s,TopAbs_FACE)
    while e.More():
        face=TopoDS.Face(e.Current());a=BRepAdaptor_Surface(face)
        if a.GetType()==GeomAbs_Cylinder:
            c=a.Cylinder();p=c.Location();d=c.Axis().Direction()
            rows.append(dict(radius=c.Radius(),point=[p.X(),p.Y(),p.Z()],axis=[d.X(),d.Y(),d.Z()]))
        e.Next()
    return rows


def part(name,shape,color,kind):
    assert BRepCheck_Analyzer(shape).IsValid(),name
    return dict(name=name,shape=shape,color=color,category=kind)


def shot(parts,path,eye,target,up,scale,size,ghost=False,explode=False):
    renderer=vtk.vtkRenderer();renderer.SetBackground(.965,.975,.982)
    renderer.SetUseDepthPeeling(True);renderer.SetMaximumNumberOfPeels(80)
    window=vtk.vtkRenderWindow();window.SetOffScreenRendering(1);window.SetMultiSamples(0)
    window.SetAlphaBitPlanes(1);window.SetSize(*size);window.AddRenderer(renderer)
    for p in parts:
        q=dict(p)
        if explode and p['category']=='copper':
            q['shape']=transform(p['shape'],move=(0,0,11 if 'Bottom_' in p['name'] else -12))
        a=actor_from_part(q);a.GetProperty().SetAmbient(.26)
        if ghost and p['category']=='copper':a.GetProperty().SetOpacity(.20)
        a.GetProperty().SetSpecular(.22);a.GetProperty().SetSpecularPower(22)
        renderer.AddActor(a)
    camera=renderer.GetActiveCamera();camera.SetPosition(*eye);camera.SetFocalPoint(*target)
    camera.SetViewUp(*up);camera.ParallelProjectionOn();camera.SetParallelScale(scale)
    renderer.ResetCameraClippingRange();window.Render()
    capture=vtk.vtkWindowToImageFilter();capture.SetInput(window);capture.ReadFrontBufferOff();capture.Update()
    w=vtk.vtkPNGWriter();w.SetFileName(str(path));w.SetInputConnection(capture.GetOutputPort());w.Write()
    window.Finalize()


def main():
    snap_path=ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
    snap=json.loads(snap_path.read_text())
    smp_path=ROOT/'QSTL_QD4_2SET_38PAD/SMP-FS-SBPCT.stp'
    copper_paths=[MECH/'Bottom_reference.step',MECH/'Top_ForFridge_reference.step']
    protected=[Path(snap['source']),ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.SchDoc',smp_path,*copper_paths]
    hashes={str(p):sha(p) for p in protected};assert hashes[str(Path(snap['source']))]==BASE
    fit=json.loads((MECH/'assembly_validation.json').read_text())
    tx,ty,tz=fit['pcb_transform']['translation_mm'];T=fit['pcb_thickness_mm']
    # Inverse of the preserved proper Ry(180) PCB-to-carrier rigid transform.
    bottom=transform(read(copper_paths[0]),ry=180,move=(tx,-ty,tz))
    top_global=transform(read(copper_paths[1]),move=fit['top_transform']['translation_mm'])
    top=transform(top_global,ry=180,move=(tx,-ty,tz))
    copper=[part('Bottom_SMP_Side_Copper',bottom,(.70,.36,.17),'copper'),
            part('Top_ForFridge_QD_Side_Copper',top,(.83,.49,.25),'copper')]
    mounts=[p for p in snap['pads'] if not p['component']]
    m2=[p for p in mounts if abs(p['hole']-2.1)<1e-4];assert len(m2)==4
    axes=[c for c in cylinders(bottom) if abs(c['radius']-.8)<1e-5 and abs(c['axis'][2])>.999]
    m2_audit=[]
    for p in m2:
        c=min(axes,key=lambda c:math.hypot(c['point'][0]-p['x'],c['point'][1]-p['y']))
        error=math.hypot(c['point'][0]-p['x'],c['point'][1]-p['y'])
        m2_audit.append(dict(pcb_xy_mm=[p['x'],p['y']],copper_xy_mm=c['point'][:2],axis_error_mm=error,
                             pcb_clearance_diameter_mm=p['hole'],reference_tap_drill_mm=2*c['radius']))
    assert max(x['axis_error_mm'] for x in m2_audit)<1e-5,m2_audit
    print('M2 axes aligned',flush=True)
    raw_smp=read(smp_path);local_smp=transform(raw_smp,rx=90)
    model_audit=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_models.json').read_text())
    smp_models=[p for p in model_audit['models'] if p['component'].startswith('SMP')]
    assert len(smp_models)==16 and all(m['rotation_xyz_deg']==[90.,0.,0.] for m in smp_models)
    dz=smp_models[0]['dz_mm']
    saved=[dict(name=m['component'],x=m['origin_mm'][0],y=m['origin_mm'][1]) for m in smp_models]
    relocation_file=ROOT/'script/rf_redline_review_20261011/corrected_endpair_measurements.json'
    relocation=json.loads(relocation_file.read_text())
    proposed=relocation['candidate']['centres'];assert len(proposed)==16
    src_center=next(p for p in snap['pads'] if p['component']=='SMP35' and p['number']=='1')
    smp_pads=[p for p in snap['pads'] if p['component']=='SMP35']
    layouts={'Saved_7Rows':saved,'Relocation_Horizontal_End_Pairs':proposed}
    records={};grouped={}
    # Exact preserved pocket profile, rotated with QD: 4.3 x 5.3 mm, R0.5.
    pocket_parts=[box(8.1,39.85,-.01,3.3,5.3,1.21),box(7.6,40.35,-.01,4.3,4.3,1.21)]
    for x in (8.1,11.4):
        for y in (40.35,44.65):pocket_parts.append(cylinder(x,y,-.01,.5,1.21))
    pocket=pocket_parts[0]
    for p in pocket_parts[1:]:pocket=BRepAlgoAPI_Fuse(pocket,p).Shape()
    for name,locs in layouts.items():
        print('Build',name,flush=True)
        holes=[cylinder(p['x'],p['y'],-.1,p['hole']/2,T+.2) for p in mounts]
        for loc in locs:
            for p in smp_pads:
                holes.append(cylinder(loc['x']+p['x']-src_center['x'],loc['y']+p['y']-src_center['y'],
                                      -.1,p['hole']/2,T+.2))
        board=cut(cut(box(0,0,0,19.5,67.9,T),compound(holes)),pocket)
        parts=copper+[part('PCB_19p5x67p9_M2_Registered',board,(.055,.32,.22),'board')]
        for i,p in enumerate(locs):
            parts.append(part(p['name'],transform(local_smp,move=(p['x'],p['y'],T+dz)),(.78,.80,.82),'SMP'))
        target=OUT/(name+'_Copper_M2_Review.step')
        export_colored(parts,target,name+'_M2_Size_Review')
        reopened=read(target);original=compound([p['shape'] for p in parts])
        assert BRepCheck_Analyzer(reopened).IsValid()
        assert count_solids(reopened)==count_solids(original)
        assert max(abs(a-b) for a,b in zip(bounds(reopened),bounds(original)))<2e-5
        assert abs(volume(reopened)-volume(original))<.02
        records[name]=dict(step=str(target),sha256=sha(target),smp_centres=locs,valid=True,
                           solids=count_solids(reopened),bounds_mm=bounds(reopened),
                           volume_delta_mm3=volume(reopened)-volume(original))
        grouped[name]=parts
        shot(parts,HERE/(name+'_top_raw.png'),(9.75,36,180),(9.75,36,0),(0,1,0),43,(900,1800),ghost=True)
        shot(parts,HERE/(name+'_oblique_raw.png'),(90,110,125),(9.75,38,0),(0,1,0),44,(1100,1700),ghost=True)
    shot(grouped['Relocation_Horizontal_End_Pairs'],HERE/'relocation_exploded_raw.png',
         (90,115,150),(9.75,38,0),(0,1,0),48,(1200,1800),explode=True)
    print('Models and renders complete',flush=True)
    # Quantify substrate/case fit independently of intentionally ignored SMP holes.
    bare=box(0,0,0,19.5,67.9,T)
    baseline={p['name']:volume(common(p['shape'],bare)) for p in copper}
    trials=[]
    for label,x0,x1,y1 in [('W19p5',0,19.5,67.9),('W20',-.25,19.75,67.9),
                          ('W21',-.75,20.25,67.9),('W22',-1.25,20.75,67.9),
                          ('L68p0',0,19.5,68),('L68p1',0,19.5,68.1),('L70',0,19.5,70)]:
        probe=box(x0,0,0,x1-x0,y1,T)
        overlap={p['name']:volume(common(p['shape'],probe)) for p in copper}
        trials.append(dict(name=label,board_bounds_xy_mm=[x0,0,x1,y1],overlap_mm3=overlap,
                           incremental_overlap_mm3={n:v-baseline[n] for n,v in overlap.items()}))
    # These reference planar faces are independently present in source inspection.
    left=tx-26.24782402436659;right=tx-6.636108289443491
    end=72.8-ty
    report=dict(status='MECHANICAL_ENVELOPE_REVIEW_ONLY',native_pcb_sha256=BASE,
                pcb_size_mm=[19.5,67.9,T],m2_registration=m2_audit,
                copper_bounds_pcb_frame={p['name']:bounds(p['shape']) for p in copper},
                inverse_carrier_transform=dict(ry_deg=180,translation_mm=[tx,-ty,tz]),
                QD_side_skirt_inner_X_mm=[left,right],skirt_clear_width_mm=right-left,
                fixed_M2_left_margin_mm=-left,fixed_M2_right_margin_mm=right-19.5,
                SMP_side_end_lip_Y_mm=end,current_positive_Y_margin_mm=end-67.9,
                rectangular_substrate_overlap_tests=trials,baseline_substrate_only_overlap_mm3=baseline,
                outputs=records,source_hashes=hashes,latest_relocation_source=str(relocation_file),
                latest_relocation_source_sha256=sha(relocation_file),
                limitations=['SMP-to-legacy-copper-hole mismatches intentionally ignored as instructed.',
                    'SMP poses use exact embedded source STEP; no mating plugs or screw heads are included.',
                    'R0603/C1206 placement and routing are not rendered or validated in this outline review.',
                    'The relocation is the corrected horizontal inward end-pair candidate, not the rejected 3/3/2 rows.',
                    'Existing side-wall and nominal-seat overlap is retained; outer copper width is not usable PCB width.',
                    'The ZIF-end negative-Y expansion is not bounded by these two copper parts alone; rod/cable/adapter limits are absent.',
                    'No native PCB, source copper, Gerber or fabrication package is modified.'])
    assert hashes=={str(p):sha(p) for p in protected}
    report['source_files_unchanged']=True
    (OUT/'mechanical_review.json').write_text(json.dumps(report,indent=2)+'\n')
    compose(report)
    print(json.dumps({k:report[k] for k in ('QD_side_skirt_inner_X_mm','skirt_clear_width_mm',
                     'fixed_M2_left_margin_mm','fixed_M2_right_margin_mm','current_positive_Y_margin_mm')},indent=2))


def compose(r):
    fig,axes=plt.subplots(1,3,figsize=(16,10),dpi=180)
    images=['Saved_7Rows_oblique_raw.png','Relocation_Horizontal_End_Pairs_oblique_raw.png','relocation_exploded_raw.png']
    titles=['Saved 16-SMP / seven rows','Latest relocation / horizontal end pairs','Relocation / exploded copper parts']
    for ax,image,title in zip(axes,images,titles):
        ax.imshow(Image.open(HERE/image));ax.axis('off');ax.set_title(title,fontsize=12,pad=12)
    fig.suptitle('16-SMP PCB + existing copper carrier | Four M2 axes registered',fontsize=17,y=.97)
    fig.text(.5,.914,'PCB 19.50 x 67.90 mm | Copper: Bottom + Top_ForFridge | SMP-to-copper-hole mismatch ignored',ha='center',fontsize=11)
    fig.text(.5,.085,'Left and centre: copper shown translucent to expose the PCB. Right: copper separated only for viewing.',ha='center',fontsize=10)
    fig.text(.5,.055,'R/C, connector plugs and screw heads omitted. Mechanical review only; native PCB and source copper unchanged.',ha='center',fontsize=10,color='#596d78')
    fig.subplots_adjust(left=.015,right=.985,top=.86,bottom=.115,wspace=.015)
    fig.savefig(OUT/'SMP16_Copper_M2_Assembly.png');plt.close(fig)
    fig,(ax,detail)=plt.subplots(1,2,figsize=(13,10),dpi=180,gridspec_kw={'width_ratios':[1.15,1]})
    ax.imshow(Image.open(HERE/'Relocation_Horizontal_End_Pairs_top_raw.png'),extent=(-11.75,31.25,-7,79))
    ax.add_patch(Rectangle((0,0),19.5,67.9,fill=False,edgecolor='#087f55',lw=1.7))
    for p in r['m2_registration']:
        x,y=p['pcb_xy_mm'];ax.add_patch(Circle((x,y),1.5,fill=False,edgecolor='#cc2942',lw=1.4));ax.plot(x,y,'+',color='#cc2942',ms=8)
    ax.annotate('',xy=(0,-2.5),xytext=(19.5,-2.5),arrowprops=dict(arrowstyle='<->',color='#087f55'))
    ax.text(9.75,-4,'PCB width 19.50 mm',ha='center',color='#087f55',fontsize=10)
    ax.annotate('',xy=(-3,0),xytext=(-3,67.9),arrowprops=dict(arrowstyle='<->',color='#087f55'))
    ax.text(-4.5,34,'PCB length 67.90 mm',rotation=90,ha='right',va='center',color='#087f55',fontsize=10)
    ax.axhline(r['SMP_side_end_lip_Y_mm'],xmin=.16,xmax=.85,color='#b16934',ls='--',lw=1)
    ax.text(21,65.5,'End lip\nY = 68.04\n+0.14 mm',color='#945427',fontsize=10)
    ax.set(xlim=(-9,31),ylim=(-7,80),aspect='equal');ax.axis('off');ax.set_title('M2-registered plan / relocation candidate',fontsize=12)
    left,right=r['QD_side_skirt_inner_X_mm']
    detail.set_xlim(-.9,20.4);detail.set_ylim(-2.9,4.5)
    detail.add_patch(Rectangle((left-.5,-.6),.5,2.5,facecolor='#bd743e'))
    detail.add_patch(Rectangle((right,-.6),.5,2.5,facecolor='#bd743e'))
    detail.add_patch(Rectangle((0,0),19.5,r['pcb_size_mm'][2],facecolor='#237b59',edgecolor='#07422b'))
    detail.add_patch(Rectangle((right,0),19.5-right,r['pcb_size_mm'][2],facecolor='#e45154'))
    for x in (0,19.5):detail.plot([x,x],[-.6,2.5],ls=':',color='#1c6e4e',lw=.8)
    detail.annotate('',xy=(left,2.6),xytext=(right,2.6),arrowprops=dict(arrowstyle='<->',color='#985826'))
    detail.text((left+right)/2,2.85,f'Copper skirt inner width {right-left:.3f} mm',ha='center',fontsize=11,color='#985826')
    detail.text(0,-1.1,f'Left margin\n{r["fixed_M2_left_margin_mm"]:.3f} mm',ha='left',fontsize=10)
    detail.text(19.5,-1.1,f'Right wall overlap\n{-r["fixed_M2_right_margin_mm"]:.3f} mm',ha='right',fontsize=10,color='#b7333c')
    detail.text(9.75,.8,'PCB / thickness 1.588 mm',ha='center',va='center',color='white',fontsize=10)
    detail.set_aspect('equal');detail.axis('off');detail.set_title('Width envelope schematic / measured CAD faces',fontsize=12,pad=10)
    fig.suptitle('PCB growth envelope with the existing copper parts unchanged',fontsize=17,y=.96)
    fig.text(.75,.24,'With M2 axes fixed, symmetric width growth\nis blocked by the existing side wall.\nThe current right edge already overlaps by 0.061 mm.',ha='center',fontsize=11,color='#943a37')
    fig.text(.75,.15,'Positive-Y growth: about 0.14 mm to the end lip.\nThe open ZIF end has no finite limit from these\ntwo copper parts alone; surroundings are not included.',ha='center',fontsize=10,color='#405f6d')
    fig.text(.5,.055,'Nominal CAD dimensions, not a tolerance-qualified maximum board size. Existing seating overlap is retained. Red circles: four M2 mounting axes.',ha='center',fontsize=9,color='#5e6d78')
    fig.subplots_adjust(left=.03,right=.98,top=.90,bottom=.08,wspace=.05)
    fig.savefig(OUT/'PCB_Copper_Growth_Envelope.png');plt.close(fig)


if __name__=='__main__':main()
