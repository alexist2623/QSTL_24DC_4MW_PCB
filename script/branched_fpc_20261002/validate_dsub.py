"""Independently check and render copper parsed from the saved native draft."""
from pathlib import Path
import sys,json,struct,hashlib,math
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties,pads_stream,binary_records,olefile,UNIT
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch,Circle,Rectangle
OUT=R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/ZIF_to_DSUB25';P=OUT/'ZIF_to_DSUB25.PcbDoc'
plan=json.loads((OUT/'design_plan.json').read_text())
with olefile.OleFileIO(P) as o:d={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
nets=properties(d['Nets6/Data']);cs=properties(d['Components6/Data']);ps=pads_stream(d['Pads6/Data']);rs=[];ts=[];vs=[]
with olefile.OleFileIO(OUT/'ZIF_to_DSUB25.SchDoc') as o:sch=properties(o.openstream('FileHeader').read())
for record in sch:
 if record.get('RECORD')=='34':
  symbol=sch[int(record['OwnerIndex'])+1]
  for c in cs:
   if c['SOURCEUNIQUEID']==symbol['UniqueID']:c['SOURCEDESIGNATOR']=record['Text']
for rec in binary_records(d['Regions6/Data'],11):
 b=rec['body'];n=struct.unpack_from('<I',b,18)[0];pos=22+n;count=struct.unpack_from('<I',b,pos)[0];pos+=4
 points=[tuple(v*UNIT for v in struct.unpack_from('<2d',b,pos+16*i)) for i in range(count)]
 rs.append(dict(layer=b[0],net=struct.unpack_from('<H',b,3)[0],g=Polygon(points)))
for rec in binary_records(d['Tracks6/Data'],4):
 b=rec['body'];x1,y1,x2,y2,w=[v*UNIT for v in struct.unpack_from('<5i',b,13)]
 ts.append(dict(layer=b[0],net=struct.unpack_from('<H',b,3)[0],g=LineString([(x1,y1),(x2,y2)]).buffer(w/2),a=[x1,y1],b=[x2,y2]))
for rec in binary_records(d['Vias6/Data'],3):
 b=rec['body'];x,y,size,hole=[v*UNIT for v in struct.unpack_from('<4i',b,13)]
 vs.append(dict(net=struct.unpack_from('<H',b,3)[0],x=x,y=y,size=size,hole=hole,g=Point(x,y).buffer(size/2)))
checks=[]
def ck(ok,s):checks.append(dict(check=s,passed=bool(ok)));assert ok,s
ck(len(ps)==78 and len(cs)==2 and len(nets)==51,'78 pads, two components and 51 distinct net labels')
refhash=json.loads((H/'reference/anton_connector.json').read_text())['source_sha256']
refpath=R/'script/anton_zif_20260923/reference/DSUBtoZIF_20250306'
ck(all(hashlib.sha256((refpath/n).read_bytes()).hexdigest()==v for n,v in refhash.items()),'Anton reference remains unchanged')
allg={};padmap={}
for p in ps:
 x,y,sx,sy=[v*UNIT for v in p['coords'][:4]]
 p['g']=box(x-sx/2,y-sy/2,x+sx/2,y+sy/2) if p['shape']==2 else Point(x,y).buffer(sx/2)
 ref=cs[p['component']]['SOURCEDESIGNATOR'];padmap[f"{ref}.{p['number']}"]=p
for ni,n in enumerate(nets):
 for lay in (1,32):
  shapes=[p['g'] for p in ps if p['net']==ni and p['layer'] in (lay,74)]+[r['g'] for r in rs if r['net']==ni and r['layer']==lay]+[t['g'] for t in ts if t['net']==ni and t['layer']==lay]+[v['g'] for v in vs if v['net']==ni]
  allg[ni,lay]=unary_union(shapes)
 if n['NAME'].startswith('DSUB_'):
  dp=int(n['NAME'].split('_')[1]);ap=plan['source_mapping'][str(dp)]
  ck(padmap[f'A.{ap}']['net']==ni and padmap[f'J1.{dp}']['net']==ni,f'Anton map DSUB {dp} - ZIF {ap}')
  islands=[]
  for l in (1,32):
   g=allg[ni,l]
   if not g.is_empty:
    for shape in ([g] if g.geom_type=='Polygon' else list(g.geoms)):islands.append((l,shape))
  parent=list(range(len(islands)))
  def root(i):
   while parent[i]!=i:i=parent[i]
   return i
  bridges=[p['g'] for p in ps if p['net']==ni and p['layer']==74]+[v['g'] for v in vs if v['net']==ni]
  for bridge in bridges:
   touched=[i for i,(l,g) in enumerate(islands) if bridge.intersects(g)]
   for i in touched[1:]:parent[root(i)]=root(touched[0])
  ck(len({root(i) for i in range(len(islands))})==1,f"{n['NAME']}: all copper joined through physical plated bridges")
 else:ck(sum(p['net']==ni for p in ps)==1 and not any(t['net']==ni for t in ts),n['NAME']+': unconnected odd finger')
minimum=(999,None)
for l in (1,32):
 for i in range(len(nets)):
  for j in range(i+1,len(nets)):
   a,b=allg[i,l],allg[j,l]
   if a.is_empty or b.is_empty:continue
   gap=a.distance(b)
   if gap<minimum[0]:minimum=(gap,[l,nets[i]['NAME'],nets[j]['NAME']])
ck(minimum[0]>.0707,'No same-layer signal shorts; staggered-finger minimum clearance retained')
outline=Polygon(plan['outline'])
ck(all(outline.buffer(3e-6).covers(g) for g in allg.values() if not g.is_empty),'Signal copper contained by board outline')
ck(len(vs)==12 and all(abs(v['y']-23)<3e-6 for v in vs),'12 vias confined to transition row, away from mating fingers')
ck(len([p for p in ps if p['coords'][8]>0])==27,'25 signal holes and two boardlock holes')
native=(OUT/'native_validation.txt').read_text()
ck('DRC_RETURNED_TRUE' in native and 'REBUILT_CONNECTION_COUNT=0' in native,'Native Altium DRC and rebuilt connectivity pass after save/reopen')
ck('PAD_PASTE_ENABLED=0' in native,'Native audit confirms all pad paste disabled')
ck(not any(r['layer'] in (35,36) for r in rs) and not any(t['layer'] in (35,36) for t in ts),'No explicit paste-layer geometry including via apertures')
ck(all(v['body'][66]==2 and struct.unpack_from('<i',v['body'],54)[0]*UNIT<-.99 and struct.unpack_from('<i',v['body'],242)[0]*UNIT<-.99 for v in binary_records(d['Vias6/Data'],3)),'Saved via mask overrides close every aperture on both faces')
ck(len(d['Connections6/Data'])==0,'Saved PCB has zero outstanding connections')
report={'checks':checks,'minimum_gap_mm':minimum[0],'minimum_pair':minimum[1],'native_drc_performed':True,'pcb_sha256':hashlib.sha256(P.read_bytes()).hexdigest()}
(OUT/'geometry_validation.json').write_text(json.dumps(report,indent=2)+'\n')
fig,axes=plt.subplots(1,3,figsize=(15,8),gridspec_kw={'width_ratios':[1,1,1.1]},facecolor='#f4f3ef')
for ax,l,title in zip(axes[:2],(1,32),('Top copper / contact face','Bottom copper / same XY view')):
 ax.add_patch(Patch(plan['outline'],fc='#e3bb59',ec='#363b32',lw=1.2))
 for (i,layer),g in allg.items():
  if layer==l and not g.is_empty:
   for shape in ([g] if g.geom_type=='Polygon' else list(g.geoms)):ax.add_patch(Patch(list(shape.exterior.coords),fc='#bc7230' if l==1 else '#416e97',ec='none'))
 for p in ps:
  if p['coords'][8]:ax.add_patch(Circle((p['coords'][0]*UNIT,p['coords'][1]*UNIT),p['coords'][8]*UNIT/2,fc='white',ec='#5b5b52',lw=.4))
 for v in vs:ax.add_patch(Circle((v['x'],v['y']),v['hole']/2,fc='white',ec='none'))
 ax.add_patch(Rectangle((7.7,36),15.6,4,fill=False,ec='#8255a0',ls='--',lw=1))
 ax.add_patch(Rectangle((0,0),31,15,fill=False,ec='#8255a0',ls='--',lw=1))
 ax.set_aspect('equal');ax.set_xlim(-2,33);ax.set_ylim(-2,44);ax.set_title(title,fontsize=12,weight='bold');ax.set_xlabel('X (mm)');ax.set_ylabel('Y (mm)');ax.grid(alpha=.12)
 ax.text(15.5,41.2,'51 x 0.30 mm / 15.60 mm mating width',ha='center',fontsize=8)
 ax.text(15.5,1,'25-pin Micro-D + 2 boardlocks',ha='center',fontsize=8)
axes[2].axis('off');axes[2].set_title('Reference pin mapping',loc='left',fontsize=12,weight='bold')
axes[2].text(0,.94,'DSUB 1-13  ->  ZIF 2, 6, ... 50\nDSUB 14-25 ->  ZIF 4, 8, ... 48\nOdd ZIF contacts: not connected',va='top',fontsize=11,linespacing=1.8)
axes[2].text(0,.69,'40 mm overall length (provisional)\n31 mm connector-base width\n15.6 mm mating-tail width\n25 plated signal holes: 0.7112 mm\nBoardlocks: 2.69 mm / 24.51 mm pitch',va='top',fontsize=10,linespacing=1.8)
axes[2].text(0,.38,'Two copper layers, 18 um each\n45 um PI core + adhesive\n25 um coverlay each face\nBack stiffener boundaries: dashed\nFinished mating end: 0.20 +/- 0.03 mm\nConnector area: 1.6 mm finished (provisional)',va='top',fontsize=9,linespacing=1.8)
axes[2].text(0,.07,'NATIVE ALTIUM DRC: 0 AFTER SAVE / REOPEN\nSaved copper connectivity checked independently.\nNo fabrication release.',va='top',fontsize=9,weight='bold',color='#38654b')
fig.suptitle('ZIF contact tail to 25-pin Micro-D adapter',fontsize=19,weight='bold',y=.98);fig.tight_layout(rect=[0,0,1,.94])
fig.savefig(OUT/'ZIF_to_DSUB25_draft.png',dpi=160);plt.close(fig)
print(json.dumps({'passed_checks':len(checks),'minimum_gap_mm':minimum[0],'review':str(OUT/'ZIF_to_DSUB25_draft.png')}))
