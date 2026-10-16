"""Check the current long-board proposal against preserved copper STEP solids."""
import json
import math
from pathlib import Path
import numpy as np
from build_review import (ROOT,HERE,MECH,read,transform,box,cut,common,cylinder,
                         compound,bounds,volume,cylinders,part,shot,sha)
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle,Circle

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Mechanical_Review_20261015'
OUT.mkdir(exist_ok=True)


def wire_xy(ax,shape,color):
    exp=TopExp_Explorer(shape,TopAbs_EDGE)
    while exp.More():
        a=BRepAdaptor_Curve(TopoDS.Edge(exp.Current()))
        t=np.linspace(a.FirstParameter(),a.LastParameter(),45)
        pts=[a.Value(float(v)) for v in t]
        ax.plot([p.X() for p in pts],[p.Y() for p in pts],color=color,lw=.35,alpha=.6)
        exp.Next()


def pocket(cx,cy):
    w,h,r=4.3,5.3,.5
    pieces=[box(cx-w/2+r,cy-h/2,-.01,w-2*r,h,1.21),
            box(cx-w/2,cy-h/2+r,-.01,w,h-2*r,1.21)]
    for x in (cx-w/2+r,cx+w/2-r):
        for y in (cy-h/2+r,cy+h/2-r):pieces.append(cylinder(x,y,-.01,r,1.21))
    result=pieces[0]
    for p in pieces[1:]:result=BRepAlgoAPI_Fuse(result,p).Shape()
    return result


