"""Picture-only outline/mount/SMP movement concept; preserve all native designs."""
from pathlib import Path
from copy import deepcopy
from itertools import combinations
import json
import math
import hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon as Patch
from shapely.geometry import Point, box
from latest_connection_plan import ROOT, HERE, SOURCES, load, pg

OUT=ROOT/'QSTL_QD4_2SET_38PAD/Outline_Mount_Concept_20261014'
OUT.mkdir(exist_ok=True)
GREEN='#178f77';GOLD='#dc9b2a';PURPLE='#9466c2';RED='#b85d38'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    old,padrows=load();new=deepcopy(old)
    for r in new:
        position=r['position'];x,y=r['start']
        if position.startswith('P1'):
            x=2.75 if position.endswith('L') else 16.75;y=64.45
        elif position.startswith(('P5','P6','P7')):
            y+=1.70
        elif position.startswith('P8'):
            x=2.75 if position.endswith('L') else 16.75
        r['start']=[x,y]
    s=json.loads(SOURCES['snapshot'].read_text())
    mounts=[p for p in s['pads'] if not p['component']]
    changed=deepcopy(mounts)
    movements=[]
    for a,b in zip(mounts,changed):
        if abs(a['hole']-2.1)<.01 and a['y']>60:
            b['y']=70.0;b['concept_group']='upper_M2'
        elif abs(a['hole']-4)<.01:
            b['y']=a['y']-2;b['concept_group']='large_lower_mount'
        elif abs(a['hole']-2.1)<.01:
            b['y']=a['y']-2;b['concept_group']='dependent_lower_M2'
        else:b['concept_group']='retained_M1'
        if a['y']!=b['y']:
            movements.append(dict(group=b['concept_group'],old_xy=[a['x'],a['y']],
                proposed_xy=[b['x'],b['y']],delta_y_mm=b['y']-a['y'],
                retained_hole_mm=a['hole'],retained_land_mm=a['size_x']))
    return old,new,padrows,mounts,changed,movements,s


def footprint(ax,r,template,sourcecentre,ghost=False):
    x,y=r['start']
    if ghost:
        ax.add_patch(Circle((x,y),2.75,fc='none',ec='#9babae',lw=.7,ls='--',alpha=.6))
        return
    ax.add_patch(Rectangle((x-2.75,y-2.75),5.5,5.5,fc='none',ec='#577d82',lw=.45,ls=':',alpha=.7))
    ax.add_patch(Circle((x,y),2.75,fc='#dce6e7',ec='#7b989d',lw=.7,alpha=.65))
    for p in template:
        cx=p['x']+x-sourcecentre['x'];cy=p['y']+y-sourcecentre['y']
        ax.add_patch(Circle((cx,cy),p['size_x']/2,fc='#c7a960' if p['number']=='1' else '#65848a',ec='none'))
        ax.add_patch(Circle((cx,cy),p['hole']/2,fc='#edf3f2',ec='none'))
    ax.text(x,y+2.06,r['smp'],ha='center',va='center',fontsize=7,color='#173c47',fontweight='bold',clip_on=True)
    ax.text(x,y-2.10,f"QD {r['qd_pad']}",ha='center',va='center',fontsize=6.8,color='#456369',clip_on=True)


def mount(ax,p,ghost=False):
    if ghost:
        ax.add_patch(Circle((p['x'],p['y']),p['size_x']/2,fc='none',ec='#9d9d9d',lw=.7,ls='--'))
        return
    group=p.get('concept_group','')
    col=PURPLE if group=='dependent_lower_M2' else GOLD if abs(p['hole']-2.1)<.01 else RED if abs(p['hole']-4)<.01 else '#6a868c'
    ax.add_patch(Circle((p['x'],p['y']),p['size_x']/2,fc=col,ec=col,lw=.6,alpha=.6))
    ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,fc='white',ec=col,lw=1))
    if abs(p['hole']-2.1)<.01 or abs(p['hole']-4)<.01:
        ax.plot([p['x']-.35,p['x']+.35],[p['y'],p['y']],color=col,lw=.7)
        ax.plot([p['x'],p['x']],[p['y']-.35,p['y']+.35],color=col,lw=.7)


def arrow(ax,a,b,color=GREEN):
    ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='-|>',lw=1.35,color=color,shrinkA=1,shrinkB=1),zorder=15)


