"""Read-only native/Gerber size comparison with equal-scale outline drawings."""
import hashlib
import importlib.util
import json
import re
import zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch, Rectangle
from shapely.geometry import Polygon

ROOT=Path(__file__).resolve().parents[2]
REF=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/PCB/Sample_Holder')
OUT=ROOT/'QSTL_QD4_2SET_38PAD/Sample_Holder_Size_Comparison_20261015'
OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('reader',ROOT/'script/_support/zif_revision_v2/render_native_layout.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def rod_dimensions():
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib
    path=ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Probe_H_Frame/Probe_H_Frame.step'
    reader=STEPControl_Reader();assert reader.ReadFile(str(path))==IFSelect_RetDone
    reader.TransferRoots();shape=reader.OneShape()
    explorer=TopExp_Explorer(shape,TopAbs_SOLID);rods=[]
    while explorer.More():
        b=Bnd_Box();BRepBndLib.Add_s(explorer.Current(),b)
        lo=b.CornerMin();hi=b.CornerMax()
        xyz=[lo.X(),lo.Y(),lo.Z(),hi.X(),hi.Y(),hi.Z()]
        if xyz[4]-xyz[1]>300:rods.append(xyz)
        explorer.Next()
    rods.sort(key=lambda b:b[0]);assert len(rods)==2
    outer=rods[1][3]-rods[0][0];inner=rods[1][0]-rods[0][3]
    widths=[b[3]-b[0] for b in rods]
    assert abs(outer-51)<1e-5 and abs(inner-39)<1e-5
    return dict(source=str(path),sha256=digest(path),outer_width_mm=round(outer,5),
                inner_clear_width_mm=round(inner,5),rail_widths_mm=[round(v,5) for v in widths],
                actual_full_length_mm=round(rods[0][4]-rods[0][1],5),rail_bounds_mm=rods,
                source_drawing='SO01373.10-Probe-R01.pdf, A00424 R01, section X2-X2',
                scope='Existing simplified rod model; width only, cropped length and no crossbars in the comparison.')


def native_outline(path):
    with r.olefile.OleFileIO(path) as o:board=r.props(o.openstream('Board6/Data').read())[0]
    idx=sorted(int(k[2:]) for k in board if re.fullmatch('VX[0-9]+',k))
    assert all(board.get('KIND'+str(i))=='0' for i in idx),'Unexpected arc in native outline'
    vertices=np.array([[r.mm(board['VX'+str(i)]),r.mm(board['VY'+str(i)])] for i in idx])
    lo=vertices.min(axis=0);hi=vertices.max(axis=0)
    return dict(source=str(path),sha256=digest(path),raw_vertices_mm=vertices.tolist(),
                normalized_vertices_mm=(vertices-lo).tolist(),width_mm=float(hi[0]-lo[0]),
                length_mm=float(hi[1]-lo[1]),outline_area_mm2=Polygon(vertices).area)


def gerber_outline(path):
    with zipfile.ZipFile(path) as z:raw=z.read('Sample_Holder.GM')
    txt=raw.decode('ascii');assert '%FSLAX44Y44*%' in txt and '%MOMM*%' in txt
    x=y=None;pts=[]
    for line in txt.splitlines():
        if not re.match('[XY]',line):continue
        xv=re.search(r'X(-?\d+)',line);yv=re.search(r'Y(-?\d+)',line)
        if xv:x=int(xv.group(1))/10000
        if yv:y=int(yv.group(1))/10000
        if x is not None and y is not None:pts.append([x,y])
    ar=np.array(pts);wh=ar.max(axis=0)-ar.min(axis=0)
    return dict(archive=str(path),archive_sha256=digest(path),member='Sample_Holder.GM',
                width_mm=float(wh[0]),length_mm=float(wh[1]),
                note='Routed outline centreline; 0.0254 mm drawing aperture is not added to board dimensions.')


def dimension(ax,a,b,label,offset=(0,0),color='#4c6068'):
    p=np.array(a)+offset;q=np.array(b)+offset
    ax.annotate('',xy=q,xytext=p,arrowprops=dict(arrowstyle='<->',lw=1,color=color))
    m=(p+q)/2
    ax.text(m[0]-.7 if p[0]==q[0] else m[0],m[1] if p[0]==q[0] else m[1]+1.3,label,
            rotation=90 if p[0]==q[0] else 0,ha='right' if p[0]==q[0] else 'center',
            va='center' if p[0]==q[0] else 'bottom',fontsize=10,color=color)


def main():
    src=REF/'Sample_Holder.PcbDoc'
    cur=ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
    archive=REF/'Sample_Holder_gerbers_new_2025.08.21.zip'
    before={str(p):digest(p) for p in (src,cur,archive)}
    ref=native_outline(src);saved=native_outline(cur);gerber=gerber_outline(archive)
    rod=rod_dimensions()
    assert abs(ref['width_mm']-gerber['width_mm'])<.00001
    assert abs(ref['length_mm']-gerber['length_mm'])<.00001
    plan=dict(width_mm=19.5,length_mm=77.5,outline_area_mm2=19.5*77.5,
              normalized_vertices_mm=[[0,0],[19.5,0],[19.5,77.5],[0,77.5],[0,0]],
              status='Proposal only; not saved to native PCB')
    result=dict(reference=ref,reference_gerber=gerber,saved_native=saved,latest_plan=plan,henning_rod=rod,
        centred_board_to_inner_rail_gap_each_side_mm=dict(
            reference=(rod['inner_clear_width_mm']-ref['width_mm'])/2,
            saved_native=(rod['inner_clear_width_mm']-saved['width_mm'])/2,
            latest_plan=(rod['inner_clear_width_mm']-plan['width_mm'])/2),
        versus_latest_plan=dict(width_delta_mm=ref['width_mm']-plan['width_mm'],
             length_delta_mm=ref['length_mm']-plan['length_mm'],
             width_ratio=ref['width_mm']/plan['width_mm'],length_ratio=ref['length_mm']/plan['length_mm'],
             outline_area_ratio=ref['outline_area_mm2']/plan['outline_area_mm2']),
        source_files_unchanged=True,scope='Outer PCB dimensions only; centre overlay is not mechanical mounting alignment.')
    fig=plt.figure(figsize=(12,10),dpi=200)
    gs=fig.add_gridspec(1,2,width_ratios=(1.65,1.2),left=.055,right=.97,top=.86,bottom=.23,wspace=.15)
    ax=fig.add_subplot(gs[0]);over=fig.add_subplot(gs[1])
    designs=[(ref,0,'Reference Sample_Holder','#ad7043'),
             (saved,47,'Saved 16-RF PCB','#668999'),(plan,80,'Latest 16-RF plan','#208974')]
    for dat,x,label,col in designs:
        ar=np.array(dat['normalized_vertices_mm'])+[x,0]
        ax.add_patch(Patch(ar,fc=col+'24',ec=col,lw=1.7))
        ax.text(x+dat['width_mm']/2,dat['length_mm']/2,
                f"{dat['width_mm']:.1f}\n x\n{dat['length_mm']:.1f}\nmm",ha='center',va='center',fontsize=13,color=col)
        ax.text(x+dat['width_mm']/2,-5,label.replace(' ','\n',1),ha='center',va='top',fontsize=10,color=col)
        dimension(ax,[x,dat['length_mm']+2],[x+dat['width_mm'],dat['length_mm']+2],f"{dat['width_mm']:.1f} mm")
    dimension(ax,[-3,0],[-3,ref['length_mm']],f"{ref['length_mm']:.1f} mm")
    ax.plot([-6,104],[0,0],color='#aab9bd',lw=.7,ls=':')
    ax.set(xlim=(-8,105),ylim=(-15,116),aspect='equal');ax.axis('off')
    ax.set_title('Equal scale / lower edges aligned',fontsize=13,pad=12)
    outer=rod['outer_width_mm']/2;inner=rod['inner_clear_width_mm']/2
    for xa,xb in ((-outer,-inner),(inner,outer)):
        over.add_patch(Rectangle((xa,-54),xb-xa,108,fc='#b78d6e',ec='#896349',lw=1.0,alpha=.65))
        for y in (-50,50):
            over.plot([xa-.4,xb+.4],[y-1,y+1],color='white',lw=2.8,zorder=5)
            over.plot([xa-.4,xb+.4],[y-1,y+1],color='#896349',lw=.7,zorder=6)
    for dat,col,label,ls in ((ref,'#ad7043','Reference PCB','-'),(plan,'#208974','Latest plan','-'),(saved,'#668999','Saved native','--')):
        w,h=dat['width_mm'],dat['length_mm']
        over.add_patch(Rectangle((-w/2,-h/2),w,h,fc='none',ec=col,lw=1.8,ls=ls,label=label))
    dimension(over,[-outer,66],[outer,66],f"Rod outer width {2*outer:.0f} mm",color='#795037')
    dimension(over,[-inner,58],[inner,58],f"Inner clear gap {2*inner:.0f} mm",color='#795037')
    for xa,xb in ((-inner,-ref['width_mm']/2),(ref['width_mm']/2,inner)):
        over.annotate('',xy=(xa,0),xytext=(xb,0),arrowprops=dict(arrowstyle='<->',color='#a33d37',lw=1))
    over.text(0,0,'Reference PCB\nside clearance\n3.20 mm each',ha='center',va='center',fontsize=8.5,color='#a33d37',
              bbox=dict(fc='white',ec='none',alpha=.93,pad=2))
    over.text(0,-57.5,'Each rail: 6 mm | Rod length clipped',ha='center',va='center',fontsize=8.5,color='#795037')
    over.set(xlim=(-31,31),ylim=(-74,74),aspect='equal');over.axis('off')
    over.legend(loc='lower center',bbox_to_anchor=(.5,0),fontsize=9,frameon=False)
    over.set_title('PCB widths inside the Henning rod rails',fontsize=12,pad=12)
    fig.suptitle('PCB size comparison with Henning rod width',fontsize=19,y=.975)
    fig.text(.5,.93,'Reference: Carrier_12MW_72DC / PCB / Sample_Holder',ha='center',fontsize=11)
    fig.text(.5,.902,'Reference native outline agrees with the 2025-08-21 Gerber outline.',ha='center',fontsize=10,color='#526771')
    fig.text(.5,.165,'Henning rod: 51 mm outer width / 39 mm inner clear width / two 6 mm rails',ha='center',fontsize=12,weight='bold',color='#795037')
    fig.text(.5,.125,'Centred PCB-to-rail clearance on each side: reference 3.20 mm | current PCB / plan 9.75 mm',ha='center',fontsize=11)
    fig.text(.5,.083,'Reference PCB: 32.6 x 107.1 mm | Saved 16-RF: 19.5 x 67.9 mm | Latest plan: 19.5 x 77.5 mm',ha='center',fontsize=10)
    fig.text(.5,.052,'Rod source: existing Probe_H_Frame STEP, based on drawing SO01373.10-Probe-R01 / A00424 R01.',ha='center',fontsize=9,color='#526771')
    fig.text(.5,.025,'Width comparison only; crossbars, screws and copper carriers are excluded. All source design files remain unchanged.',ha='center',fontsize=9,color='#765443')
    fig.savefig(OUT/'Sample_Holder_Size_Comparison_With_Rod.png');plt.close(fig)
    assert before=={str(p):digest(p) for p in (src,cur,archive)}
    assert digest(Path(rod['source']))==rod['sha256']
    (OUT/'size_comparison_with_rod.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('reference','saved_native','latest_plan')},indent=2))


if __name__=='__main__':main()
