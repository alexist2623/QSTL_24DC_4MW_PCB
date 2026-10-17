"""Render the saved whole board and complete capacitor-to-SMP paths."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon
from shapely.geometry import Point,box,LineString
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name;OUT=P/'SMP_Rounded_Entries_20261016';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/(N+'.PcbDoc');snap=read_snapshot(pcb,sch)
digest=hashlib.sha256(pcb.read_bytes()).hexdigest();routes=json.loads((H/'entry_routes.json').read_text());status={r['channel']:r for r in routes['entry_report']}
bg='#10252e';gold='#e9c064';muted='#527983';orange='#ffb05c'
def paint(ax,name,bounds):
    ax.set_facecolor(bg);win=box(*bounds)
    for d in snap[0]:
        if d['layer'] not in (32,74) or d['geometry'].disjoint(win):continue
        ax.add_patch(Polygon(d['geometry'].exterior.coords,fc=gold if d['net']!='GND' else muted,ec='none',zorder=4))
        if d['hole']:ax.add_patch(Circle((d['x'],d['y']),d['hole']/2,fc=bg,zorder=5))
        if d['ref'] is None and win.covers(Point(d['x'],d['y'])):ax.text(d['x'],d['y']+.9,d['pin'],color='white',ha='center',zorder=9,fontsize=11)
    for t in snap[2]:
        if t['net']=='S'+name[3:] and t['layer']==32:
            geo=t['geometry'].buffer(t['width']/2,quad_segs=16);ax.add_patch(Polygon(geo.exterior.coords,fc=orange,ec='none',zorder=7))
    for v in snap[3]:
        if v['net']=='GND' and win.covers(Point(v['x'],v['y'])):
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,fc='#64a890',zorder=5));ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,fc=bg,zorder=6))
    ax.set(xlim=(bounds[0],bounds[2]),ylim=(bounds[1],bounds[3]));ax.set_aspect('equal');ax.grid(alpha=.08);ax.tick_params(labelsize=7)
fig,axes=plt.subplots(4,4,figsize=(19,19),layout='constrained')
for ax,g in zip(axes.flat,routes['groups']):
    name=g['row']['smp'];a=np.array(g['capacitor']['centre_mm']);b=np.array(g['row']['start']);mid=(a+b)/2
    bounds=(mid[0]-5.1,mid[1]-5.1,mid[0]+5.1,mid[1]+5.1);paint(ax,name,bounds)
    r=status[name];label='UNCHANGED: A-hole shield obstruction' if name in routes['uncertain_entries'] else f'R {r["radius_mm"]:.2f} mm | {r["arcs"]} circular arc'+('s' if r['arcs']>1 else '')
    ax.set_title(name+' / '+g['row']['capacitor']+'\n'+label,fontsize=10,color='#ae3f38' if name in routes['uncertain_entries'] else '#183a42')
    ax.text(*a,g['row']['capacitor'],color='white',fontsize=9,ha='center',va='center',zorder=9)
fig.suptitle('Saved SMP RF approaches | 13 revised, C13 retained, SMP02/24 unchanged',fontsize=17)
fig.supxlabel('Actual saved copper | RF width 0.11 mm | All paths stay on L6 | '+digest[:16],fontsize=10)
fig.savefig(OUT/'Saved_All_SMP_Entries.png',dpi=170);plt.close(fig)
# Show the rejected broad turn explicitly, without representing it as saved copper.
fig,axes=plt.subplots(1,2,figsize=(12,7),layout='constrained')
for ax,name,mirror in zip(axes,('SMP02','SMP24'),(False,True)):
    bounds=(-6.7,37.6,4.5,48.8) if not mirror else (15.,37.6,26.2,48.8);paint(ax,name,bounds)
    angle=np.linspace(math.pi/2,math.pi,300);pts=np.c_[-1.65+1.6*np.cos(angle),42.65+1.6*np.sin(angle)]
    pts=np.vstack(([-.765,44.25],pts,[-3.25,40.1]))
    if mirror:pts[:,0]=19.5-pts[:,0]
    line=LineString(pts);ax.plot(*line.xy,c='#f77583',lw=1.5,ls='--',label='Rejected R1.6 trial (not saved)',zorder=8)
    outer=line.offset_curve(-.438 if not mirror else .438,quad_segs=32)
    ax.plot(*outer.xy,c='#c78afe',lw=1.2,ls=':',label='Required outer shield centreline',zorder=8)
    ax.set_title(name+' retained | '+('A4' if not mirror else 'A3')+' blocks broad outer shield',fontsize=12)
    ax.legend(loc='lower center',fontsize=8,facecolor='white',framealpha=.9)
fig.suptitle('Unchanged entries: continuous shield clearance could not be verified',fontsize=15)
fig.supxlabel('Solid orange = actual saved RF; dashed overlays = rejected trial | '+digest[:16],fontsize=9)
fig.savefig(OUT/'Unchanged_SMP02_SMP24.png',dpi=180);plt.close(fig)
code=(ROOT/'script/native_16rf_apply_20261016/render_saved.py').read_text().replace("DEST/'Native_Applied_20261016'","DEST/'SMP_Rounded_Entries_20261016'")
scope={'__file__':str(H/'saved_overview.py'),'__name__':'__main__'};exec(compile(code,'saved_overview','exec'),scope)
fig,ax=plt.subplots(figsize=(6.6,16),layout='constrained');scope['init'](ax,'Saved RF | rounded SMP approaches');scope['copper'](ax,32)
fig.supxlabel('32.600 x 99.025 mm | '+digest[:16],fontsize=9);fig.savefig(OUT/'Saved_RF_Whole_Board.png',dpi=190);plt.close(fig)
assert digest==hashlib.sha256(pcb.read_bytes()).hexdigest(),'PCB changed during rendering'
print(OUT)
