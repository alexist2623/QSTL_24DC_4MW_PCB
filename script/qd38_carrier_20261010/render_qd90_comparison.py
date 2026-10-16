"""Compare a 90-degree QD-footprint rotation without changing native design files."""
from pathlib import Path
import hashlib
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

H=Path(__file__).resolve().parent
ROOT=H.parents[1]
DEST=ROOT/'QSTL_QD4_2SET_38PAD'
PCB=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc'
native=json.loads((H/'through_dc_saved_native_snapshot.json').read_text())
before=hashlib.sha256(PCB.read_bytes()).hexdigest()
assert before==native['source_sha256']
center=(9.75,42.5)
rows=[(24.5,[3.75,9.75,15.75]),(30.5,[3.75,15.75]),(36.5,[3.75,15.75]),
      (42.5,[3.75,15.75]),(48.5,[3.75,15.75]),(54.5,[3.75,15.75]),(60.5,[3.75,9.75,15.75])]
fig,axes=plt.subplots(1,2,figsize=(14,7.3))
for ax,turn in zip(axes,(0,90)):
    ax.set_aspect('equal')
    ax.add_patch(Polygon(native['board_outline'],closed=True,facecolor='#e6efe8',edgecolor='#263e35'))
    for y,xs in rows:
        if not 34<y<51:continue
        for x in xs:
            color='#df8d36' if y==42.5 else '#3186a9'
            ax.add_patch(Circle((x,y),2.75,facecolor=color,edgecolor=color,alpha=.2,lw=1.2))
            for dx,dy in [(0,0),(-1.27,-1.27),(-1.27,1.27),(1.27,-1.27),(1.27,1.27)]:
                ax.add_patch(Circle((x+dx,y+dy),.5,facecolor='#c6a853',edgecolor='#726139',lw=.5))
                ax.add_patch(Circle((x+dx,y+dy),.375,facecolor='white',edgecolor='none'))
    width,height=(5.3,4.3) if turn==0 else (4.3,5.3)
    ax.add_patch(Rectangle((center[0]-width/2,center[1]-height/2),width,height,facecolor='white',edgecolor='#ae3940',lw=1.3))
    for p in native['pads']:
        if p['component']!='Q1':continue
        dx,dy=p['x']-center[0],p['y']-center[1]
        x,y=(p['x'],p['y']) if turn==0 else (center[0]-dy,center[1]+dx)
        a=math.radians(p['rotation']+turn)
        vertices=[(x+u*p['size_x']/2*math.cos(a)-v*p['size_y']/2*math.sin(a),
                   y+u*p['size_x']/2*math.sin(a)+v*p['size_y']/2*math.cos(a))
                  for u,v in [(-1,-1),(1,-1),(1,1),(-1,1)]]
        pin1=p['number']=='1'
        ax.add_patch(Polygon(vertices,facecolor='#c94e55' if pin1 else '#d4a344',edgecolor='#6c562c',lw=.4))
        if pin1:
            ax.annotate('Pad 1',xy=(x,y),xytext=(x+1.1,y+.55),fontsize=9,color='#a22b39',
                        arrowprops={'arrowstyle':'-','color':'#a22b39','lw':.8})
    ax.axhline(42.5,color='#bd565b',linestyle=':',lw=.7)
    ax.plot(center[0],center[1],'+',color='#ad343d',ms=8)
    ax.text(center[0],center[1]-.65,f'{width:.1f} × {height:.1f} mm\npocket',ha='center',va='center',fontsize=12,color='#ad343d')
    ax.set(xlim=(-.3,19.8),ylim=(34.8,50.2),xlabel='X (mm)',ylabel='Y (mm)',
           title='Current QD orientation' if turn==0 else 'QD +90° counterclockwise')
    ax.tick_params(labelsize=9)
fig.suptitle('QD rotation comparison | SMP grid unchanged: 3 / 2 / 2 / 2 (QD) / 2 / 2 / 3',fontsize=15)
fig.text(.5,.092,'QD centre fixed at (9.75, 42.5) mm. All 38 pad numbers rotate with the footprint; pocket depth stays 1.2 mm.',ha='center',fontsize=10)
fig.text(.5,.054,'Transparent circles: Top SMP bodies. Gold/white circles: through-hole lands/drills. QD pads: Bottom face.',ha='center',fontsize=10)
fig.text(.5,.018,'PLACEMENT COMPARISON ONLY — native PCB and source GDS unchanged; R/C and routing are not represented.',ha='center',fontsize=9,color='#973d3d')
fig.tight_layout(rect=(0,.135,1,.95))
out=DEST/'review/QD_90deg_SMP_seven_rows_comparison_20261011.png'
fig.savefig(out,dpi=170)
plt.close(fig)
assert hashlib.sha256(PCB.read_bytes()).hexdigest()==before
print(out)
