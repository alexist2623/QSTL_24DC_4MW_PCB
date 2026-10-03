"""Independently verify and render saved Altium cable copper, without UI access."""
from pathlib import Path
import sys,struct,json,math,hashlib,csv
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile,UNIT
from shapely.geometry import Polygon,LineString,box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Rectangle,FancyBboxPatch
OUT=R/'QSTL_24DC_4MW_PCB/FPC_15015_0451';P=OUT/'FPC_15015_0451.PcbDoc'
with olefile.OleFileIO(P) as o:d={'/'.join(s):o.openstream(s).read() for s in o.listdir()}
nets=properties(d['Nets6/Data']);pads=pads_stream(d['Pads6/Data']);b=properties(d['Board6/Data'])[0]
regs=[]
for row in binary_records(d['Regions6/Data'],11):
    v=row['body'];off=v.index(b'V7_LAYER=');n=struct.unpack_from('<I',v,off-4)[0]
    pr=dict(x.split('=',1) for x in v[off:off+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
    pos=off+n;rings=[]
    while pos<len(v):
        count=struct.unpack_from('<I',v,pos)[0];pos+=4
        rings.append([tuple(c*UNIT for c in struct.unpack_from('<2d',v,pos+i*16)) for i in range(count)]);pos+=count*16
    regs.append(dict(layer=v[0],net=struct.unpack_from('<H',v,3)[0],props=pr,g=Polygon(rings[0],rings[1:])))
tracks=[]
for row in binary_records(d['Tracks6/Data'],4):
    v=row['body'];xy=struct.unpack_from('<5i',v,13);x1,y1,x2,y2,w=[c*UNIT for c in xy]
    tracks.append(dict(layer=v[0],net=struct.unpack_from('<H',v,3)[0],g=LineString([(x1,y1),(x2,y2)]).buffer(w/2),width=w))
checks=[]
def check(condition,message):
    checks.append(dict(check=message,passed=bool(condition)))
    assert condition,message
check(len(nets)==51,'51 named nets')
check(len(pads)==102,'102 native pads')
check(len({p['component'] for p in pads})==2,'Two integral contact arrays')
check(all(p['layer']==1 and p['coords'][8]==0 for p in pads),'All contacts Top, no drills')
check(len(binary_records(d['Vias6/Data'],3))==0,'No vias')
check(len(d['Connections6/Data'])==0,'Saved connection count zero')
check({r['layer'] for r in regs}=={1,37},'Copper and Top coverlay apertures only')
check(sum(t['net']!=65535 for t in tracks)==51,'51 parallel signal tracks')
geoms=[];rows=[]
for i,n in enumerate(nets):
    pp=[p for p in pads if p['net']==i];rr=[r for r in regs if r['net']==i];tt=[t for t in tracks if t['net']==i]
    check(len(pp)==2 and len(rr)==2 and len(tt)==1,n['NAME']+': two terminals and one trace')
    pin_number=int(n['NAME'][2:]);expected_y=.3*pin_number
    check(all(abs(p['coords'][1]*UNIT-expected_y)<3e-6 for p in pp),n['NAME']+': exact 0.30 mm pitch')
    padpolys=[]
    for p in pp:
        x,y,sx,sy=[c*UNIT for c in p['coords'][:4]];padpolys.append(box(x-sx/2,y-sy/2,x+sx/2,y+sy/2))
    g=unary_union([r['g'] for r in rr]+[t['g'] for t in tt]+padpolys)
    check(g.geom_type=='Polygon' and g.is_valid,n['NAME']+': physically continuous saved copper')
    geoms.append(g);rows.append([n['NAME'],pin_number,pin_number,round(expected_y,6)])
minimum=min(geoms[i].distance(geoms[j]) for i in range(51) for j in range(i+1,51))
check(minimum>.0707,'All signal nets isolated; drawing minimum diagonal clearance')
check(all(abs(t['width']-.20)<3e-6 for t in tracks if t['net']!=65535),'Body conductors 0.20 mm wide')
layers={b[k]:k[:-4] for k in b if k.startswith('V9_STACK_LAYER') and k.endswith('_NAME')}
check('Bottom Layer' not in layers,'One copper layer in stored V9 stack')
check(b['V9_SUBSTACK0_ISFLEX']=='TRUE','Native flex substack flag')
def mm(value):return float(value[:-3])*.0254
vertices=[(.2,0,None),(101.4,0,(101.4,.2,270,360)),(101.6,.2,None),(101.6,15.4,(101.4,15.4,0,90)),(101.4,15.6,None),(.2,15.6,(.2,15.4,90,180)),(0,15.4,None),(0,.2,(.2,.2,180,270))]
for i,(x,y,arc) in enumerate(vertices):
    check(abs(mm(b[f'VX{i}'])-x)<3e-6 and abs(mm(b[f'VY{i}'])-y)<3e-6,f'Outline vertex {i}: exact cable dimensions')
    check(b[f'KIND{i}']==('1' if arc else '0'),f'Outline segment {i}: native line/arc type')
    if arc:
        cx,cy,a1,a2=arc
        check(abs(mm(b[f'CX{i}'])-cx)<3e-6 and abs(mm(b[f'CY{i}'])-cy)<3e-6 and abs(mm(b[f'R{i}'])-.2)<3e-6 and float(b[f'SA{i}'])==a1 and float(b[f'EA{i}'])==a2,f'Outline corner {i}: native R0.20 arc')
openings=sorted([r['g'].bounds for r in regs if r['layer']==37])
check(len(openings)==2 and all(abs(a-bb)<3e-6 for bounds,expected in zip(openings,[(0,-.01,3,15.61),(98.6,-.01,101.6,15.61)]) for a,bb in zip(bounds,expected)),'Two saved 3 mm full-width coverlay openings')
check(abs(mm(b[layers['Top Layer']+'COPTHICK'])-.018)<3e-6,'18 um copper')
check(abs(mm(b[layers['Polyimide base + adhesive']+'DIELHEIGHT'])-.045)<3e-6,'45 um PI/adhesive base')
check(abs(mm(b[layers['Top Solder']+'DIELHEIGHT'])-.050)<3e-6,'50 um PI/adhesive coverlay')
carrier=R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc'
check(hashlib.sha256(carrier.read_bytes()).hexdigest()==(H/'carrier_before.sha256').read_text(),'Original carrier unchanged')
with (OUT/'contact_mapping.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['Net','End_A_contact','End_B_contact','Y_mm']);w.writerows(rows)
(OUT/'saved_geometry_validation.json').write_text(json.dumps(dict(checks=checks,minimum_copper_gap_mm=minimum,pcb_sha256=hashlib.sha256(P.read_bytes()).hexdigest()),indent=2))

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(16,9),facecolor='#f5f4ef');gs=fig.add_gridspec(3,3,height_ratios=[.22,1.05,1.65],hspace=.48,wspace=.28)
fig.text(.035,.955,'MOLEX 15015-0451  |  Altium FPC reconstruction',fontsize=21,weight='bold',color='#172f36')
fig.text(.035,.918,'51 contacts   /   0.30 mm pitch   /   Type A: contacts on the same face   /   catalog length: 102 mm',fontsize=11,color='#54666a')
ax=fig.add_subplot(gs[1,:]);ax.set_aspect('equal');ax.set_xlim(-3,104.6);ax.set_ylim(-4,20.7);ax.axis('off')
def draw(ax,zoom=False):
    ax.add_patch(FancyBboxPatch((0,0),101.6,15.6,boxstyle='round,pad=0,rounding_size=0.2',facecolor='#dbac47',edgecolor='#4c4837',lw=.8,zorder=1))
    for g in geoms:ax.add_patch(Patch(list(g.exterior.coords),closed=True,facecolor='#b77326',edgecolor='none',zorder=2))
    ax.add_patch(Rectangle((3,0),95.6,15.6,facecolor='#f9d66a',alpha=.68,edgecolor='none',zorder=3))
    for a in [0,98.6]:
        for r in regs:
            if r['layer']==1 and r['g'].bounds[0]>=a-.01 and r['g'].bounds[2]<=a+3.06:
                clipped=r['g'].intersection(box(a,0,a+3,15.6))
                ax.add_patch(Patch(list(clipped.exterior.coords),closed=True,facecolor='#d9bb64',edgecolor='#72551e',lw=.18 if zoom else .05,zorder=4))
    for x in [4,97.6]:ax.axvline(x,color='#326b84',ls='--',lw=1,zorder=5)
draw(ax)
def dim(ax,a,b,label,y):
    ax.annotate('',xy=(a,y),xytext=(b,y),arrowprops=dict(arrowstyle='<->',lw=.8,color='#273b40'))
    ax.text((a+b)/2,y+.45,label,ha='center',fontsize=11,color='#273b40')
dim(ax,0,101.6,'101.60 mm',18)
ax.annotate('',xy=(-1.8,0),xytext=(-1.8,15.6),arrowprops=dict(arrowstyle='<->',lw=.8));ax.text(-2.7,7.8,'15.60 mm',rotation=90,va='center',ha='center')
ax.text(0,-2,'END A',weight='bold');ax.text(101.6,-2,'END B',ha='right',weight='bold')
ax.text(50.8,-2,'Top / mating face   |   all 51 conductors retained',ha='center',color='#54666a')
ax1=fig.add_subplot(gs[2,0]);draw(ax1,True);ax1.set_xlim(-.18,4.35);ax1.set_ylim(0,3.05);ax1.set_aspect('equal');ax1.set_title('Staggered contacts - saved copper',loc='left',fontsize=12,weight='bold',pad=15)
ax1.set_xlabel('Distance from end (mm)');ax1.set_ylabel('Across cable (mm)');ax1.grid(alpha=.12)
ax1.axvline(3,color='#78442a',lw=.8);ax1.text(3.04,2.88,'Coverlay',fontsize=8,color='#78442a');ax1.text(4.03,.13,'4 mm stiffener',rotation=90,fontsize=8,color='#326b84')
ax2=fig.add_subplot(gs[2,1]);ax2.axis('off');ax2.set_title('Section at either cable end',loc='left',fontsize=12,weight='bold',pad=15)
ax2.set_xlim(-.1,6.3);ax2.set_ylim(-.19,.21)
ax2.add_patch(Rectangle((0,0),6,.045,color='#dfa943'))
ax2.add_patch(Rectangle((0,.045),6,.018,color='#bd7936'))
ax2.add_patch(Rectangle((3,.063),3,.05,color='#f4d775'))
ax2.add_patch(Rectangle((0,-.15),4,.15,color='#80a9b9'))
ax2.annotate('50 um coverlay + adhesive',xy=(4.5,.10),xytext=(.0,.18),fontsize=8,arrowprops=dict(arrowstyle='-',lw=.6))
ax2.annotate('18 um copper',xy=(2,.054),xytext=(.0,.14),fontsize=8,arrowprops=dict(arrowstyle='-',lw=.6))
ax2.annotate('45 um base + adhesive',xy=(5,.02),xytext=(.0,-.175),fontsize=8,arrowprops=dict(arrowstyle='-',lw=.6))
ax2.text(.1,-.095,'150 um stiffener + adhesive',fontsize=8)
ax2.text(.0,-.22,'Exposed end: 0.213 mm layer sum\nDrawing requirement: 0.20 +/- 0.03 mm',fontsize=9,transform=ax2.transData)
ax3=fig.add_subplot(gs[2,2]);ax3.axis('off');ax3.set_title('Verified native geometry',loc='left',fontsize=12,weight='bold',pad=15)
ax3.text(0,.94,'51 isolated, continuous nets\n102 native contacts on Top\nNo holes, vias or paste\nOne copper layer / flex stack\nR0.20 outline corners\n3.00 mm contact openings\n4.00 mm back stiffeners',va='top',linespacing=1.7,fontsize=11,color='#273b40')
ax3.text(0,.05,'Geometric reconstruction; proprietary process\nand adhesive details are not fully disclosed.',fontsize=8.5,color='#746749',va='bottom')
fig.subplots_adjust(left=.035,right=.975,bottom=.08,top=.90)
fig.savefig(OUT/'FPC_15015_0451_review.png',dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
print(json.dumps({'nets':51,'native_pads':102,'min_gap_mm':minimum,'checks':len(checks),'review':str(OUT/'FPC_15015_0451_review.png')}))