def draw(ax,rows,padrows,mounts,s,proposed=False,old=None,oldmounts=None,ylim=(-1,75),show_moves=False,height=None,qd_center=(9.75,42.5)):
    if height is None:height=72.5 if proposed else 67.9
    ax.set_facecolor('white')
    ax.add_patch(Rectangle((0,0),19.5,height,facecolor='#ecf3f2',edgecolor='#294f57',lw=1.2))
    if proposed:
        ax.add_patch(Rectangle((0,67.9),19.5,height-67.9,fc='#ccefe2',ec='none'))
        ax.plot([0,19.5],[67.9,67.9],color='#8faaaa',ls='--',lw=.9)
        ax.plot([0,19.5],[68.04,68.04],color=RED,ls=':',lw=.8)
        for y,h in ((19.5,18.5),(48.5,18.7)):
            ax.add_patch(Rectangle((5.5,y),8.5,h,fc='#addecf',ec='none',alpha=.3))
    template=[p for p in s['pads'] if p['component']=='SMP35']
    sc=next(p for p in template if p['number']=='1')
    if show_moves:
        for a,b in zip(old,rows):
            if a['start']!=b['start']:footprint(ax,a,template,sc,True)
        for a,b in zip(oldmounts,mounts):
            if a['y']!=b['y']:mount(ax,a,True)
    for r in rows:footprint(ax,r,template,sc)
    for p in mounts:mount(ax,p)
    for p in s['pads']:
        if p['component']=='J1':
            ax.add_patch(Patch(list(pg(p).exterior.coords),fc='#94b1b1',ec='none'))
    ax.text(9.75,4.8,'Existing ZIF',ha='center',va='center',fontsize=7,color='#45636a',clip_on=True)
    for pr in padrows:
        ax.add_patch(Patch(list(pg(pr['after']).exterior.coords),fc='#bca464',ec='#7c704c',lw=.25))
    qx,qy=qd_center
    ax.add_patch(Rectangle((qx-2.15,qy-2.65),4.3,5.3,fc='#16323d',ec='#0b232d',lw=.7))
    ax.text(qx,qy,'QD',ha='center',va='center',color='white',fontsize=10,clip_on=True)
    if show_moves:
        for a,b in zip(old,rows):
            if a['start']!=b['start']:arrow(ax,a['start'],b['start'])
        for a,b in zip(oldmounts,mounts):
            if a['y']!=b['y']:
                col=PURPLE if b['concept_group']=='dependent_lower_M2' else GOLD if b['concept_group']=='upper_M2' else RED
                arrow(ax,[a['x'],a['y']],[b['x'],b['y']],col)
    ax.set(xlim=(-.6,20.1),ylim=ylim,aspect='equal',xlabel='X (mm)',ylabel='Y (mm)')
    ax.tick_params(labelsize=8)


def annotate_pair(ax,y,text,color):
    ax.text(9.75,y,text,ha='center',va='center',fontsize=8,color=color,
            bbox=dict(facecolor='white',edgecolor='none',alpha=.9,pad=1))


def check(new,mounts,s):
    bodies=[(r['smp'],box(r['start'][0]-2.75,r['start'][1]-2.75,
                          r['start'][0]+2.75,r['start'][1]+2.75)) for r in new]
    minbody=min((a.distance(b),an,bn) for (an,a),(bn,b) in combinations(bodies,2))
    bm=min((b.distance(pg(p)),name,p['concept_group']) for name,b in bodies for p in mounts)
    mm=min((pg(a).distance(pg(b)),a['concept_group'],b['concept_group']) for a,b in combinations(mounts,2))
    board=box(0,0,19.5,72.5)
    holesinside=all(board.covers(Point(p['x'],p['y']).buffer(p['hole']/2)) for p in mounts)
    lowm=[p for p in mounts if p['concept_group']=='dependent_lower_M2']
    zif=[p for p in s['pads'] if p['component']=='J1']
    zgap=min(pg(a).distance(pg(b)) for a in lowm for b in zif)
    return dict(SMP_count=len(new),minimum_SMP_bounding_box_gap_mm=minbody,
        minimum_SMP_box_to_mount_land_gap_mm=bm,minimum_mount_land_gap_mm=mm,
        all_mount_drills_inside_trial_outline=holesinside,minimum_lower_M2_land_to_ZIF_pad_gap_mm=zgap,
        central_SMP_body_projection_corridor_mm=8.5,
        upper_extension_beyond_existing_copper_lip_mm=72.5-68.03999922,
        scope='Nominal 2D envelope checks only; no screw-head, plug, tolerance, carrier, R/C or routing fit certification.')


