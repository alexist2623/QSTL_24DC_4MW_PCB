"""Render actual saved native copper and masks; never substitute plan routes."""
from pathlib import Path
import sys,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Circle,PathPatch
from matplotlib.path import Path as PlotPath
from shapely.geometry import Point,box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.affinity import rotate,translate
H=Path(__file__).resolve().parent;ROOT=H.parents[1];DEST=ROOT/'QSTL_QD4_2SET_38PAD';OUT=DEST/'Native_Applied_20261016';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
pcb=DEST/'QSTL_QD4_2SET_38PAD.PcbDoc';digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
sch=json.loads((DEST/'schematic_validation.json').read_text());pads,regions,tracks,vias,board=read_snapshot(pcb,sch)
bg='#10252e';gold='#e9c064';muted='#46626c';white='#d8e6e9'
def draw(ax,g,color,alpha=1,z=1):
    if g.is_empty:return
    if hasattr(g,'geoms'):
        for part in g.geoms:draw(ax,part,color,alpha,z)
    elif g.geom_type=='Polygon':
        g=orient(g);verts=[];codes=[]
        for ring in [g.exterior,*g.interiors]:
            v=list(ring.coords);verts.extend(v);codes.extend([PlotPath.MOVETO]+[PlotPath.LINETO]*(len(v)-2)+[PlotPath.CLOSEPOLY])
        ax.add_patch(PathPatch(PlotPath(verts,codes),facecolor=color,edgecolor='none',alpha=alpha,zorder=z))
def init(ax,title,limits=None):
    ax.set_facecolor('#f6f8f8');draw(ax,board,bg)
    ax.plot(*board.exterior.xy,color='#487b78',lw=.8)
    a,b,c,d=board.bounds;ax.set_xlim(a-1,c+1);ax.set_ylim(b-1,d+1)
    if limits:ax.set_ylim(*limits)
    ax.set_aspect('equal');ax.set_title(title,fontsize=12,pad=11);ax.set_xlabel('X (mm)');ax.tick_params(labelsize=8)
    for p in pads:
        if p['ref'] is None:
            draw(ax,p['geometry'],muted,z=5);ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,facecolor='#f6f8f8',edgecolor='none',zorder=8))
            ax.text(p['x'],p['y']+p['sy']/2+.3,p['pin'],color=white,fontsize=7,ha='center',zorder=9,clip_on=True)
    cavity=box(7.6,43.5,11.9,48.8);draw(ax,cavity,'#040c10',z=4)
    ax.text(9.75,46.15,'QD',color=white,ha='center',va='center',fontsize=7,zorder=10)
def copper(ax,ll):
    for t in tracks:
        if t['layer']==ll and t['net']:
            color=('#5dd4df' if t['net'].startswith('MW') else '#ffb45c') if ll==32 else ('#e8c761' if ll==2 else '#75c2ff')
            draw(ax,t['geometry'].buffer(t['width']/2,quad_segs=12),color,z=4)
    for v in vias:
        if v['low']<=ll<=v['high']:
            col=muted if v['net']=='GND' else gold
            ax.add_patch(Circle((v['x'],v['y']),v['diameter']/2,facecolor=col,edgecolor='none',zorder=5))
            ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,facecolor=bg,edgecolor='none',zorder=6))
    for p in pads:
        if p['layer'] in (ll,74) and p['ref']:
            draw(ax,p['geometry'],gold if p['net']!='GND' else '#607d85',z=5)
            if p['hole']:ax.add_patch(Circle((p['x'],p['y']),p['hole']/2,facecolor=bg,edgecolor='none',zorder=6))
    if ll==32:
        refs={p['ref'] for p in pads if p['ref'] and p['ref']!='Q1' and p['ref']!='J1'}
        for ref in sorted(refs):
            pp=[p for p in pads if p['ref']==ref]
            if ref.startswith('SMP'):
                sig=next(p for p in pp if p['pin']=='1');x,y=sig['x'],sig['y'];ax.add_patch(Circle((x,y),2.75,fill=False,ec='#68848d',lw=.55,zorder=3));ax.text(x,y+2.9,ref,fontsize=6,color=white,ha='center',zorder=10)
            else:
                x=sum(p['x'] for p in pp)/2;y=sum(p['y'] for p in pp)/2;rot=pp[0]['rotation']
                sx,sy=(3.5,1.8) if ref[0]=='C' else (1.6,.8)
                body=translate(rotate(box(-sx/2,-sy/2,sx/2,sy/2),rot,origin=(0,0)),x,y)
                ax.plot(*body.exterior.xy,color='#adc0c5',lw=.45,zorder=9);ax.text(x,y,ref,fontsize=5.5,color=white,ha='center',va='center',zorder=10,bbox=dict(facecolor=bg,edgecolor='none',pad=.4))

fig,axs=plt.subplots(1,3,figsize=(12,12),layout='constrained')
for ax,ll,title in zip(axs,(32,2,3),('L6 - 16 RF channels + shielding','L2 - DC-A / 19 nets','L3 - DC-B / 19 nets')):
    init(ax,title);copper(ax,ll)
axs[0].set_ylabel('Y (mm)')
fig.suptitle('Saved Altium PCB | 16 RF + 38 DC\n32.600 x 99.025 mm | L4 and L5 GND',fontsize=15)
fig.supxlabel('Native saved-coordinate render (not an Altium screenshot) | '+digest[:16],fontsize=9)
fig.savefig(OUT/'Saved_RF_DC_Layers.png',dpi=180);plt.close(fig)

fig,axs=plt.subplots(1,2,figsize=(13,12),layout='constrained')
init(axs[0],'Saved L6 RF detail',(19,74));copper(axs[0],32)
init(axs[1],'Top mask: protected vias, exposed centre',(19,74))
opening=unary_union([r['geometry'] for r in regions if r['layer']==37])
# Include normal pad apertures in addition to explicit mask-opening regions.
opening=opening.union(unary_union([p['geometry'].buffer(.05,join_style='mitre') for p in pads if p['layer'] in (1,74)]))
draw(axs[1],board,gold,z=1);draw(axs[1],board.difference(opening),'#4e8138',z=2)
draw(axs[1],box(7.6,43.5,11.9,48.8),gold,z=7)
for text in axs[1].texts:
    if text.get_text()=='QD':text.set_text('Exposed Top GND');text.set_color(bg);text.set_fontsize(6)
for p in pads:
    if p['ref'] is None:axs[1].add_patch(Circle((p['x'],p['y']),p['hole']/2,facecolor='#f6f8f8',edgecolor='none',zorder=10))
for v in vias:
    if v['low']==1 and opening.covers(Point(v['x'],v['y'])):axs[1].add_patch(Circle((v['x'],v['y']),v['hole']/2,facecolor=bg,edgecolor='none',zorder=6))
fig.suptitle('Saved RF geometry and solder mask',fontsize=16)
fig.supxlabel('Read-only native geometry | cyan: QD to C/R; orange: C to SMP | source '+digest[:16],fontsize=9)
fig.savefig(OUT/'Saved_RF_Detail_and_Top_Mask.png',dpi=170);plt.close(fig)
print(OUT)
