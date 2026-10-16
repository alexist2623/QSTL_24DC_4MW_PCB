"""Correct the movement sketch: preserve lower M2; large-hole displacement TBD."""
from copy import deepcopy
import json
import matplotlib.pyplot as plt
from outline_mount_concept import ROOT, OUT, build, draw, arrow, annotate_pair, sha, GREEN, GOLD, RED


def main():
    old,new,pads,original,_,_,snapshot=build()
    protected=[ROOT/'QSTL_QD4_2SET_38PAD'/p for p in ('QSTL_QD4_2SET_38PAD.PcbDoc',
        'QSTL_QD4_2SET_38PAD.SchDoc','QD4_2SET_38.PcbLib')]
    protected += [ROOT/'QSTL_24DC_4MW_PCB/Mechanical_Assembly'/p for p in ('Bottom_reference.step','Top_ForFridge_reference.step')]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in protected}
    mounts=deepcopy(original)
    fixed=[];tbd=[]
    for a,b in zip(original,mounts):
        if abs(a['hole']-2.1)<.01 and a['y']>60:
            b['y']=70;b['concept_group']='upper_M2'
        elif abs(a['hole']-2.1)<.01:
            b['concept_group']='fixed_lower_M2'
            fixed.append(dict(x=b['x'],y=b['y'],hole=b['hole']))
            assert all(a[k]==b[k] for k in ('x','y','hole','size_x','size_y'))
        elif abs(a['hole']-4)<.01:
            b['concept_group']='large_mount_move_TBD'
            tbd.append(dict(existing_xy=[a['x'],a['y']],direction='negative Y',distance_mm=None))
        else:
            b['concept_group']='retained_M1'
    fig=plt.figure(figsize=(11,13),dpi=180)
    gs=fig.add_gridspec(1,2,width_ratios=(1,1.1),left=.06,right=.97,top=.89,bottom=.15,wspace=.30)
    a=fig.add_subplot(gs[0]);b=fig.add_subplot(gs[1])
    for ax,limits in ((a,(-1,75)),(b,(10,42))):
        draw(ax,new,pads,mounts,snapshot,True,old,original,limits,True)
        # Only the direction is illustrated. There is no new circle or selected
        # coordinate for the large mounting holes in this correction.
        for p in mounts:
            if p['concept_group']=='large_mount_move_TBD':
                arrow(ax,[p['x'],p['y']],[p['x'],p['y']-1.25],RED)
        annotate_pair(ax,13.19,'LOWER M2: FIXED\nOriginal Y = 13.19 mm','#235c99')
        annotate_pair(ax,18.2,'M2.5: move downward\nAmount TBD',RED)
    a.set_title('Corrected movement intent\nLower M2 retained',fontsize=13)
    b.set_title('Lower end detail\nLarge circles show their existing datum',fontsize=12)
    annotate_pair(b,24.6,'SMP pair moves outward',GREEN)
    annotate_pair(b,35.7,'Lower side SMPs move upward',GREEN)
    fig.suptitle('Correction: do not move the lower M2 mounting pair',fontsize=17,y=.97)
    fig.text(.5,.93,'The extra lower-M2 shift has been removed. The 2.00 mm large-hole shift was an assistant assumption, not a user dimension.',ha='center',fontsize=9)
    fig.text(.5,.103,'Large mounting holes remain drawn at their old locations to show the datum; brown arrows indicate direction only.',ha='center',fontsize=10)
    fig.text(.5,.073,'Their final positions must clear the FIXED lower M2 and the outward SMPs. This clearance is not yet resolved.',ha='center',fontsize=10,color=RED)
    fig.text(.5,.043,'Other outline/SMP trial movements are carried over for context. Native PCB, schematic and reference CAD remain unchanged.',ha='center',fontsize=9.5)
    target=OUT/'Corrected_Lower_M2_Fixed_Plan.png'
    fig.savefig(target);plt.close(fig)
    assert hashes=={str(p.relative_to(ROOT)):sha(p) for p in protected}
    report=dict(status='CORRECTED_INTENT_SKETCH_WITH_UNRESOLVED_LARGE_MOUNT_POSITION',
        lower_M2_fixed=fixed,large_mount_direction_only=tbd,
        rejects='Extra lower M2 -2 mm movement and fixed large mounting hole -2 mm assumption.',
        unresolved='Choose large-hole positions clearing fixed lower M2 and proposed outboard SMPs; no certified fit.',
        native_sources_unchanged=True,source_hashes=hashes,image=str(target))
    (OUT/'fixed_lower_M2_correction.json').write_text(json.dumps(report,indent=2)+'\n')
    readme=OUT/'README.md';text=readme.read_text()
    marker='## Latest correction: lower M2 remains fixed'
    if marker not in text:
        text=text.replace('# PCB extension, mounting and SMP concept',
          '# PCB extension, mounting and SMP concept\n\n'+marker+'\n\n'
          'The user rejects the added lower-M2 movement. Keep both lower M2 axes at their saved coordinates, Y=13.19 mm. '
          'The assistant-selected 2 mm downward large-hole displacement is also withdrawn as a fixed dimension; its amount remains TBD. '
          'The [corrected intent sketch](Corrected_Lower_M2_Fixed_Plan.png) shows direction only and retains the large holes at their existing datum. '
          'Clearance to the fixed lower M2 and proposed outward SMPs is unresolved. Native sources are unchanged.\n\n'
          '**The earlier numeric plan below, its purple lower-M2 arrows, and its clearance results are rejected history. Do not use them as the current concept.**')
        readme.write_text(text)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