def main():
    protect=[ROOT/'QSTL_QD4_2SET_38PAD'/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc',
        'QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib','pin_mapping.csv','full_copper_candidate.json')]
    protect += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protect}
    old,new,pads,om,nm,moves,s=build();audit=check(new,nm,s)
    assert audit['SMP_count']==16 and audit['minimum_SMP_bounding_box_gap_mm'][0]>.249
    assert audit['minimum_SMP_box_to_mount_land_gap_mm'][0]>0 and audit['minimum_mount_land_gap_mm'][0]>0
    assert audit['all_mount_drills_inside_trial_outline']
    fig=plt.figure(figsize=(14,16),dpi=190)
    gs=fig.add_gridspec(2,3,width_ratios=(1,1,1.04),height_ratios=(.8,1.2),left=.055,right=.97,
        bottom=.16,top=.92,wspace=.30,hspace=.40)
    a=fig.add_subplot(gs[:,0]);b=fig.add_subplot(gs[:,1]);c=fig.add_subplot(gs[0,2]);d=fig.add_subplot(gs[1,2])
    draw(a,old,pads,om,s);a.set_title('Previous latest relocation\n19.50 x 67.90 mm',fontsize=12)
    draw(b,new,pads,nm,s,True,old,om,show_moves=True);b.set_title('Rough movement plan\n19.50 x 72.50 mm (trial)',fontsize=12)
    draw(c,new,pads,nm,s,True,old,om,(56.0,74.2),True);c.set_title('TOP: extend board; raise M2; move SMPs outward',fontsize=9.5)
    annotate_pair(c,72.95,'PCB top: 67.90 -> 72.50',GREEN)
    annotate_pair(c,70,'M2 centres: Y = 70.00',GOLD)
    annotate_pair(c,68.08,'Existing copper end lip: Y = 68.04',RED)
    annotate_pair(c,61.45,'Top SMP pair -> side columns\nY: 62.75 -> 64.45',GREEN)
    draw(d,new,pads,nm,s,True,old,om,(8.5,42),True);d.set_title('BOTTOM: move mounts down; open the centre',fontsize=10)
    annotate_pair(d,35.9,'Lower three SMP rows: +1.70 mm',GREEN)
    annotate_pair(d,24.6,'End SMP pair moves sideways\nY = 22.25 retained',GREEN)
    annotate_pair(d,16.09,'M2.5 locations: -2.00 mm\nY = 16.09',RED)
    annotate_pair(d,10.0,'Linked proposal: lower M2 also -2.00 mm',PURPLE)
    b.annotate('',xy=(5.5,55.75),xytext=(14,55.75),arrowprops=dict(arrowstyle='<->',color=GREEN,lw=1.2))
    annotate_pair(b,56.6,'8.50 mm between SMP envelopes',GREEN)
    fig.suptitle('PCB extension + mounting-hole and SMP movement concept',fontsize=18,y=.98)
    fig.text(.5,.95,'Arrows: requested movement in green/gold/brown; additional linked lower-M2 movement in purple',ha='center',fontsize=10)
    fig.text(.5,.112,'Same board width, QD position and 16 circuit identities. Green strips show the corridor between SMP body projections only.',ha='center',fontsize=10)
    fig.text(.5,.087,'Upper M2: 65.34 -> 70.00 | Large lower mounts: 18.09 -> 16.09 | Linked lower M2: 13.19 -> 11.19 mm',ha='center',fontsize=10)
    fig.text(.5,.063,'Existing hole sizes retained in this sketch: M2 positions dia. 2.10 mm; user-labelled M2.5 locations have dia. 4.00 mm openings.',ha='center',fontsize=9.5)
    fig.text(.5,.039,'Copper carrier recess/end lip and corresponding mounting holes require revision. R0603/C1206, RF routing and hardware fit remain unverified.',ha='center',fontsize=9.5,color=RED)
    fig.text(.5,.017,'PICTURE-ONLY CONCEPT: dimensions are trial values; native PCB, schematic and reference CAD are unchanged.',ha='center',fontsize=10,color='#405d66')
    fig.savefig(OUT/'PCB_Extension_Mount_SMP_Movement_Plan.png');plt.close(fig)
    fig,ax=plt.subplots(figsize=(7,15),dpi=200)
    draw(ax,new,pads,nm,s,True,old,om,show_moves=True)
    ax.set_title('Proposed side-column layout | 19.50 x 72.50 mm',fontsize=13)
    fig.text(.5,.041,'Trial concept only. Purple arrows add a linked move of the lower M2 pair.\n'
        'Copper carrier must change with the outline and mounting axes.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.07,1,.98));fig.savefig(OUT/'Proposed_Side_Columns_Overview.png');plt.close(fig)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protect}
    report=dict(status='PICTURE_ONLY_CONCEPT_NOT_APPLIED',old_size_mm=[19.5,67.9],proposed_size_mm=[19.5,72.5],
        original=old,proposed=new,mount_movements=moves,nominal_checks=audit,
        preserved_source_hashes=hashes,source_designs_unchanged=True,
        linked_extra_move='Lower M2 row is additionally proposed to move down 2 mm; not an approved native change.',
        limitations=['Trial dimensions and two-dimensional envelopes only.',
          'Existing copper end lip and mounting axes are incompatible with the proposed outline/hole movement until revised.',
          'Do not interpret the 8.5 mm SMP-body corridor as available R/C or RF routing capacity.',
          'Screw heads, mating plugs, exact connector solid intersections, R0603/C1206 and all routing remain pending.',
          'The previous RF connection guides are not rerouted on this new placement; circuit identities are retained.'])
    (OUT/'concept_geometry.json').write_text(json.dumps(report,indent=2)+'\n')
    md=['# PCB extension, mounting and SMP concept','',
       'This is an offline picture-only concept responding to the requested outline/mounting/SMP movement. It does not modify any native PCB, schematic, library or reference CAD.','',
       '## Trial movements','',
       '- PCB width stays 19.50 mm; positive-Y end moves from 67.90 to 72.50 mm.',
       '- Upper M2 centres move from Y=65.34 to 70.00 mm; their X coordinates and 2.10 mm drills stay fixed.',
       '- Top inward SMP pair moves outward to X=2.75/16.75, Y=64.45 mm. This also raises it 1.70 mm so the next side row retains 5.75 mm pitch.',
       '- Three lower side rows move up 1.70 mm to Y=28.00, 33.75 and 39.50 mm. The bottom inward pair moves outward to X=2.75/16.75 at unchanged Y=22.25 mm.',
       '- The two large lower openings, called M2.5 locations by the user, move from Y=18.09 to 16.09 mm. Retain their actual 4.00 mm openings and 5.00 mm lands for this sketch.',
       '- Additional dependent proposal, explicitly purple in the image: move the lower M2 pair down 2.00 mm, Y=13.19 to 11.19 mm, preserving its spacing from the large mounting openings.',
       '- All 16 SMP/QD circuit identities, QD midpoint geometry, board width, lower M1 locations and ZIF geometry are retained. No new RF routing is claimed.','',
       '## Geometric limits','',
       f"Nominal 5.5 mm SMP bounding boxes have {audit['minimum_SMP_bounding_box_gap_mm'][0]:.3f} mm minimum row gap. The space between the side-column body projections is 8.50 mm, not a verified component/routing corridor.",
       '',
       'The existing copper end lip begins at Y=68.039999 mm. The proposed PCB extends 4.460001 mm past it. Its recess/end lip and the moved mounting axes therefore need a corresponding copper-carrier revision. Existing unchanged copper parts cannot be described as fitting this proposal.',
       '',
       'Nominal hole/land and connector-envelope checks are recorded in concept_geometry.json. They are not fastener-head, mating-plug, tolerance or solid-assembly validation. R0603/C1206 placement, RF/DC routing, shielding and native DRC are not performed.','',
       '[Movement comparison](PCB_Extension_Mount_SMP_Movement_Plan.png) | [Large proposed view](Proposed_Side_Columns_Overview.png)','']
    (OUT/'README.md').write_text('\n'.join(md))
    print(json.dumps(dict(output=str(OUT),checks=audit,native_unchanged=True),indent=2))


if __name__=='__main__':main()
