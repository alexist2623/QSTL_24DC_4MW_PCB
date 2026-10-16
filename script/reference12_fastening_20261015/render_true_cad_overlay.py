"""Compare zero/180-degree registration using the actual copper mesh projection.

No design changes. Current sixteen-SMP coordinates are copied from the saved
proposal, whereas the copper comes from the supplied twelve-RF assembly STL.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as PlotPath
from matplotlib.patches import PathPatch, Rectangle, Circle, Polygon as PlotPolygon
from matplotlib.lines import Line2D
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.affinity import affine_transform
from shapely.geometry.polygon import orient

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016'
REF=ROOT/'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015'
PLAN=ROOT/'QSTL_QD4_2SET_38PAD/Four_End_SMP_Side_Entry_20261015/side_entry_audit.json'


def project_mesh(path):
    reader=vtk.vtkXMLPolyDataReader();reader.SetFileName(str(path));reader.Update()
    tri=vtk.vtkTriangleFilter();tri.SetInputConnection(reader.GetOutputPort());tri.Update()
    mesh=tri.GetOutput();pts=vtk_to_numpy(mesh.GetPoints().GetData())
    faces=[]
    for i in range(mesh.GetNumberOfCells()):
        c=mesh.GetCell(i)
        if c.GetNumberOfPoints()!=3:continue
        p=Polygon([pts[c.GetPointId(k),:2] for k in range(3)])
        if p.area>1e-10:faces.append(p)
    projection=unary_union(faces)
    assert projection.is_valid
    return projection


def patch(ax,shape,**kwargs):
    polygons=[shape] if shape.geom_type=='Polygon' else list(shape.geoms)
    for p in polygons:
        if p.geom_type!='Polygon':continue
        p=orient(p,sign=1)
        vertices=[];codes=[]
        for ring in [p.exterior,*p.interiors]:
            coords=list(ring.coords)
            vertices.extend(coords)
            codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(coords)-2)+[PlotPath.CLOSEPOLY])
        ax.add_patch(PathPatch(PlotPath(vertices,codes),**kwargs))


def draw(ax,data,holes,lower,upper,angle,ylim):
    cx,cy=data['qd_centre_mm'];s=1 if angle==0 else -1
    mat=[s,0,0,s,cx,cy]
    patch(ax,affine_transform(lower,mat),fc='#ce9868',ec='#8c552e',lw=.9,alpha=.5,zorder=1)
    patch(ax,affine_transform(upper,mat),fc='none',ec='#b78968',lw=.65,ls=':',zorder=2)
    # The old PCB outline is deliberately shown separately. It has different
    # length and ZIF orientation from the current 16-RF proposal.
    old=affine_transform(Polygon([(-16.3,-41.3),(16.3,-41.3),(16.3,65.8),(-16.3,65.8)]),mat)
    patch(ax,old,fc='none',ec='#818b8f',lw=.9,ls=(0,(5,3)),zorder=3)
    ax.add_patch(Rectangle((-6.55,0),32.6,77.5,fc='none',ec='#078567',lw=2,zorder=7))
    for route in data['routes']:
        x,y=zip(*route['points_mm']);ax.plot(x,y,color='#4b899d',lw=.65,alpha=.65,zorder=4)
    for r in data['rows']:
        x,y=r['start']
        ax.add_patch(Rectangle((x-2.75,y-2.75),5.5,5.5,fc='#66b1cf',ec='#176c8b',lw=.75,alpha=.4,zorder=5))
        ax.text(x,y,r['smp'].replace('SMP',''),ha='center',va='center',fontsize=8,color='#09465d',clip_on=True,zorder=8)
    for row in data['pads']:
        p=row['after'];a=np.deg2rad(p['rotation']);c=np.cos(a);sine=np.sin(a)
        coords=np.array([[-1,-1],[1,-1],[1,1],[-1,1]],dtype=float)*[p['size_x']/2,p['size_y']/2]
        coords=coords@np.array([[c,sine],[-sine,c]])+[p['x'],p['y']]
        ax.add_patch(PlotPolygon(coords,fc='#cfaa53',ec='#917134',lw=.2,zorder=8))
    ax.add_patch(Rectangle((cx-2.15,cy-2.65),4.3,5.3,fc='#183f4a',zorder=8))
    ax.text(cx,cy,'QD',ha='center',va='center',color='white',fontsize=9,zorder=9)
    for h in holes:
        x0,y0=h['source_xy_mm'];x=cx+s*x0;y=cy+s*y0
        color='#264fb0' if h['name'][0]=='P' else '#b71f2d'
        ax.add_patch(Circle((x,y),h['measured_diameter_mm']/2,fc='white',ec=color,lw=1.5,zorder=9))
        ax.text(x+(2.2 if x<cx else -2.2),y,h['name'],ha='left' if x<cx else 'right',va='center',fontsize=9,
                color=color,weight='bold',clip_on=True,zorder=10)
    ax.plot([cx,cx],[ylim[0],ylim[1]],color='#a0b5b9',ls=':',lw=.5,zorder=0)
    ax.text(cx,3.6,'16-RF ZIF end',ha='center',fontsize=8,color='#08785e',clip_on=True,zorder=10)
    zif_y=cy+s*60
    ax.text(cx,zif_y,'Reference ZIF end',ha='center',fontsize=8,color='#666f72',clip_on=True)
    ax.set(xlim=(-10.5,30),ylim=ylim,aspect='equal',xlabel='Current PCB X (mm)',ylabel='Current PCB Y (mm)')
    ax.tick_params(labelsize=8);ax.grid(alpha=.10)
    return mat


def main():
    data=json.loads(PLAN.read_text());holes=json.loads((OUT/'pa_pattern.json').read_text())['holes']
    source=[PLAN,REF/'SMP_Side_Shell.vtp',REF/'Component_Side_Shell.vtp',
            ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc']
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    lower=project_mesh(REF/'SMP_Side_Shell.vtp');upper=project_mesh(REF/'Component_Side_Shell.vtp')
    fig,axs=plt.subplots(1,2,figsize=(12,14),dpi=190)
    matrices={}
    for ax,angle in zip(axs,(0,180)):
        matrices[str(angle)]=draw(ax,data,holes,lower,upper,angle,(-24,116))
        ax.set_title('A | Original hole-map orientation (0 deg)' if angle==0 else 'B | Previous check (180 deg rotation)',fontsize=13,pad=17)
    legend=[Line2D([0],[0],color='#a96638',lw=7,alpha=.55,label='Actual copper CAD projection'),
            Line2D([0],[0],color='#176c8b',lw=7,alpha=.6,label='Current 16-SMP body envelopes'),
            Line2D([0],[0],color='#078567',lw=2,label='Current PCB: 32.6 x 77.5 mm'),
            Line2D([0],[0],color='#818b8f',ls='--',label='Reference PCB: 32.6 x 107.1 mm')]
    fig.suptitle('Actual copper CAD + current PCB/SMP overlay',fontsize=19,y=.977)
    fig.legend(handles=legend,loc='upper center',bbox_to_anchor=(.5,.945),ncol=2,fontsize=10,frameon=False)
    fig.text(.5,.067,'Same scale and same QD datum in both panels. Only the reference CAD/hole pattern rotates; SMPs never move.\n'
             'Brown circular openings belong to the 12-RF copper carrier; blue numbered boxes are the proposed 16 SMPs.',
             ha='center',fontsize=10,linespacing=1.7)
    fig.text(.5,.025,'Source: supplied Assembly1.stl, projected in XY. This is a placement comparison, not a verified assembly fit.',
             ha='center',fontsize=9.5,color='#8f4c2b')
    fig.subplots_adjust(left=.08,right=.96,top=.865,bottom=.15,wspace=.26)
    fig.savefig(OUT/'Actual_Copper_PCB_SMP_Overlay_0_vs_180.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,13),dpi=210)
    draw(ax,data,holes,lower,upper,0,(-6,116))
    ax.set_title('Original orientation: copper CAD + current 16-SMP plan',fontsize=14,pad=20)
    fig.text(.5,.05,'Copper mesh projection: brown | Current PCB: green | Current SMP bodies: blue\n'
             'P/A labels retain the orientation of the original supplied hole map.',ha='center',fontsize=10,linespacing=1.7)
    fig.text(.5,.018,'Sample-datum alignment only; no native PCB or CAD geometry changed.',ha='center',fontsize=9.5,color='#8f4c2b')
    fig.tight_layout(rect=(0,.085,1,.99));fig.savefig(OUT/'Original_Orientation_Actual_CAD_Overlay.png');plt.close(fig)
    assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source}
    report=dict(status='READ_ONLY_OVERLAY',reference_source='Assembly1.stl registered mesh projections',
                source_hashes=hashes,source_files_unchanged=True,
                lower_projection_area_mm2=lower.area,lower_projection_bounds_mm=lower.bounds,
                upper_projection_area_mm2=upper.area,upper_projection_bounds_mm=upper.bounds,
                affine_transforms=matrices,all_current_SMP_coordinates_unchanged=True,
                reason_for_previous_visual_difference='Previous review rotated reference hole pattern 180 degrees; earlier hole map did not.',
                registration_approved=False,three_dimensional_fit_validated=False)
    (OUT/'actual_cad_overlay.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(output=str(OUT),lower_bounds=lower.bounds,upper_bounds=upper.bounds,native_changed=False)))


if __name__=='__main__':main()
