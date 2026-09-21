"""Read-only DC routing export with native-coordinate detail views."""
from pathlib import Path
import json, math, hashlib, importlib.util, collections
from PIL import Image, ImageDraw, ImageFont

H=Path(__file__).resolve().parent;W=H.parent
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB')
SOURCE=P/'QSTL_24DC_4MW_PCB.PcbDoc';DEST=P/'docs/DC_only.png'
spec=importlib.util.spec_from_file_location('native_reader',W/'zif_revision_v2/render_native_layout.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);reader.SOURCE=SOURCE
n=reader.read_native()
isdc=lambda net:bool(net and net.startswith('ZIF'))
tracks=[t for t in n['tracks'] if isdc(t['net'])]
vias=[v for v in n['vias'] if isdc(v['net'])]
nets={t['net'] for t in tracks}
assert len(nets)==24 and {t['layer'] for t in tracks}=={1,2,4}
assert len(vias)==49
SS=2;BG='#101820';PCB='#14232c';FAINT='#30424d';CYAN='#62c3e6';ORANGE='#efb66c'
BIAS={'ZIF21':'#ce99f2','ZIF23':'#62c3e6','ZIF25':'#62c3e6','ZIF02':'#ce99f2'}
L2NETS={f'ZIF{k:02d}' for k in [4,6,8,10,12,16,18,20,22,24,25,23]}
def color(net):return CYAN if net in L2NETS else '#ce99f2'
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf',round(size*SS))
im=Image.new('RGB',(1700*SS,1940*SS),BG);d=ImageDraw.Draw(im)
def text(x,y,s,size=20,fill='#cbdde7',bold=False):d.text((x*SS,y*SS),s,font=font(size,bold),fill=fill)
text(40,22,'중앙으로 모은 DC 배선',32,'#ffffff',True)
text(40,73,'위에서 본 좌표 · L2 / L4: 중앙 구간 12개씩 중첩 · ZIF 패드 인출부: Top',20,'#a6bdca')
text(40,110,'전체 경로',21,'#ffffff',True)
text(720,110,'QD · R 부근 확대',21,'#ffffff',True)
text(720,1122,'ZIF 진입부 확대',21,'#ffffff',True)

def panel(origin,bounds,scale,mode):
 xmin,ymin,xmax,ymax=bounds
 size=(round((xmax-xmin)*scale*SS),round((ymax-ymin)*scale*SS))
 canvas=Image.new('RGB',size,PCB);dr=ImageDraw.Draw(canvas)
 def xy(x,y):return ((x-xmin)*scale*SS,(ymax-y)*scale*SS)
 def inside(x,y,pad=0):return xmin-pad<=x<=xmax+pad and ymin-pad<=y<=ymax+pad
 def circle(x,y,r,fill,outline=None):
  a,b=xy(x,y);rr=r*scale*SS;dr.ellipse((a-rr,b-rr,a+rr,b+rr),fill=fill,outline=outline,width=SS)
 def pad(p,fill):
  if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:circle(p['x'],p['y'],p['size_x']/2,fill)
  else:dr.polygon([xy(*v) for v in reader.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=fill)
  if p['hole']:circle(p['x'],p['y'],p['hole']/2,PCB)
 def label(x,y,s,fill='#d4e2eb',sz=17,anchor='mm',background=True):
  pt=xy(x,y);f=font(sz,True)
  if background:
   b=dr.textbbox(pt,s,font=f,anchor=anchor);dr.rounded_rectangle((b[0]-3*SS,b[1]-2*SS,b[2]+3*SS,b[3]+2*SS),radius=2*SS,fill=BG)
  dr.text(pt,s,font=f,fill=fill,anchor=anchor)

 # Context pads only; RF and GND copper are deliberately absent.
 for p in n['pads']:
  if inside(p['x'],p['y'],1) and not isdc(p['net']):pad(p,FAINT)
 for c in n['components']:
  if c['designator'] in ['R1','R2','R3','R4'] and inside(c['x'],c['y'],2):
   dr.polygon([xy(*v) for v in reader.corners(c['x'],c['y'],1.6,.8,c['rotation'])],fill='#283c47',outline='#576b77')
 for t in tracks:
  fill=ORANGE if t['layer']==1 else (CYAN if t['layer']==2 else '#ce99f2')
  dr.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])],fill=fill,width=max(SS,round(t['width']*scale*SS)))
 for p in n['pads']:
  if isdc(p['net']) and inside(p['x'],p['y'],1):pad(p,ORANGE if p['component']=='J1' else color(p['net']))
 for v in vias:
  if inside(v['x'],v['y'],.5):
   circle(v['x'],v['y'],v['diameter']/2,color(v['net']));circle(v['x'],v['y'],v['hole']/2,BG)

 if mode in ['overview','detail']:
  dr.rectangle((*xy(7.6,44.65),*xy(11.9,40.35)),fill='#182a34',outline='#4c6775',width=SS)
  label(9.75,42.85,'QD',sz=22 if mode=='detail' else 18,background=False)
  label(9.75,42.26,'4.3 × 4.3 mm',fill='#809daa',sz=14 if mode=='detail' else 11,background=False)
  if mode=='detail':
   for p in n['pads']:
    if p['component']!='Q1' or not isdc(p['net']):continue
    k=int(p['number']);x,y=p['x'],p['y']
    if 2<=k<=8:x=11.50
    elif 10<=k<=16:
     label(x,39.48,str(k),BG,11,background=False)
     continue
    elif 17<=k<=23:x=8.0
    label(x,y,str(k),color(p['net']),16,background=False)
   label(5.85,48.75,'R4 · ZIF02',BIAS['ZIF02'],18)
   label(13.65,48.75,'R3 · ZIF25',BIAS['ZIF25'],18)
   label(16.9,44.65,'R2 · ZIF23',BIAS['ZIF23'],18)
   label(16.2,31.55,'R1 · ZIF21',BIAS['ZIF21'],18)
  else:
   for name in ['R1','R2','R3','R4']:
    p=next(p for p in n['pads'] if p['component']==name and p['number']=='2')
    label(p['x'],p['y']+1.1,name,color(p['net']),14)
   label(13.5,4.5,'J1 / ZIF',ORANGE,18)
 if mode=='zif':
  for p in n['pads']:
   if p['component']=='J1' and isdc(p['net']):
    label(p['x'],4.0 if int(p['number'])%2 else 5.38,p['number'],ORANGE,17,background=False)
  label(6.05,4.7,'J1 / ZIF',sz=19,background=False)
  label(10.25,8.85,'→ L2 / L4',sz=16,fill=CYAN)
 dr.rectangle((0,0,size[0]-1,size[1]-1),outline='#39515e',width=SS)
 im.paste(canvas,(round(origin[0]*SS),round(origin[1]*SS)))

