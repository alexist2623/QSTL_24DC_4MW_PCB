"""Prepare the measured P/A hole pattern without modifying a PCB document."""
from pathlib import Path
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'QSTL_QD4_2SET_38PAD/Reference12_Fastening_20261015/fastening_review.json'
OUT = ROOT / 'QSTL_QD4_2SET_38PAD/PA_Mounting_Pattern_20261016'


def main():
    data = json.loads(SOURCE.read_text())
    holes = []
    for prefix, key, diameter in [('P', 'pcb_mount_axes_mm', 3.2),
                                  ('A', 'additional_cad_hole_axes_mm', 2.0)]:
        for index, point in enumerate(data[key], 1):
            holes.append(dict(name=f'{prefix}{index}', source_xy_mm=point,
                              measured_diameter_mm=diameter,
                              diameter_basis='PCB PTH' if prefix == 'P' else 'CAD bore, PCB drill size pending'))
    OUT.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(8,12), dpi=190)
    for hole in holes:
        x,y = hole['source_xy_mm']
        color = '#226b99' if hole['name'].startswith('P') else '#bd552f'
        ax.add_patch(Circle((x,y),hole['measured_diameter_mm']/2,fc='white',ec=color,lw=2))
        ax.plot([x-.8,x+.8],[y,y],c=color,lw=.7)
        ax.plot([x,x],[y-.8,y+.8],c=color,lw=.7)
        ax.text(x+(2.5 if x<0 else -2.5),y,
                f"{hole['name']}\n({x:.1f}, {y:.1f})",ha='left' if x<0 else 'right',
                va='center',fontsize=9,color=color,linespacing=1.35)
    def dim(a,b,text,xy):
        ax.annotate('',xy=a,xytext=b,arrowprops=dict(arrowstyle='<->',color='#496269'))
        ax.text(*xy,text,ha='center',va='center',fontsize=10,bbox=dict(fc='white',ec='none',pad=2))
    dim((-12.8,44),(12.8,44),'25.60 mm',(0,46))
    dim((-14.3,7),(14.3,7),'28.60 mm',(0,9))
    dim((-22,-45.3),(-22,37.8),'83.10 mm',(-22,-3.75))
    dim((21,-37.8),(21,37.8),'75.60 mm',(21,0))
    ax.axvline(0,color='#9baeb2',ls=':',lw=.8)
    ax.set(xlim=(-29,29),ylim=(-51,50),aspect='equal',xlabel='Source CAD X (mm)',ylabel='Source CAD Y (mm)')
    ax.grid(alpha=.12)
    ax.set_title('P1-P4 + A1-A4: measured mounting axes',fontsize=16,pad=18)
    fig.text(.5,.075,'P: existing PCB holes, diameter 3.20 mm\nA: measured CAD bores, nominal diameter 2.00 mm; PCB clearance diameter pending',
             ha='center',fontsize=10,linespacing=1.6)
    fig.text(.5,.025,'Coordinate template only. Target PCB, translation and outline extension are not yet applied.',
             ha='center',fontsize=9,color='#98482d')
    fig.tight_layout(rect=(0,.12,1,1))
    fig.savefig(OUT/'PA_Mounting_Axes.png')
    plt.close(fig)
    result=dict(status='TARGET_CLARIFICATION_PENDING_NO_NATIVE_CHANGE',source=str(SOURCE),holes=holes,
                x_span_mm=28.6,y_span_mm=83.1,current_16rf_proposal_length_mm=77.5,
                pattern_scaling_allowed=False,target_translation_mm=None)
    (OUT/'pa_pattern.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(output=str(OUT),holes=len(holes),native_changed=False)))


if __name__ == '__main__':
    main()
