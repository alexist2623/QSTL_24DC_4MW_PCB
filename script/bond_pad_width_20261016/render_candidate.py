"""Review the proposed width increase without claiming a saved native result."""
from pathlib import Path
import sys,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import shape,Polygon,Point
from shapely.ops import nearest_points,unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Bond_Pad_Width_20261017'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,pad_shape
plan=json.loads((H/'candidate.json').read_text());before=read_snapshot(H/'baseline'/(P.name+'.PcbDoc'),json.loads((P/'schematic_validation.json').read_text()))
old={p['pin']:p for p in before[0] if p['ref']=='Q1'};new={p['pin']:dict(p,sy=.26) for p in old.values()}
fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained');cx,cy=plan['sample_center']
for ax in axes:
    ax.set_facecolor('#142b36');ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
    for pin,p in new.items():
        g=pad_shape(p);x,y=g.exterior.xy;ax.fill(x,y,color='#efc75e');xx,yy=old[pin]['geometry'].exterior.xy;ax.plot(xx,yy,color='#76d8ff',lw=.6)
        if ax is axes[0]:ax.text(p['x'],p['y'],pin,ha='center',va='center',fontsize=6,color='#142b36')
    for v in plan['shield_vias']:
        if abs(v['x']-cx)<4 and abs(v['y']-cy)<5:
            ax.add_patch(plt.Circle((v['x'],v['y']),v['diameter']/2,color='#76948b'))
            ax.add_patch(plt.Circle((v['x'],v['y']),v['hole']/2,color='#142b36'))
    for p in before[2]:
        if p['layer']==32 and p['net'] and p['net'].startswith('MW'):
            x,y=p['geometry'].xy;ax.plot(x,y,color='#efc75e',lw=.8)
axes[0].set_xlim(cx-4.3,cx+4.3);axes[0].set_ylim(cy-4.7,cy+4.7);axes[0].set_title('All 38 pads: 0.250 to 0.260 mm')
a,b=new['4'],new['5'];ga,gb=pad_shape(a),pad_shape(b);u,v=nearest_points(ga,gb);mid=((u.x+v.x)/2,(u.y+v.y)/2)
axes[1].set_xlim(min(ga.bounds[0],gb.bounds[0])-.15,max(ga.bounds[2],gb.bounds[2])+.15);axes[1].set_ylim(min(ga.bounds[1],gb.bounds[1])-.15,max(ga.bounds[3],gb.bounds[3])+.3)
axes[1].plot([u.x,v.x],[u.y,v.y],color='#ff706b',lw=1.8)
axes[1].annotate(f'{u.distance(v):.6f} mm minimum gap',xy=mid,xytext=(mid[0],max(ga.bounds[3],gb.bounds[3])+.16),ha='center',color='#ff706b',arrowprops=dict(arrowstyle='->',color='#ff706b'))
axes[1].set_title('Limiting pair: Q1 pads 4 / 5')
fig.suptitle('Bond-pad widening candidate | native save / DRC pending',fontsize=15)
fig.supxlabel('Gold: proposed 0.260 mm pad | Cyan: previous 0.250 mm outline\nCentres, lengths, angles, end-midpoint alignment and electrical mapping retained.',fontsize=10)
fig.savefig(OUT/'Bond_Pad_Width_Candidate.png',dpi=180);plt.close(fig)
print(str(OUT/'Bond_Pad_Width_Candidate.png'))