def main():
    proposal_path=ROOT/'QSTL_QD4_2SET_38PAD/Outline_Mount_Concept_20261014/qd_gap_midpoint_audit.json'
    proposal=json.loads(proposal_path.read_text())
    old=json.loads((ROOT/'QSTL_QD4_2SET_38PAD/Mechanical_Review_20261014/mechanical_review.json').read_text())
    fit=json.loads((MECH/'assembly_validation.json').read_text());T=fit['pcb_thickness_mm']
    paths=[MECH/'Bottom_reference.step',MECH/'Top_ForFridge_reference.step',proposal_path]
    paths += [ROOT/'QSTL_QD4_2SET_38PAD'/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    t=old['inverse_carrier_transform']['translation_mm']
    bottom=transform(read(paths[0]),ry=180,move=t)
    top=transform(transform(read(paths[1]),move=fit['top_transform']['translation_mm']),ry=180,move=t)
    shapes={'Bottom_SMP_Side':bottom,'Top_ForFridge_QD_Side':top}
    B={n:bounds(s) for n,s in shapes.items()}
    axes={n:[c for c in cylinders(s) if abs(c['axis'][2])>.999 and abs(c['radius']-(.8 if n.startswith('Bottom') else 2.1))<1e-5] for n,s in shapes.items()}
    registrations=[]
    for p in proposal['mounts']:
        if abs(p['hole']-2.1)>.01:continue
        errors={n:min(math.dist(c['point'][:2],[p['x'],p['y']]) for c in ac) for n,ac in axes.items()}
        registrations.append(dict(group=p['concept_group'],pcb_xy=[p['x'],p['y']],axis_error_mm=errors))
    assert all(max(m['axis_error_mm'].values())<1e-5 for m in registrations if m['group']=='fixed_lower_M2')
    envelope=box(0,0,0,19.5,77.5,T)
    holes=[cylinder(p['x'],p['y'],-.1,p['hole']/2,T+.2) for p in proposal['mounts']]
    board=cut(cut(envelope,compound(holes)),pocket(*proposal['new_qd_centre_mm']))
    print('Aligned copper and generated proposal envelope',flush=True)
    intersections={n:common(s,board) for n,s in shapes.items()}
    actual_overlap={n:volume(s) for n,s in intersections.items()}
    old_envelope=box(0,0,0,19.5,67.9,T)
    old_overlap={n:volume(common(s,old_envelope)) for n,s in shapes.items()}
    new_overlap={n:volume(common(s,envelope)) for n,s in shapes.items()}
    lip=old['SMP_side_end_lip_Y_mm'];centre=proposal['new_qd_centre_mm']
    r=dict(status='EXISTING_COPPER_DOES_NOT_FIT_CURRENT_PROPOSAL',board_mm=[19.5,77.5,T],
        qd_centre_mm=centre,registration='Preserved rigid transform; fixed lower M2 axes independently matched.',
        mount_registration=registrations,copper_bounds_pcb_frame=B,
        positive_Y_outer_overhang_mm={n:max(0.,77.5-b[4]) for n,b in B.items()},
        positive_Y_outer_margin_mm={n:b[4]-77.5 for n,b in B.items()},
        end_lip_start_y_mm=lip,PCB_length_beyond_lip_start_mm=77.5-lip,
        inherited_right_skirt_overlap_mm=-old['fixed_M2_right_margin_mm'],
        baseline_rectangular_overlap_mm3=old_overlap,current_rectangular_overlap_mm3=new_overlap,
        incremental_rectangular_overlap_mm3={n:new_overlap[n]-old_overlap[n] for n in shapes},
        current_board_with_mounts_and_moved_blind_pocket_overlap_mm3=actual_overlap,
        source_hashes=hashes,source_files_unchanged=True,
        limitations=['Actual preserved STEP solids and lower-M2 registration are used.',
          'SMP-to-legacy-copper openings are intentionally excluded from fit certification, as previously instructed.',
          'Board model contains current mounting holes and moved blind pocket, but excludes SMP drills and passives.',
          'Overlap volumes are nominal CAD geometry; source seating/wall overlaps are distinguished by the baseline.',
          'Copper parts are not resized, remachined or overwritten. No tolerances, fasteners, cables or rod are evaluated.'])
    parts=[part('PCB_current_77p5',board,(.08,.48,.29),'board')]
    parts += [part(n,s,(.78,.43,.22) if n.startswith('Bottom') else (.79,.57,.35),'copper') for n,s in shapes.items()]
    parts += [part(n+'_intersection',s,(.85,.10,.17),'interference') for n,s in intersections.items() if volume(s)>1e-7]
    shot(parts,HERE/'current_77p5_copper_oblique.png',(80,110,135),(9.75,40,0),(0,1,0),46,(1100,1700),ghost=True)
    print('Solid intersection check and render complete',flush=True)
    fig=plt.figure(figsize=(13,13),dpi=180)
    gs=fig.add_gridspec(2,2,width_ratios=(.8,1.3),height_ratios=(1.2,.8),
        left=.04,right=.97,top=.91,bottom=.13,wspace=.15,hspace=.2)
    view=fig.add_subplot(gs[:,0]);zoom=fig.add_subplot(gs[0,1]);table=fig.add_subplot(gs[1,1])
    view.imshow(Image.open(HERE/'current_77p5_copper_oblique.png'));view.axis('off')
    view.set_title('Current PCB with preserved copper\nRed = nominal solid intersections',fontsize=11)
    wire_xy(zoom,bottom,'#b06e38');wire_xy(zoom,top,'#678a9d')
    zoom.add_patch(Rectangle((0,0),19.5,77.5,fc='none',ec='#187c55',lw=1.7))
    for y,c,label in ((77.5,'#187c55','PCB top 77.50'),(B['Bottom_SMP_Side'][4],'#b06e38','Bottom outer end 75.44'),
                       (B['Top_ForFridge_QD_Side'][4],'#678a9d','Top outer end 79.44'),(lip,'#b72f39','End lip starts 68.04')):
        zoom.plot([-.6,20.2],[y,y],c=c,ls='--',lw=.9)
        zoom.text(21,y,label,color=c,fontsize=9,va='center')
    for m in registrations:
        if m['group']!='upper_M2':continue
        x,y=m['pcb_xy'];zoom.add_patch(Circle((x,y),1.05,fc='none',ec='#c12b48',lw=1.6))
        zoom.scatter(x,65.33999922,c='#9d6b34',marker='+',s=65)
        zoom.annotate('',xy=(x,75),xytext=(x,65.33999922),arrowprops=dict(arrowstyle='<->',color='#c12b48',lw=1.))
    zoom.text(9.75,70.2,'Upper M2 axis shift\n+9.66 mm vs copper',ha='center',fontsize=9,color='#b02740',
        bbox=dict(fc='white',ec='none',alpha=.85))
    zoom.set(xlim=(-1,35),ylim=(62.5,81),aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    zoom.set_title('Upper end: projected edges from actual STEP solids',fontsize=11)
    table.axis('off')
    lines=[('Bottom copper outer overhang','2.06 mm'),('Top copper outer margin','1.94 mm'),
        ('Beyond existing end-lip start','9.46 mm'),('Upper M2 axis mismatch','9.66 mm'),
        ('Lower M2 axes','Aligned (<0.00001 mm)'),('Inherited right skirt overlap','0.061 mm')]
    tt=table.table(cellText=lines,colLabels=['Current geometry vs unchanged copper','Result'],cellLoc='left',
        colWidths=[.63,.37],bbox=[0,.15,1,.85]);tt.auto_set_font_size(False);tt.set_fontsize(10)
    for (rr,cc),cell in tt.get_celld().items():
        cell.set_edgecolor('#d7dfdf');cell.set_facecolor('#244550' if rr==0 else '#f5efea')
        cell.get_text().set_color('white' if rr==0 else '#2f4146')
    fig.suptitle('Current 77.50 mm PCB does not fit the unchanged copper parts',fontsize=18,y=.975)
    fig.text(.5,.944,'Aligned using the fixed lower M2 pair | Copper geometry is unchanged | QD centre = (9.75, 46.15) mm',ha='center',fontsize=10.5)
    fig.text(.5,.085,'The board exceeds Bottom copper and intersects the existing end lip. Being inside Top outer bounds is not a fit check.',ha='center',fontsize=10)
    fig.text(.5,.058,'Upper mounting holes and the moved QD/device region require corresponding carrier revisions.',ha='center',fontsize=10)
    fig.text(.5,.031,'Nominal CAD review only. SMP-opening mismatches, passives, screw heads, mating cables and rod are excluded. Source files preserved.',ha='center',fontsize=9.2,color='#8c4e3e')
    fig.savefig(OUT/'Current_Proposal_Copper_Clearance_Review.png');plt.close(fig)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in paths}
    (OUT/'current_proposal_copper_audit.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','positive_Y_outer_overhang_mm','positive_Y_outer_margin_mm',
        'PCB_length_beyond_lip_start_mm','mount_registration','current_board_with_mounts_and_moved_blind_pocket_overlap_mm3')},indent=2))


if __name__=='__main__':main()
