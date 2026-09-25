"""Dimension the actual saved holes against the centered cable envelope."""
from pathlib import Path
import json,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
H=Path(__file__).resolve().parent; P=H.parents[1]/'QSTL_24DC_4MW_PCB'
out=P/'Mechanical_Assembly/ZIF_M1_Review'
inputs=json.loads((out/'model_inputs.json').read_text())
validation=json.loads((P/'docs/ZIF_M1_mount_validation.json').read_text())
mounts=sorted(validation['mounts'],key=lambda m:m['x'])
width=inputs['cable']['width_mm'];center=9.75;left=center-width/2;right=center+width/2
left_hole_inner=mounts[0]['x']+mounts[0]['drill_mm']/2
right_hole_inner=mounts[1]['x']-mounts[1]['drill_mm']/2
gaps=[left-left_hole_inner,right_hole_inner-right]
report=dict(pcb_sha256=validation['pcb_sha256'],cable_width_mm=width,cable_edges_x_mm=[left,right],
    hole_centers_mm=[[m['x'],m['y']] for m in mounts],hole_diameters_mm=[m['drill_mm'] for m in mounts],
    inside_hole_edge_separation_mm=right_hole_inner-left_hole_inner,
    signed_hole_edge_to_cable_edge_clearance_mm=gaps,
    interpretation='Negative clearance means overlap in XY projection. The cable is above the PCB; this is not a claim that the hole void collides with it in 3D.',
    cable_height_assumption_mm=.47)
(out/'cable_hole_clearance.json').write_text(json.dumps(report,indent=2))
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11})
fig=plt.figure(figsize=(13.6,8.3),facecolor='white')
ax=fig.add_axes([.06,.34,.88,.57]);ax.set_aspect('equal')
ax.add_patch(Rectangle((0,0),19.5,7.1,facecolor='#faf6de',edgecolor='#667142',lw=1.5))
entry=inputs['cable']['free_end_y_mm']
ax.add_patch(Rectangle((1.05,entry),17.4,3.8,facecolor='#e6eaee',edgecolor='#6a7680',lw=1.5))
ax.text(9.75,4.45,'J1 / ZIF housing',ha='center',color='#3e4b56',fontsize=12)
ax.add_patch(Rectangle((left,-1.1),width,entry+1.1,facecolor='#e7b468',alpha=.33,edgecolor='#c06a0b',lw=1.5))
for m in mounts:
    ax.add_patch(Circle((m['x'],m['y']),m['drill_mm']/2,facecolor='white',edgecolor='#b52225',lw=2))
    ax.plot([m['x']-.14,m['x']+.14],[m['y']]*2,color='#b52225',lw=.8)
    ax.plot([m['x']]*2,[m['y']-.14,m['y']+.14],color='#b52225',lw=.8)
for x in (left,right):ax.plot([x,x],[-1.1,entry],color='#c06a0b',lw=2,ls='--')
ax.annotate('2 x diameter 1.20 mm',xy=(mounts[0]['x']-.35,mounts[0]['y']+.45),xytext=(.25,3.7),arrowprops={'arrowstyle':'->','color':'#b52225'},color='#b52225')
def dim(ax,x0,x1,y,label,color='#263e50'):
    ax.annotate('',xy=(x1,y),xytext=(x0,y),arrowprops={'arrowstyle':'<->','color':color,'lw':1.25})
    ax.text((x0+x1)/2,y+.14,label,ha='center',va='bottom',color=color,fontsize=11,bbox={'facecolor':'white','edgecolor':'none','pad':1})
dim(ax,mounts[0]['x'],mounts[1]['x'],-.6,'17.40 mm hole center pitch')
dim(ax,left,right,-1.8,'15.60 mm cable width','#b26509')
for x in (left,right):ax.plot([x,x],[-1.85,-1.2],color='#b26509',lw=.8)
ax.set_xlim(-.9,20.4);ax.set_ylim(-2.3,6.9);ax.axis('off')
detail=fig.add_axes([.07,.095,.32,.26]);detail.set_aspect('equal')
m=mounts[0];r=m['drill_mm']/2
detail.add_patch(Rectangle((.3,-.2),3.0,2.9,facecolor='#faf6de',edgecolor='none'))
detail.add_patch(Rectangle((left,-.2),1.35,2.9,facecolor='#e7b468',alpha=.4,edgecolor='none'))
detail.add_patch(Circle((m['x'],m['y']),r,facecolor='none',edgecolor='#b52225',lw=2))
detail.axvline(left,color='#b26509',lw=2,ls='--')
detail.plot([left,left_hole_inner],[m['y']]*2,color='#168354',lw=5)
detail.plot([left_hole_inner,left_hole_inner],[m['y'],2.5],color='#b52225',lw=.8,ls=':')
detail.annotate('',xy=(left_hole_inner,2.4),xytext=(left,2.4),arrowprops={'arrowstyle':'<->','color':'#b52225'})
detail.text((left+left_hole_inner)/2,2.5,'0.30 mm clearance',ha='center',color='#168354',fontsize=11)
detail.text(.3,.04,'Left hole detail; right is symmetric',fontsize=9,color='#40525e')
detail.set_xlim(.25,3.35);detail.set_ylim(-.1,2.85);detail.axis('off')
fig.text(.44,.28,'HOLE / CABLE RELATION — TOP PROJECTION',fontsize=13,fontweight='bold',color='#273e50')
fig.text(.44,.235,'Clear width between inner hole edges: 16.20 mm',fontsize=12)
fig.text(.44,.197,'Cable width: 15.60 mm',fontsize=12)
fig.text(.44,.158,'Signed clearance: +0.30 mm on each side (clearance)',fontsize=12,color='#168354',fontweight='bold')
fig.text(.44,.115,'Heads omitted so the drilled-hole outlines remain visible.',fontsize=10,color='#56636f')
fig.text(.44,.083,'Cable is a dimensional envelope above the PCB; this is an XY comparison.',fontsize=9,color='#56636f')
fig.text(.06,.955,'ZIF end mounting — cable and hole clearance',fontsize=19,fontweight='bold',color='#1c3445')
fig.text(.06,.925,'Saved PCB dimensions  |  mm  |  Dashed orange: cable edge  |  Red: drilled hole',fontsize=10,color='#56636f')
fig.text(.06,.025,'PCB '+validation['pcb_sha256'][:24]+'  |  Hole geometry from the saved M1 PCB; board width preserved.',fontsize=9,color='#56636f')
for ext in ('png','svg'):fig.savefig(out/('ZIF_Cable_Hole_Clearance.'+ext),dpi=190)
print(json.dumps(report,indent=2))
