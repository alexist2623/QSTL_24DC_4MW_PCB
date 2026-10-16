"""Preview a 23 mm outline without moving any proposed design geometry."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from outline_mount_concept import draw
from central_four_rc_placement import paint_component, COLORS
from latest_connection_plan import ROOT, SOURCES

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Width23_Outline_Plan_20261015'
OUT.mkdir(exist_ok=True)
PLAN=ROOT/'QSTL_QD4_2SET_38PAD/Outline_Mount_Concept_20261014/qd28_left_entry_audit.json'
RC=ROOT/'QSTL_QD4_2SET_38PAD/Central_Four_RC_Plan_20261015/central_rc_placement_audit.json'
ROD=ROOT/'QSTL_QD4_2SET_38PAD/Sample_Holder_Size_Comparison_20261015/size_comparison_with_rod.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def line_dimension(ax,x0,x1,y,label,color='#3a606c',size=9):
    ax.annotate('',xy=(x1,y),xytext=(x0,y),arrowprops=dict(arrowstyle='<->',color=color,lw=1))
    ax.text((x0+x1)/2,y+.65,label,ha='center',va='bottom',fontsize=size,color=color)


def board(ax,data,groups,snapshot,width,zoom=False):
    x0=9.75-width/2
    added=(width-19.5)/2
    draw(ax,data['rows'],data['pads'],data['mounts'],snapshot,
         proposed=False,height=77.5,ylim=(-3,84),qd_center=tuple(data['qd_centre_mm']))
    # Change only the drawn board outline; all component/pad/hole coordinates
    # are loaded verbatim from the preceding proposal.
    first=ax.patches[0]
    assert isinstance(first,Rectangle) and abs(first.get_width()-19.5)<1e-8
    first.set_x(x0);first.set_width(width)
    first.set_edgecolor('#197d69' if width>19.5 else '#294f57')
    for r in groups:
        c=r['capacitor_component'];res=r['resistor_component'];col=COLORS[r['smp']]
        paint_component(ax,c,col);paint_component(ax,res,col)
        cp=c['pads'][1];rp=res['pads'][0]
        ax.plot([cp['x'],rp['x']],[cp['y'],rp['y']],color=col,lw=1.1,zorder=10)
    if width>19.5:
        for a,b in ((x0,0),(19.5,x0+width)):
            ax.add_patch(Rectangle((a,0),b-a,77.5,fc='#7bd5af',alpha=.55,ec='none',zorder=1.1))
        for x in (0,19.5):ax.plot([x,x],[0,77.5],color='#708c93',lw=.8,ls='--',zorder=3)
    ax.plot([9.75,9.75],[0,77.5],c='#92a4a8',ls=':',lw=.6,zorder=2)
    ax.set_xlim(min(-4.5,x0-2.5),max(24,x0+width+2.5))
    if zoom:
        ax.set_ylim(36.5,57.7)
        for a,b in ((x0,0),(19.5,x0+width)):
            line_dimension(ax,a,b,56.3,f'+{added:.2f}',size=8,color='#176e52')
        ax.set_title('Central four R/C pairs: positions unchanged',fontsize=11,pad=10)
    else:
        line_dimension(ax,x0,x0+width,80.0,f'{width:.2f} mm',size=11)
        if width>19.5:
            for x in (x0/2,(19.5+x0+width)/2):
                ax.text(x,11.0,f'+{added:.2f} mm',rotation=90,ha='center',va='center',fontsize=7.5,color='#145b47',zorder=4)
        ax.text(9.75,-1.5,'Length: 77.50 mm',ha='center',va='center',fontsize=9,color='#344c53')
        ax.set_title('Current proposal' if width==19.5 else f'{width:g} mm outline proposal',fontsize=12,pad=12)
        ax.set_xticks([0,9.75,19.5])
    ax.tick_params(labelsize=8)


def rod_width(ax,rod,width):
    outer=rod['outer_width_mm']/2;inner=rod['inner_clear_width_mm']/2
    for a,b in ((-outer,-inner),(inner,outer)):
        ax.add_patch(Rectangle((a,0),b-a,20,fc='#c4a48c',ec='#8b654a'))
    ax.add_patch(Rectangle((-width/2,0),width,20,fc='#e5f1ed',ec='#197d69',lw=1.7))
    ax.add_patch(Rectangle((-19.5/2,0),19.5,20,fc='none',ec='#708c93',ls='--',lw=.9))
    for a,b in ((-width/2,-19.5/2),(19.5/2,width/2)):
        ax.add_patch(Rectangle((a,0),b-a,20,fc='#7bd5af',ec='none',alpha=.6))
    line_dimension(ax,-outer,outer,28,'Rod outer width 51 mm',color='#795037')
    line_dimension(ax,-inner,inner,23,'Inner clear gap 39 mm',color='#795037')
    line_dimension(ax,-width/2,width/2,-5,f'PCB width {width:g} mm',color='#176e52')
    for a,b in ((-inner,-width/2),(width/2,inner)):
        ax.annotate('',xy=(b,10),xytext=(a,10),arrowprops=dict(arrowstyle='<->',lw=1,color='#3f6370'))
        ax.text((a+b)/2,12,f'{inner-width/2:.2f}',ha='center',fontsize=8,color='#3f6370')
    ax.text(0,9,'No lateral\nrearrangement',ha='center',va='center',fontsize=9,color='#27564d')
    ax.set(xlim=(-31,31),ylim=(-10,34),aspect='equal');ax.axis('off')
    ax.set_title('Width comparison with Henning rod (mm)',fontsize=11,pad=14)


def main():
    native=ROOT/'QSTL_QD4_2SET_38PAD'
    protect=[PLAN,RC,ROD]+[native/n for n in ('QSTL_QD4_2SET_38PAD.PcbDoc','QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protect}
    data=json.loads(PLAN.read_text());rc=json.loads(RC.read_text());groups=rc['groups']
    source_fingerprint=json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts'],paths=data['paths'],groups=groups),sort_keys=True)
    snapshot=json.loads(SOURCES['snapshot'].read_text())
    rod=json.loads(ROD.read_text())['henning_rod']
    assert sha(Path(rod['source']))==rod['sha256']
    fig=plt.figure(figsize=(13,13),dpi=210)
    gs=fig.add_gridspec(2,3,width_ratios=(.8,.8,1.3),height_ratios=(1,.8),
                      left=.05,right=.97,top=.88,bottom=.13,wspace=.24,hspace=.23)
    old=fig.add_subplot(gs[:,0]);new=fig.add_subplot(gs[:,1]);detail=fig.add_subplot(gs[0,2]);rail=fig.add_subplot(gs[1,2])
    board(old,data,groups,snapshot,19.5)
    board(new,data,groups,snapshot,23.0)
    board(detail,data,groups,snapshot,23.0,zoom=True)
    rod_width(rail,rod,23.0)
    fig.suptitle('23.00 mm PCB width proposal — no component rearrangement',fontsize=18,y=.975)
    fig.text(.5,.935,'19.50 -> 23.00 mm total width | Add 1.75 mm on each side | Proposed length remains 77.50 mm',ha='center',fontsize=11)
    fig.text(.5,.907,'All SMP, QD, ZIF, mounting holes and the four trial central R/C pairs retain their exact coordinates.',ha='center',fontsize=10.5)
    fig.text(.5,.090,'Green bands: added board area. Dashed side lines: the previous 19.50 mm outline.',ha='center',fontsize=10)
    fig.text(.5,.062,'Only the existing four trial R/C pairs and their local junctions are shown; no new routing or other R/C placement is implied.',ha='center',fontsize=9.5)
    fig.text(.5,.033,'PLAN ONLY: native PCB/CAD unchanged. Width clearance is not an assembly fit check; the known mounting conflicts remain.',ha='center',fontsize=9.4,color='#9b5038')
    fig.savefig(OUT/'PCB_23mm_No_Rearrangement_Plan.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,12),dpi=200)
    board(ax,data,groups,snapshot,23)
    ax.set_title('23.00 x 77.50 mm proposal\nExisting placements retained',fontsize=14,pad=14)
    fig.text(.5,.035,'Added width: 1.75 mm per side | Picture only; native PCB unchanged',ha='center',fontsize=9.5)
    fig.tight_layout(rect=(0,.065,1,.98));fig.savefig(OUT/'PCB_23mm_Enlarged.png');plt.close(fig)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protect}
    assert source_fingerprint==json.dumps(dict(rows=data['rows'],pads=data['pads'],mounts=data['mounts'],paths=data['paths'],groups=groups),sort_keys=True)
    result=dict(status='WIDTH23_OUTLINE_ONLY_NOT_APPLIED',old_proposed_width_mm=19.5,new_proposed_width_mm=23.,
                proposed_length_mm=77.5,fixed_x_centreline_mm=9.75,old_x_limits_mm=[0,19.5],new_x_limits_mm=[-1.75,21.25],
                added_each_side_mm=1.75,all_positions_and_path_samples_unchanged=True,
                retained_counts=dict(SMP=16,QD_pads=38,mounts=len(data['mounts']),trial_RC_pairs=4),
                rod_inside_width_mm=39.,centred_PCB_to_rail_clearance_each_side_mm=8.0,
                native_unchanged=True,source_hashes=hashes,
                limitations=['Unapplied outline proposal; saved native remains 19.5 x 67.9 mm.',
                    'Known mechanical mounting conflicts remain unresolved.',
                    'Other 12 R/C pairs and full routing are not added or certified by this drawing.'])
    (OUT/'width23_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_hashes'},indent=2))


if __name__=='__main__':main()