panel((40,150),(0,0,19.5,50),31,'overview')
panel((720,150),(0,29,19.5,49.3),47,'detail')
panel((720,1160),(0,.1,11.9,9.3),77,'zif')
text(40,1730,'하늘색: L2 DC_A / 중앙 주 배선 12개',20,CYAN)
text(40,1771,'보라색: L4 DC_B / 중앙 주 배선 12개',20,'#ce99f2')
text(40,1812,'주황색: Top 패드 인출부',20,ORANGE)
text(40,1853,'중앙 평행 구간: 구리 간격 0.475 mm',18,'#839fac')
text(40,1900,'저장된 PcbDoc의 실제 배선 좌표 · RF 배선과 GND 면은 숨김',17,'#9db5c3')
text(1235,1900,'SHA-256  '+n['source_sha256'][:16]+'…',14,'#7894a3')
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==n['source_sha256']
im.resize((1700,1940),Image.Resampling.LANCZOS).save(DEST)
report={'source':str(SOURCE),'source_sha256':n['source_sha256'],'image':str(DEST),'dc_nets':len(nets),'tracks_by_layer':dict(collections.Counter(t['layer'] for t in tracks)),'dc_vias':len(vias),'view':'top coordinates with QD/R and ZIF detail views','design_modified':False}
(H/'DC_only_export.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
