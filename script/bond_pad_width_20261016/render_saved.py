"""Render the final saved pads, measured gap and remaining via-land protrusion."""
from pathlib import Path
import sys,json,hashlib,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import Point
from shapely.ops import nearest_points
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'Bond_Pad_Width_20261017'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
sch=json.loads((P/'schematic_validation.json').read_text());pcb=P/(P.name+'.PcbDoc');sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest();digest=sha(pcb)
pads,regions,tracks,vias,outline=read_snapshot(pcb,sch)
before=read_snapshot(H/'baseline'/(P.name+'.PcbDoc'),sch)
old={p['pin']:p for p in before[0] if p['ref']=='Q1'};new={p['pin']:p for p in pads if p['ref']=='Q1'}
assert len(new)==38 and all(abs(p['sy']-.26)<.000003 for p in new.values())
audit=json.loads((H/'width_audit.json').read_text());assert audit['passed'] and audit['source_sha256']==digest
plan=json.loads((H/'candidate.json').read_text());cx,cy=plan['sample_center']
fig,axes=plt.subplots(1,3,figsize=(17,6),layout='constrained',gridspec_kw={'width_ratios':[1.3,1,1]})
for ax in axes:
    ax.set_facecolor('#142b36');ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)')
    for p in tracks:
        if p['layer']==32 and p['net'] and p['net'].startswith('MW'):
            g=p['geometry'].buffer(p['width']/2,quad_segs=24);xx,yy=g.exterior.xy;ax.fill(xx,yy,color='#d9ac45')
    for v in vias:
        if abs(v['x']-cx)>4 or abs(v['y']-cy)>5:continue
        if v['net']=='GND':color='#78918b'
        elif any(p['net']==v['net'] and p['geometry'].distance(Point(v['x'],v['y']))<.001 for p in new.values()):color='#f1af65'
        else:continue
        ax.add_patch(plt.Circle((v['x'],v['y']),v['diameter']/2,color=color))
    for pin,p in new.items():
        xx,yy=p['geometry'].exterior.xy;ax.fill(xx,yy,color='#efc75e')
        xx,yy=old[pin]['geometry'].exterior.xy;ax.plot(xx,yy,color='#76d8ff',lw=.65)
        xx,yy=p['geometry'].exterior.xy;ax.plot(xx,yy,color='#efc75e',lw=.8)
        if ax is axes[0]:ax.text(p['x'],p['y'],pin,ha='center',va='center',fontsize=6,color='#142b36')
    for v in vias:
        if abs(v['x']-cx)<4 and abs(v['y']-cy)<5:
            ax.add_patch(plt.Circle((v['x'],v['y']),v['hole']/2,color='#142b36',zorder=4))
axes[0].set_xlim(cx-4.3,cx+4.3);axes[0].set_ylim(cy-4.7,cy+4.7);axes[0].set_title('All 38 pads: 0.250 to 0.260 mm')
ga,gb=new['4']['geometry'],new['5']['geometry'];u,v=nearest_points(ga,gb);mid=((u.x+v.x)/2,(u.y+v.y)/2)
axes[1].set_xlim(min(ga.bounds[0],gb.bounds[0])-.12,max(ga.bounds[2],gb.bounds[2])+.12);axes[1].set_ylim(min(ga.bounds[1],gb.bounds[1])-.12,max(ga.bounds[3],gb.bounds[3])+.35)
axes[1].plot([u.x,v.x],[u.y,v.y],color='#ff706b',lw=1.8)
axes[1].annotate(f'{u.distance(v):.6f} mm pad gap\nJLCPCB minimum: 0.150 mm',xy=mid,xytext=(mid[0],max(ga.bounds[3],gb.bounds[3])+.16),ha='center',fontsize=9,color='#ff706b',arrowprops=dict(arrowstyle='->',color='#ff706b'))
axes[1].set_title('Limiting QD pair: pads 4 / 5')
p=new['29'];v=next(v for v in vias if v['net']==p['net'] and p['geometry'].distance(Point(v['x'],v['y']))<.001)
axes[2].set_xlim(p['x']-.65,p['x']+.65);axes[2].set_ylim(p['y']-.65,p['y']+.65)
axes[2].annotate('Via land diameter: 0.350 mm\nHole: 0.200 mm',xy=(v['x'],v['y']),xytext=(p['x'],p['y']+.35),ha='center',fontsize=9,color='#f1af65',arrowprops=dict(arrowstyle='->',color='#f1af65'))
axes[2].text(p['x'],p['y']-.4,'0.045 mm side protrusion remains\nPad 29 end protrusion: 0.074 mm',ha='center',fontsize=9,color='#ffffff')
axes[2].set_title('Widening does not contain the via land')
fig.suptitle('Saved Altium QD bond pads | short-axis width increased by 4%',fontsize=16)
fig.supxlabel('Gold: saved pad | Cyan: previous pad outline | Orange: DC via land\nPad centres, lengths, rotations, end-midpoint alignment and net mapping preserved. Native geometry render, not a GUI screenshot.',fontsize=10)
path=OUT/'Saved_Bond_Pad_Width.png';fig.savefig(path,dpi=180);plt.close(fig)
assert sha(pcb)==digest
(H/'render_manifest.json').write_text(json.dumps(dict(source_sha256=digest,images={path.name:sha(path)}),indent=2))
print(str(path))
