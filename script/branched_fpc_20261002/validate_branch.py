"""Check saved native copper, drills, coverlay and schematic independently."""
from pathlib import Path
import sys,json,struct,hashlib,collections,math
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile,UNIT
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Circle,Rectangle

OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/ZIF_to_2xZIF';P=OUT/'ZIF_to_2xZIF.PcbDoc'
plan=json.loads((OUT/'design_plan.json').read_text())
upper_tip=plan['length_mm'];separation=plan['output_end_separation_mm'];lower_tip=upper_tip-separation
with olefile.OleFileIO(P) as o:d={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
nets=properties(d['Nets6/Data']);cs=properties(d['Components6/Data']);ps=pads_stream(d['Pads6/Data']);rs=[];ts=[];vs=[]
for rec in binary_records(d['Regions6/Data'],11):
 b=rec['body'];n=struct.unpack_from('<I',b,18)[0];pos=22+n;count=struct.unpack_from('<I',b,pos)[0];pos+=4
 points=[tuple(v*UNIT for v in struct.unpack_from('<2d',b,pos+16*i)) for i in range(count)]
 rs.append(dict(layer=b[0],net=struct.unpack_from('<H',b,3)[0],g=Polygon(points)))
for rec in binary_records(d['Tracks6/Data'],4):
 b=rec['body'];x1,y1,x2,y2,w=[v*UNIT for v in struct.unpack_from('<5i',b,13)]
 ts.append(dict(layer=b[0],net=struct.unpack_from('<H',b,3)[0],g=LineString([(x1,y1),(x2,y2)]).buffer(w/2),a=[x1,y1],b=[x2,y2],width=w))
for rec in binary_records(d['Vias6/Data'],3):
 b=rec['body'];x,y,size,hole=[v*UNIT for v in struct.unpack_from('<4i',b,13)]
 vs.append(dict(net=struct.unpack_from('<H',b,3)[0],x=x,y=y,size=size,hole=hole,g=Point(x,y).buffer(size/2),drill=Point(x,y).buffer(hole/2),span=list(b[29:31])))
checks=[]
def ck(ok,s):
 checks.append(dict(check=s,passed=bool(ok)))
 if not ok:raise AssertionError(s)
ck(len(ps)==153 and len(cs)==3 and len(nets)==51,'153 contacts, three ends and 51 nets')
ck(all(hashlib.sha256((R/n).read_bytes()).hexdigest()==v for n,v in plan['source_hashes'].items()),'Original carrier and straight cable remain unchanged')
allg={};padmap={}
for p in ps:
 x,y,sx,sy=[v*UNIT for v in p['coords'][:4]]
 p['g']=box(x-sx/2,y-sy/2,x+sx/2,y+sy/2)
 ref=cs[p['component']]['SOURCEDESIGNATOR'];padmap[f"{ref}.{p['number']}"]=p
 ck(p['layer']==(32 if ref=='C' else 1) and p['coords'][8]==0,f"{ref}.{p['number']}: correct contact face, no drill")
for ni,n in enumerate(nets):
 pin=int(n['NAME'].split('_')[1])
 members=[p for p in ps if p['net']==ni]
 ck(len(members)==3 and all(padmap[f'{ref}.{pin}']['net']==ni for ref in ('A','B','C')),f'{n["NAME"]}: C.n, A.n and B.n on the same net')
 for lay in (1,32):
  shapes=[p['g'] for p in members if p['layer']==lay]+[r['g'] for r in rs if r['net']==ni and r['layer']==lay]+[t['g'] for t in ts if t['net']==ni and t['layer']==lay]+[v['g'] for v in vs if v['net']==ni]
  allg[ni,lay]=unary_union(shapes)
  ck(allg[ni,lay].geom_type=='Polygon' and allg[ni,lay].is_valid,f'{n["NAME"]}: continuous copper on layer {lay}')
 bridges=[v for v in vs if v['net']==ni]
 ck(len(bridges)==1 and all(bridges[0]['g'].difference(allg[ni,l]).area<1e-10 for l in (1,32)),f'{n["NAME"]}: one physical plated bridge joins both layers')
minimum=(999,None)
for l in (1,32):
 for i in range(51):
  for j in range(i+1,51):
   gap=allg[i,l].distance(allg[j,l])
   if gap<minimum[0]:minimum=(gap,[l,nets[i]['NAME'],nets[j]['NAME']])
ck(minimum[0]>.0707,'No shorts; retained minimum contact clearance above 0.0707 mm')
b=properties(d['Board6/Data'])[0]
def mm(s):return float(s[:-3])*.0254
outline=Polygon([(mm(b[f'VX{i}']),mm(b[f'VY{i}'])) for i in range(len(plan['outline']))])
ck(outline.is_valid and not outline.interiors,'One continuous flex outline with no cutout')
ck(all(outline.buffer(3e-6).covers(g) for g in allg.values()),'All signal copper inside saved outline')
ck(abs(outline.bounds[3]-420)<3e-6,'Saved overall length 420 mm')
component_y={c['SOURCEDESIGNATOR']:mm(c['Y']) for c in cs}
ck(abs(component_y['A']-component_y['B']-70)<3e-6,'Saved output-tip separation is user-specified 70 mm')
ck(len(vs)==51 and all(v['span']==[1,32] and 384.69<v['y']<399.71 for v in vs),'51 through vias in static branch zone, spanning only the two flex copper layers')
holegap=min(v['drill'].distance(allg[i,l]) for v in vs for i in range(51) if i!=v['net'] for l in (1,32))
ck(holegap>.145,'Drills do not intersect adjacent-net copper')
ck(all(abs(v['size']-.30)<3e-6 and abs(v['hole']-.10)<3e-6 for v in vs),'0.30 mm lands / 0.10 mm drills; nominal 0.10 mm annular rings')
top=unary_union([r['g'] for r in rs if r['layer']==37]);bottom=unary_union([r['g'] for r in rs if r['layer']==38])
ck(top.symmetric_difference(unary_union([box(25.59,upper_tip-3,41.21,upper_tip),box(25.59,lower_tip,41.21,lower_tip+3)])).area<.001,'Top coverlay: two 3 mm mating openings')
ck(bottom.symmetric_difference(box(-.01,0,15.61,3)).area<.001,'Bottom coverlay: common-end 3 mm opening only')
ck(all(not top.intersects(v['g']) and not bottom.intersects(v['g']) for v in vs),'Explicit coverlay openings avoid vias')
ck(not any(r['layer'] in (35,36) for r in rs) and not any(t['layer'] in (35,36) for t in ts),'No explicit paste geometry')
native=(OUT/'native_validation.txt').read_text()
ck('PAD_PASTE_ENABLED=0' in native,'Altium confirms disabled paste on all contact pads after save/reopen')
# Via inherited pad-cache booleans are not CAM apertures; use the native via
# mask override fields and actual paste-layer primitives, as in carrier QA.
via_records=binary_records(d['Vias6/Data'],3)
ck(all(v['body'][66]==2 and struct.unpack_from('<i',v['body'],54)[0]*UNIT<-.99 and struct.unpack_from('<i',v['body'],242)[0]*UNIT<-.99 for v in via_records),'All saved vias have manual negative mask expansion on both faces, closing every aperture')
ck(sum(s.startswith('PAD=') and '|MASK=0|' in s for s in native.splitlines())==153,'Altium confirms zero pad mask expansion on all 153 contacts')
layers={b[k]:k[:-4] for k in b if k.startswith('V9_STACK_LAYER') and k.endswith('_NAME')}
ck('Top Layer' in layers and 'Bottom Layer' in layers and b['V9_SUBSTACK0_ISFLEX']=='TRUE','Saved two-copper flex stack')

# Recover the connectivity from saved SchDoc pin positions, wires and net labels.
with olefile.OleFileIO(OUT/'ZIF_to_2xZIF.SchDoc') as o:sr=properties(o.openstream('FileHeader').read())
refs={int(p['OwnerIndex']):p['Text'] for p in sr if p.get('RECORD')=='34'}
labels={(int(p.get('Location.X',0)),int(p.get('Location.Y',0))):p['Text'] for p in sr if p.get('RECORD')=='25'}
wires=[[(int(w['X'+str(j)]),int(w['Y'+str(j)])) for j in (1,2)] for w in sr if w.get('RECORD')=='27']
recovered={}
for p in [p for p in sr if p.get('RECORD')=='2']:
 direction=int(p['PinConglomerate'])&3;dx,dy=((1,0),(0,1),(-1,0),(0,-1))[direction]
 tip=(int(p['Location.X'])+dx*int(p['PinLength']),int(p['Location.Y'])+dy*int(p['PinLength']))
 stubs=[w for w in wires if tip in w]
 ck(len(stubs)==1,'Saved schematic: exactly one wire stub at '+refs[int(p['OwnerIndex'])]+'.'+p['Designator'])
 other=next(x for x in stubs[0] if x!=tip)
 recovered[refs[int(p['OwnerIndex'])]+'.'+p['Designator']]=labels[other]
ck(recovered=={key:nets[p['net']]['NAME'] for key,p in padmap.items()},'Saved schematic wire/label graph exactly matches all 153 PCB pins')
ck(len({v for v in recovered.values()})==51,'Exactly 51 schematic signal nets')
ck('DRC_RETURNED_TRUE' in native and 'REBUILT_CONNECTION_COUNT=0' in native,'Native Altium DRC and rebuilt connectivity pass after save/reopen')
ck(len(d['Connections6/Data'])==0,'Saved PCB has zero outstanding connections')
report=dict(checks=checks,minimum_gap_mm=minimum[0],minimum_pair=minimum[1],minimum_drill_to_other_net_mm=holegap,native_drc_performed=True,stored_connections_count=0,stored_connections_rebuilt_by_altium=True,pcb_sha256=hashlib.sha256(P.read_bytes()).hexdigest())
(OUT/'geometry_validation.json').write_text(json.dumps(report,indent=2)+'\n')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
fig=plt.figure(figsize=(16,11),facecolor='#f4f3ee');gs=fig.add_gridspec(2,3,width_ratios=[.70,1.05,1.3],height_ratios=[1,1],wspace=.30,hspace=.32)
axfull=fig.add_subplot(gs[:,0]);axdetail=fig.add_subplot(gs[0,1]);axterm=fig.add_subplot(gs[1,1]);axinfo=fig.add_subplot(gs[:,2])
def draw(ax):
 ax.add_patch(Patch(list(outline.exterior.coords),fc='#efce71',ec='#454938',lw=.8,zorder=0))
 for l in (32,1):
  for (ni,layer),g in allg.items():
   if layer==l:ax.add_patch(Patch(list(g.exterior.coords),fc='#357eb0' if l==32 else '#b46b2c',ec='none',alpha=.8))
 for v in vs:ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,fc='white',ec='none',zorder=4))
 for x,y in [(0,0),(25.6,lower_tip),(25.6,upper_tip-4)]:ax.add_patch(Rectangle((x,y),15.6,4,fill=False,ec='#71348b',ls='--',lw=.9))
 ax.set_aspect('equal');ax.grid(alpha=.13)
