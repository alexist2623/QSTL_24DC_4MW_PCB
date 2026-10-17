"""Render before/after masks and native C/R body registration for review."""
from pathlib import Path
import sys,json,hashlib
from functools import lru_cache
from shapely.geometry import Point,Polygon,shape,box
from shapely.ops import unary_union
from shapely import wkb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MP
from matplotlib.patches import PathPatch,Patch
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Compact_Masks_20261016'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/(P.name+'.PcbDoc');digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
before=read_snapshot(H/'baseline'/pcb.name,sch);after=read_snapshot(pcb,sch)
pads,regions,tracks,vias,outline=after
cam={37:wkb.loads((H/'GTS.wkb').read_bytes()),38:wkb.loads((H/'GBS.wkb').read_bytes())}
plan=json.loads((H/'candidate.json').read_text());bodies={r['ref']:Polygon(r['outline']) for r in json.loads((H/'model_alignment_before.json').read_text())['rows']}
def draw(ax,g,c,z=1,alpha=1,edge='none',lw=.5):
    if g.is_empty:return
    for p in [g] if g.geom_type=='Polygon' else g.geoms:
        if p.geom_type!='Polygon':continue
        vertices=[];codes=[]
        for ring in [p.exterior]+list(p.interiors):
            xy=list(ring.coords);vertices.extend(xy);codes.extend([MP.MOVETO]+[MP.LINETO]*(len(xy)-2)+[MP.CLOSEPOLY])
        ax.add_patch(PathPatch(MP(vertices,codes),facecolor=c,edgecolor=edge,lw=lw,zorder=z,alpha=alpha))
@lru_cache(None)
def surface(ml,old):
    ll=1 if ml==37 else 32;ps,rs,ts,vs,board=before if old else after
    op=unary_union([r['geometry'] for r in rs if r['layer']==ml]) if old else cam[ml]
    # Add unchanged native pad apertures to the old mask for an equivalent comparison.
    if old:op=op.union(unary_union([p['geometry'].buffer(.05,join_style='mitre') for p in ps if p['layer'] in (ll,74)]))
    copper=unary_union([r['geometry'] for r in rs if r['layer']==ll and r['net']=='GND']+[p['geometry'] for p in ps if p['layer'] in (ll,74)]+[t['geometry'].buffer(t['width']/2) for t in ts if t['layer']==ll and t['net']]+[Point(v['x'],v['y']).buffer(v['diameter']/2) for v in vs if v['low']<=ll<=v['high']])
    keep=board.difference(op)
    return ll,ps,vs,board,op,copper,keep,keep.intersection(copper)
def face(ax,ml,old=False,body=False,labels=False):
    ll,ps,vs,board,op,copper,keep,under=surface(ml,old)
    draw(ax,board,'#17313b');draw(ax,copper,'#e2bb50',2)
    draw(ax,keep,'#28583e',3);draw(ax,under,'#62843e',4)
    for p in ps:
        if p['hole']>0:draw(ax,Point(p['x'],p['y']).buffer(p['hole']/2),'#fafafa',6)
    for v in vs:
        if not v['low']<=ll<=v['high']:continue
        pt=Point(v['x'],v['y']);covered=not op.covers(pt)
        draw(ax,pt.buffer(v['hole']/2),'#28583e' if covered else '#17313b',5)
    if body and ll==32:
        for ref,g in bodies.items():
            draw(ax,g,'#f4f3ec' if ref[0]=='C' else '#30373b',7,edge='#8d9695',lw=.4)
            if labels:
                c=g.centroid;ax.text(c.x,c.y,ref,ha='center',va='center',fontsize=6,color='#25343a' if ref[0]=='C' else 'white',zorder=8)
    ax.set_aspect('equal');ax.set_xlim(-7.1,26.6);ax.set_xlabel('X (mm)');ax.grid(alpha=.1)
fig,axes=plt.subplots(1,4,figsize=(16,9),layout='constrained')
for ax,ml,old,title in zip(axes,(38,38,37,37),(True,False,True,False),('Before | component face','After | component face','Before | opposite face','After | opposite face')):
    face(ax,ml,old,body=ml==38);ax.set_ylim(19.5,73.5);ax.set_title(title,fontsize=12)
axes[0].set_ylabel('Y (mm)');fig.suptitle('Compact solder mask | actual saved PCB / native CAM',fontsize=17)
fig.supxlabel('Green = retained solder mask; gold = exposed copper. Both faces shown in the same XY frame.\nC/R pad-hull margin 0.20 mm | Local via-land margin 0.15 mm | Pads, copper and bodies unchanged',fontsize=11)
fig.savefig(OUT/'Mask_Before_After.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(10,14),layout='constrained')
for ax,ml,title in zip(axes,(38,37),('Bottom | component and RF face','Top | local via covers')):
    face(ax,ml,body=ml==38,labels=True);ax.set_ylim(-12.2,88.1);ax.set_title(title)
axes[0].set_ylabel('Y (mm)');fig.suptitle('Saved 16 RF / 38 DC carrier | corrected masks',fontsize=16)
fig.supxlabel('Native CAM and saved geometry render, not a GUI screenshot\nGreen = mask; gold = exposed copper | '+digest[:16],fontsize=10)
fig.savefig(OUT/'Corrected_Masks_Both_Faces.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(13,5),layout='constrained')
for ax,ref in zip(axes,('C11','C12','C13')):
    face(ax,38);g=bodies[ref];x0,y0,x1,y1=g.bounds;ax.set_xlim(x0-.7,x1+.7);ax.set_ylim(y0-.7,y1+.7)
    xx,yy=g.exterior.xy;ax.plot(xx,yy,color='#38daff',lw=1.7,zorder=8,label='Native 3D body outline')
    pp=sorted([p for p in pads if p['ref']==ref],key=lambda p:p['pin']);ax.plot([p['x'] for p in pp],[p['y'] for p in pp],color='white',ls='--',lw=.8,zorder=8)
    for p in pp:ax.plot(p['x'],p['y'],'+',color='#ffffff',ms=8,zorder=9)
    ax.set_title(ref+' | pad axis and saved body');ax.set_ylabel('Y (mm)')
axes[0].legend(loc='lower left',fontsize=8);fig.suptitle('Capacitor registration | 1206 maximum body 3.50 x 1.80 mm',fontsize=14)
fig.supxlabel('Cyan = saved native 3D body outline; white crosses = pad centres. No component relocation.',fontsize=10)
fig.savefig(OUT/'Capacitor_Pad_Registration.png',dpi=180);plt.close(fig)
assert digest==hashlib.sha256(pcb.read_bytes()).hexdigest()
(H/'render_manifest.json').write_text(json.dumps(dict(source_sha256=digest,images={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in OUT.glob('*.png')}),indent=2))
print('Rendered before/after, both faces, and capacitor registration images')
