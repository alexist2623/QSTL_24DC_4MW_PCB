"""Render verified saved QD pad geometry before/after the alignment delta.

This script refuses to publish an image until a different native PCB has a
passing, hash-matched saved audit and snapshot. It never edits native design
files. Polygon corners come from actual saved pad dimensions and rotations.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon, Rectangle, Circle
from matplotlib.lines import Line2D

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
PROJECT=ROOT/'QSTL_QD4_2SET_38PAD'
BASE_SHA='1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def corners(p):
    assert p['shape']==2 and p['layer']==32 and p['component']=='Q1'
    theta=math.radians(p['rotation']);c,s=math.cos(theta),math.sin(theta)
    return [(p['x']+x*c-y*s,p['y']+x*s+y*c) for x,y in
            [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),
             (p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]]


def boundary_metrics(snapshot,sides,cx,cy,cw,ch):
    target={'LEFT':cx-cw/2-.2,'RIGHT':cx+cw/2+.2,'BOTTOM':cy-ch/2-.2,'TOP':cy+ch/2+.2}
    rows=[]
    for p in snapshot['pads']:
        if p['component']!='Q1':continue
        side=sides[str(p['number'])];polygon=corners(p)
        axis=0 if side in ('LEFT','RIGHT') else 1
        func=min if side in ('RIGHT','TOP') else max
        near=func(x[axis] for x in polygon)
        rows.append(dict(pin=p['number'],side=side,nearest_corner_coordinate_mm=near,
                         nominal_boundary_coordinate_mm=target[side],deviation_mm=near-target[side]))
    assert len(rows)==38
    return dict(pads=rows,maximum_absolute_boundary_deviation_mm=max(abs(p['deviation_mm']) for p in rows))


def dimension(ax,a,b,label,text_offset=(0,0),color='#566475'):
    ax.annotate('',xy=a,xytext=b,arrowprops=dict(arrowstyle='<->',lw=1,color=color,shrinkA=0,shrinkB=0))
    ax.text((a[0]+b[0])/2+text_offset[0],(a[1]+b[1])/2+text_offset[1],label,
            ha='center',va='center',fontsize=9,color=color,
            rotation=90 if abs(a[0]-b[0])<1e-9 else 0,
            bbox=dict(facecolor='white',edgecolor='none',pad=2))


def panel(ax,snapshot,title,metrics,cx,cy,cw,ch,show_dimensions=True):
    ax.set_facecolor('#fafcfd')
    x0,x1=cx-cw/2,cx+cw/2;y0,y1=cy-ch/2,cy+ch/2
    bx0,bx1=x0-.2,x1+.2;by0,by1=y0-.2,y1+.2
    ax.add_patch(Rectangle((x0,y0),cw,ch,facecolor='#e1e8ed',edgecolor='#778697',lw=1.1,zorder=1))
    ax.add_patch(Rectangle((bx0,by0),cw+.4,ch+.4,fill=False,edgecolor='#147d84',lw=1.3,ls=(0,(5,3)),zorder=4))
    pads=[p for p in snapshot['pads'] if p['component']=='Q1']
    for p in pads:
        ax.add_patch(PatchPolygon(corners(p),closed=True,facecolor='#d3a23f',edgecolor='#6d4c16',lw=.65,zorder=3))
    def in_own_pad(v):
        for p in pads:
            if p['net']!=v['net']:continue
            theta=math.radians(p['rotation']);c,s=math.cos(theta),math.sin(theta)
            dx,dy=v['x']-p['x'],v['y']-p['y']
            if abs(dx*c+dy*s)<=p['size_x']/2+1e-5 and abs(-dx*s+dy*c)<=p['size_y']/2+1e-5:
                return True
        return False
    vias=[v for v in snapshot['vias'] if (v['net'] or '').startswith('DC') and in_own_pad(v)]
    assert len(vias)==22,'Expected exactly22 direct QD endpoint vias in this close-up'
    for v in vias:
        ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,facecolor='#3865a0',edgecolor='#173750',lw=.6,alpha=.85,zorder=5))
        ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,facecolor='white',edgecolor='#173750',lw=.45,zorder=6))
    ax.plot([cx-.15,cx+.15],[cy,cy],color='#526273',lw=.9)
    ax.plot([cx,cx],[cy-.15,cy+.15],color='#526273',lw=.9)
    ax.text(cx,cy+.46,'QD cavity',ha='center',fontsize=11,color='#3f4e5d')
    ax.text(cx,cy-.44,f'{cw:.1f} × {ch:.1f} mm',ha='center',fontsize=10,color='#3f4e5d')
    ax.text(cx,cy-.82,'Sample datum (9.75, 42.50) mm',ha='center',fontsize=8,color='#526273')
    if show_dimensions:
        dimension(ax,(bx0,cy+4.45),(bx1,cy+4.45),f'{cw+.4:.1f} mm inner boundary')
        for x in (bx0,bx1):ax.plot([x,x],[cy+3.65,cy+4.62],color='#8694a2',lw=.55)
        dimension(ax,(cx-4.42,by0),(cx-4.42,by1),f'{ch+.4:.1f} mm inner boundary')
        for y in (by0,by1):ax.plot([cx-4.55,cx-3.50],[y,y],color='#8694a2',lw=.55)
        ax.annotate('0.20 mm nominal\ncavity-to-pad boundary',xy=(bx1,(y0+y1)/2+.8),
                    xytext=(cx+.13,cy+1.66),ha='center',va='center',fontsize=8.5,color='#147d84',
                    arrowprops=dict(arrowstyle='->',color='#147d84',lw=.8),
                    bbox=dict(facecolor='#fafcfd',edgecolor='none',pad=1))
    maximum=metrics['maximum_absolute_boundary_deviation_mm']
    value=f'{maximum*1000:.3f} µm' if maximum<.001 else f'{maximum:.4f} mm'
    ax.set_title(title+'\n'+f'Maximum nearest-corner deviation: {value}',fontsize=12,pad=13)
    ax.set_xlim(cx-5,cx+4.7);ax.set_ylim(cy-4.6,cy+5)
    ax.set_aspect('equal');ax.set_xlabel('Saved X (mm)',fontsize=9);ax.set_ylabel('Saved Y (mm)',fontsize=9)
    ax.tick_params(labelsize=8);ax.grid(color='#dfe5eb',lw=.5,alpha=.6,zorder=0)
    for spine in ax.spines.values():spine.set_color('#a7b4c0')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--after-snapshot',required=True,type=Path)
    ap.add_argument('--saved-audit',required=True,type=Path)
    ap.add_argument('--candidate',required=True,type=Path)
    ap.add_argument('--before-snapshot',type=Path,default=H.parent/'qd38_rotation_20261011/saved_revision_snapshot.json')
    ap.add_argument('--native',type=Path,default=PROJECT/'QSTL_QD4_2SET_38PAD.PcbDoc')
    args=ap.parse_args();before_path=args.before_snapshot.resolve();after_path=args.after_snapshot.resolve()
    native_hash=sha(args.native);before_native=H/'before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc'
    assert sha(before_native)==BASE_SHA and native_hash!=BASE_SHA,'A different saved native revision is required'
    before=json.loads(before_path.read_text());after=json.loads(after_path.read_text());audit=json.loads(args.saved_audit.read_text());plan=json.loads(args.candidate.read_text())
    assert before['source_sha256']==BASE_SHA
    assert after['source_sha256']==native_hash
    assert audit['passed'] is True and not audit.get('errors',[])
    assert audit['native_sha256']==native_hash and audit['candidate_sha256']==sha(args.candidate)
    assert set((str(p['number']) for p in before['pads'] if p['component']=='Q1'))==set(str(n) for n in range(1,39))
    assert set((str(p['number']) for p in after['pads'] if p['component']=='Q1'))==set(str(n) for n in range(1,39))
    cx,cy=plan['sample_center'];cw,ch=plan['cavity_mm']
    # The four corner pads belong to the horizontal support lines, exactly
    # as in the accepted alignment geometry; they cannot simultaneously
    # align to two orthogonal lines while retaining their bond-ray angle.
    sides={str(p['number']):(('TOP' if p['normal'][1]>0 else 'BOTTOM') if p['side']=='CORNER' else p['side']) for p in plan['pads']}
    bm=boundary_metrics(before,sides,cx,cy,cw,ch);am=boundary_metrics(after,sides,cx,cy,cw,ch)
    assert am['maximum_absolute_boundary_deviation_mm']<1e-5,'Saved common corner boundary failed'
    output=PROJECT/'review';output.mkdir(exist_ok=True)
    legend=[Line2D([0],[0],color='#d3a23f',lw=5,label='Saved bonding pad copper'),
            Line2D([0],[0],marker='o',color='none',markerfacecolor='#3865a0',markeredgecolor='#173750',label='Direct DC via land'),
            Line2D([0],[0],color='#147d84',ls='--',label='Common cavity-facing corner boundary')]
    note='Dashed lines align the nearest cavity-facing corners. Angled short pad edges remain angled.\nActual saved copper geometry; source GDS and sample datum are unchanged.'
    plt.rcParams['font.family']='DejaVu Sans'
    fig,ax=plt.subplots(figsize=(9,9));panel(ax,after,'QD pad-end alignment — saved revision',am,cx,cy,cw,ch)
    fig.legend(handles=legend,loc='lower center',bbox_to_anchor=(.5,.075),ncol=1,frameon=False,fontsize=9)
    fig.text(.5,.027,note,ha='center',va='center',fontsize=8.5,color='#526273')
    fig.subplots_adjust(left=.11,right=.96,bottom=.19,top=.92)
    target=output/'QD_pad_end_alignment.png';fig.savefig(target,dpi=190,facecolor='white');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(16,8.8))
    panel(axes[0],before,'Before — verified baseline',bm,cx,cy,cw,ch)
    panel(axes[1],after,'After — aligned saved pads',am,cx,cy,cw,ch)
    fig.legend(handles=legend,loc='lower center',bbox_to_anchor=(.5,.09),ncol=3,frameon=False,fontsize=9)
    fig.text(.5,.035,note,ha='center',va='center',fontsize=9,color='#526273')
    fig.subplots_adjust(left=.055,right=.975,bottom=.17,top=.92,wspace=.16)
    comparison=output/'QD_pad_end_alignment_before_after.png';fig.savefig(comparison,dpi=190,facecolor='white');plt.close(fig)
    assert sha(args.native)==native_hash
    manifest=dict(native_sha256=native_hash,baseline_native_sha256=BASE_SHA,candidate_sha256=sha(args.candidate),
                  saved_audit_sha256=sha(args.saved_audit),before_snapshot_sha256=sha(before_path),after_snapshot_sha256=sha(after_path),
                  before=bm,after=am,files=[dict(path=str(p),sha256=sha(p)) for p in (target,comparison)])
    (H/'saved_alignment_images_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    review_path=H/'alignment_review_images.json'
    review=dict(candidate_sha256=sha(args.candidate),native_sha256=native_hash,
                images=[dict(path=str(target),sha256=sha(target),view='closeup'),
                        dict(path=str(comparison),sha256=sha(comparison),view='before_after')])
    if review_path.exists():
        previous=json.loads(review_path.read_text())
        if previous.get('candidate_sha256')==review['candidate_sha256'] and previous.get('native_sha256')==native_hash:
            review['images'] += [x for x in previous.get('images',[]) if x.get('view') not in ('closeup','before_after')]
    review_path.write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(dict(images=[str(target),str(comparison)],before_max_deviation_mm=bm['maximum_absolute_boundary_deviation_mm'],after_max_deviation_mm=am['maximum_absolute_boundary_deviation_mm']),indent=2))


if __name__=='__main__':main()