def dim(ax,a,b,text,offset=(0,0),rotation=0,fs=9):
 ax.annotate('',xy=a,xytext=b,arrowprops=dict(arrowstyle='<->',lw=.8,color='#283c44'))
 ax.text((a[0]+b[0])/2+offset[0],(a[1]+b[1])/2+offset[1],text,ha='center',va='center',rotation=rotation,fontsize=fs,color='#283c44')
draw(axfull);axfull.set_xlim(-30,67);axfull.set_ylim(-8,435);axfull.axis('off')
dim(axfull,(-14,0),(-14,420),'420 mm *',(-5,0),90,10)
dim(axfull,(52,lower_tip),(52,upper_tip),'70 mm',(5,0),90,9)
for x,y,t in [(33.4,upper_tip+8,'A / Top'),(34,lower_tip-10,'B / Top'),(7.8,-6,'C / Bottom')]:axfull.text(x,y,t,ha='center',fontsize=9,weight='bold')
axfull.set_title('Full outline - same XY view',fontsize=11,weight='bold')
draw(axdetail);axdetail.set_xlim(-2,44);axdetail.set_ylim(373,423);axdetail.set_xlabel('X (mm)');axdetail.set_ylabel('Y (mm)');axdetail.set_title('Rounded branch + crossover vias',fontsize=11,weight='bold')
dim(axdetail,(15.6,375),(25.6,375),'10 mm',(0,1.5),fs=8)
dim(axdetail,(42.6,400),(42.6,420),'20 mm',(-2,0),90,8)
axdetail.text(22,406,'A: exposed Top contacts',ha='center',fontsize=8)
draw(axterm);axterm.set_xlim(25.5,28.2);axterm.set_ylim(396.8,400.5);axterm.set_xlabel('X (mm)');axterm.set_ylabel('Y (mm)');axterm.set_title('Saved crossover copper - enlarged',fontsize=11,weight='bold')
axinfo.axis('off');axinfo.set_xlim(0,1);axinfo.set_ylim(0,1)
axinfo.text(0,.98,'Each pin branches to both outputs',va='top',fontsize=16,weight='bold',color='#263d48')
axinfo.plot([.1,.42,.42,.74],[.86,.86,.92,.92],lw=2.5,color='#357eb0');axinfo.plot([.42,.42,.74],[.86,.80,.80],lw=2.5,color='#b46b2c');axinfo.plot(.42,.86,'o',color='#273d48')
axinfo.text(.06,.86,'C.n',ha='right',va='center',fontsize=12);axinfo.text(.79,.92,'A.n',va='center',fontsize=12);axinfo.text(.79,.80,'B.n',va='center',fontsize=12)
axinfo.text(0,.74,'n = 1...51; all 51 nets are connected.\nContact numbers increase left to right in this\nTop XY projection. Bottom physical view is mirrored.',va='top',fontsize=10,linespacing=1.7)
axinfo.text(0,.59,'Mating ends\n51 contacts / 0.30 mm pitch / 15.60 mm width\nOriginal staggered finger geometry\n3.00 mm exposed contacts / 4.00 mm back stiffeners\nTarget finished mating thickness: 0.20 +/- 0.03 mm',va='top',fontsize=10,linespacing=1.8)
axinfo.text(0,.40,'Routing\nBrown: Top copper, A to B\nBlue: Bottom copper, C to branch vias\n51 plated vias: land 0.30 / drill 0.10 mm\nJunction is a static no-bend region.\nMinimum saved copper gap: %.5f mm'%minimum[0],va='top',fontsize=10,linespacing=1.8)
axinfo.text(0,.18,'Output-tip separation: 70 mm (user-specified).\n* Overall 420 mm remains provisional.\n10 mm interpreted as strip-to-strip clear gap.',va='top',fontsize=9,color='#705d33',linespacing=1.6)
axinfo.text(0,.07,'NATIVE ALTIUM DRC: 0 AFTER SAVE / REOPEN\nSaved geometry and connectivity checked independently.\nFlex stack, backing and drill process need fabrication review.',va='top',fontsize=9,color='#38654b',weight='bold',linespacing=1.5)
fig.suptitle('ZIF to 2 x ZIF  |  51 same-number parallel branches',x=.04,ha='left',fontsize=21,weight='bold',y=.975)
fig.subplots_adjust(left=.045,right=.975,top=.915,bottom=.055)
fig.savefig(OUT/'ZIF_to_2xZIF_draft.png',dpi=160);plt.close(fig)
print(json.dumps({'checks':len(checks),'minimum_gap_mm':minimum[0],'minimum_drill_to_other_net_mm':holegap,'review':str(OUT/'ZIF_to_2xZIF_draft.png')}))
