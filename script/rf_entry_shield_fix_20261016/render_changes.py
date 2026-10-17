"""Compare actual before/after saved copper, rather than proposal overlays."""
from pathlib import Path
import sys,json,hashlib,importlib.util
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Polygon
from shapely.geometry import Point,box
from shapely.ops import unary_union,nearest_points
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'RF_Entry_Correction_20261016';OUT.mkdir(exist_ok=True)
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011')]
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/'QSTL_QD4_2SET_38PAD.PcbDoc'
before=read_snapshot(H/'baseline'/pcb.name,sch);after=read_snapshot(pcb,sch)
bg='#10252e';gold='#e9c064';muted='#527983';cyan='#62dce7';orange='#ffb05c'
windows=[(4.1,8,39.5,45.1),(12.1,16.2,42.8,47.4),(10.6,19.8,21.4,27.5)]
zones=[box(4.8,39.8,7.5,42),box(13.05,43.1,15.1,45.3)]
netpairs=[('MW13','MW15'),('MW30','MW28')]
metrics=[]
def draw(ax,snapshot,win,title,col):
    pads,regions,tracks,vias,board=snapshot;ax.set_facecolor(bg)
    for t in tracks:
        if t['layer']==32 and t['net']:
            geo=t['geometry'].buffer(t['width']/2,quad_segs=12)
            parts=list(geo.geoms) if hasattr(geo,'geoms') else [geo]
            for z in parts:ax.add_patch(Polygon(z.exterior.coords,fc=cyan if t['net'].startswith('MW') else orange,ec='none',zorder=4))
    for d in pads:
        if d['layer'] not in (32,74):continue
        ax.add_patch(Polygon(d['geometry'].exterior.coords,fc=gold if d['net']!='GND' else muted,ec='none',zorder=5))
        if d['hole']:ax.add_patch(Circle((d['x'],d['y']),d['hole']/2,fc=bg,zorder=6))
        if d['ref'] and not d['ref'].startswith('SMP') and box(win[0],win[2],win[1],win[3]).covers(Point(d['x'],d['y'])):
            label=d['pin'] if d['ref']=='Q1' else d['ref']+'.'+d['pin']
            ax.text(d['x'],d['y'],label,color=bg,ha='center',va='center',fontsize=7,zorder=8)
    for v in vias:
        if v['net']=='GND':
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,fc=muted,zorder=6));ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,fc=bg,zorder=7))
    subtitle=''
    if col<2:
        lines=[unary_union([t['geometry'] for t in tracks if t['net']==n and t['layer']==32]) for n in netpairs[col]]
        a,b=lines;za,zb=a.intersection(zones[col]),b.intersection(zones[col]);pair=nearest_points(za,b) if za.distance(b)<zb.distance(a) else nearest_points(a,zb)
        gap=pair[0].distance(pair[1])-.11;metrics.append(dict(view=title,channels=netpairs[col],edge_gap_mm=gap))
        xy=[z.coords[0] for z in pair];ax.plot(*zip(*xy),color='#ff8296',lw=1.4,zorder=10)
        mid=pair[0].interpolate(0) if False else ((xy[0][0]+xy[1][0])/2,(xy[0][1]+xy[1][1])/2)
        ax.annotate(f'{gap:.3f} mm',mid,xytext=(0,18),textcoords='offset points',ha='center',color='white',fontsize=9,zorder=12,bbox=dict(fc=bg,ec='none',pad=2))
        subtitle=' / '.join(netpairs[col])
    else:subtitle='C13 to SMP13 | two shield rows join the ring'
    ax.set(xlim=win[:2],ylim=win[2:]);ax.set_aspect('equal');ax.set_title(title+'\n'+subtitle,fontsize=11);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.1)
fig,axes=plt.subplots(2,3,figsize=(16,12),layout='constrained')
for row,(label,snap) in enumerate([('Before',before),('Saved revision',after)]):
    for col,win in enumerate(windows):draw(axes[row,col],snap,win,label,col)
digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
fig.suptitle('RF spacing and continuous SMP-entry shielding',fontsize=17)
fig.supxlabel('Read-only native copper render | W = 0.11 mm | L5-L6 via land / hole = 0.25 / 0.10 mm | '+digest[:16],fontsize=9)
fig.savefig(OUT/'RF_Before_After.png',dpi=200);plt.close(fig)
(H/'saved_local_metrics.json').write_text(json.dumps(metrics,indent=2))
fig,axes=plt.subplots(4,4,figsize=(16,16),layout='constrained')
plan=json.loads((H/'candidate.json').read_text())
entries=json.loads((H/'entry_routes.json').read_text())['groups']
for ax,g in zip(axes.flat,entries):
    name=g['row']['smp'];cx,cy=g['row']['start'];ax.set_facecolor(bg)
    for d in after[0]:
        if d['layer'] not in (32,74) or d['geometry'].distance(Point(cx,cy))>5:continue
        ax.add_patch(Polygon(d['geometry'].exterior.coords,fc=gold if d['net']!='GND' else muted))
        if d['hole']:ax.add_patch(Circle((d['x'],d['y']),d['hole']/2,fc=bg))
    for t in after[2]:
        if t['layer']==32 and t['net']=='S'+name[3:]:
            z=t['geometry'].buffer(t['width']/2,quad_segs=12);ax.add_patch(Polygon(z.exterior.coords,fc=orange,ec='none',zorder=4))
    for v in after[3]:
        if v['net']=='GND' and Point(cx,cy).distance(Point(v['x'],v['y']))<5:
            ax.add_patch(Circle((v['x'],v['y']),.125,fc='#58a18a'));ax.add_patch(Circle((v['x'],v['y']),.05,fc=bg))
    ax.set(xlim=(cx-3.6,cx+3.6),ylim=(cy-3.6,cy+3.6));ax.set_aspect('equal');ax.set_title(name);ax.grid(alpha=.1)
fig.suptitle('Saved SMP entry geometry | continuous rows join all 16 rings',fontsize=17)
fig.supxlabel('Native saved-coordinate render | nominal row centres 0.41-0.42 mm | '+digest[:16],fontsize=9)
fig.savefig(OUT/'Saved_All_SMP_Entries.png',dpi=150);plt.close(fig)
# Reuse the existing saved-coordinate overview drawing with a new output folder.
code=(ROOT/'script/native_16rf_apply_20261016/render_saved.py').read_text().replace("DEST/'Native_Applied_20261016'","DEST/'RF_Entry_Correction_20261016'")
exec(compile(code,'saved_overview','exec'),{'__file__':str(H/'render_saved_overview.py'),'__name__':'__main__'})
print(json.dumps(metrics,indent=2))
