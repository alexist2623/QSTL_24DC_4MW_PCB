"""Render the exact saved C13 arc and compare with the preceding saved revision."""
from pathlib import Path
import sys,json,hashlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon,Rectangle
from shapely.geometry import Point,box
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
OUT=P/'RF_Entry_Correction_20261016'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/(N+'.PcbDoc')
before=read_snapshot(H/'before_c13_rounding'/pcb.name,sch);after=read_snapshot(pcb,sch)
digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
bg='#10252e';gold='#e9c064';muted='#527983';orange='#ffb05c'
win=box(10.35,20.9,19.45,29.0)
def draw(ax,snap,label,new):
    ax.set_facecolor(bg)
    # Body is only a reference; all copper and via geometry comes from saved PcbDoc.
    ax.add_patch(Rectangle((10.85,24.95),1.8,3.5,fc='#eee6bc',alpha=.12,zorder=1))
    for d in snap[0]:
        if d['layer'] not in (32,74) or d['geometry'].disjoint(win):continue
        ax.add_patch(Polygon(d['geometry'].exterior.coords,fc=gold if d['net']!='GND' else muted,ec='none',zorder=4))
        if d['hole']:ax.add_patch(Circle((d['x'],d['y']),d['hole']/2,fc=bg,zorder=5))
    for v in snap[3]:
        if v['net']=='GND' and win.covers(Point(v['x'],v['y'])):
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,fc='#64a890',zorder=5))
            ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,fc=bg,zorder=6))
    for t in snap[2]:
        if t['layer']!=32 or t['net'] not in ('S13','MW21'):continue
        geo=t['geometry'].buffer(t['width']/2,quad_segs=24)
        ax.add_patch(Polygon(geo.exterior.coords,fc=orange if t['net']=='S13' else '#62dce7',ec='none',zorder=7))
    ax.text(11.75,26.7,'C13',ha='center',va='center',color='white',fontsize=14)
    ax.text(16.75,25.65,'SMP13',ha='center',color='white',fontsize=13)
    if new:
        x,y=13.35-1.6/math.sqrt(2),24.45-1.6/math.sqrt(2)
        ax.plot([13.35,x],[24.45,y],color='white',lw=.9,ls='--')
        ax.plot(13.35,24.45,'+',color='white',ms=8)
        ax.annotate('R 1.60 mm\nSingle 90-degree circular arc',(x,y),xytext=(13.7,26.2),color='white',fontsize=11,arrowprops=dict(arrowstyle='->',color='white'),ha='left')
        ax.annotate('',(13.35,20.7),(16.75,20.7),arrowprops=dict(arrowstyle='<->',color='white'))
        ax.text(15.05,20.35,'3.40 mm straight radial entry',ha='center',color='white',fontsize=10)
    ax.set(xlim=(10.35,19.45),ylim=(20.2,29.0));ax.set_aspect('equal')
    ax.set_title(label,fontsize=15,pad=10);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.08)
fig,axes=plt.subplots(1,2,figsize=(14,7),layout='constrained')
draw(axes[0],before,'Before: short-radius turn',False)
draw(axes[1],after,'Saved: broad tangent arc',True)
fig.suptitle('C13 RF bend correction | continuous shielding into SMP13',fontsize=17)
fig.supxlabel('Actual saved PCB geometry | RF width 0.11 mm | Shield land / hole 0.25 / 0.10 mm | '+digest[:16],fontsize=10)
fig.savefig(OUT/'C13_Rounded_Bend_Before_After.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,9),layout='constrained');draw(ax,after,'C13 to SMP13 | R 1.60 mm',True)
fig.supxlabel('Actual saved PCB geometry | '+digest[:16],fontsize=10)
fig.savefig(OUT/'C13_Rounded_Bend.png',dpi=180);plt.close(fig)
print(OUT/'C13_Rounded_Bend.png')
