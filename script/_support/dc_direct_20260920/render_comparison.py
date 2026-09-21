from pathlib import Path
import json,math,hashlib
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');D=P/'docs'
old=json.loads((H/'baseline_native.json').read_text());n=json.loads((H/'native_render_snapshot.json').read_text());S=2;BG='#101820';BOARD='#14242d';WHITE='#e4edf2';GREY='#354b56'
im=Image.new('RGB',(1850*S,1640*S),BG);d=ImageDraw.Draw(im)
def font(sz,bold=False):return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf',round(sz*S))
def text(x,y,s,size=20,color=WHITE,bold=False):d.text((x*S,y*S),s,font=font(size,bold),fill=color)
text(40,24,'DC를 중앙으로 모으고, R1 바이어스를 맨 바깥으로',32,bold=True)
text(40,80,'원본 PcbDoc 저장 좌표 · 위에서 본 공통 좌표 · RF와 GND 구리는 숨김',20,'#a4bdcb')
text(40,123,'변경 전 · L4',25,'#cbb4d9',True);text(650,123,'변경 후 · L4',25,'#ce99f2',True);text(1260,123,'변경 후 · L2',25,'#62c3e6',True)
bounds=(2.2,23.0,17.3,49.3);scale=36.5
for col,(data,layer,color) in enumerate([(old,4,'#bba1c9'),(n,4,'#ce99f2'),(n,2,'#62c3e6')]):
 ox=40+col*610;oy=170;xmin,ymin,xmax,ymax=bounds
 cw=round((xmax-xmin)*scale*S);ch=round((ymax-ymin)*scale*S);canvas=Image.new('RGB',(cw,ch),BOARD);dr=ImageDraw.Draw(canvas)
 def xy(x,y):return ((x-xmin)*scale*S,(ymax-y)*scale*S)
 def circle(x,y,r,c):
  a,b=xy(x,y);r*=scale*S;dr.ellipse((a-r,b-r,a+r,b+r),fill=c)
 def label(x,y,s,sz=13,c=WHITE):dr.text(xy(x,y),s,font=font(sz,True),fill=c,anchor='mm')
 def pad(p,c):
  if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:circle(p['x'],p['y'],p['size_x']/2,c)
  else:
   a=math.radians(p['rotation']);co,si=math.cos(a),math.sin(a)
   pts=[(p['x']+dx*co-dy*si,p['y']+dx*si+dy*co) for dx,dy in [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),(p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]];dr.polygon([xy(*p0) for p0 in pts],fill=c)
  if p['hole']:circle(p['x'],p['y'],p['hole']/2,BG)
 tracks=[t for t in data['tracks'] if t['layer']==layer and t['net'].startswith('ZIF')];nets={t['net'] for t in tracks}
 for p in data['pads']:pad(p,GREY)
 for t in tracks:dr.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])],fill=color,width=max(S,round(t['width']*scale*S)))
 for p in data['pads']:
  if p['net'] in nets:pad(p,color)
 for v in data['vias']:
  circle(v['x'],v['y'],v['diameter']/2,color if v['net'] in nets else '#ae9973');circle(v['x'],v['y'],v['hole']/2,BG)
 dr.rectangle((*xy(7.6,44.65),*xy(11.9,40.35)),fill='#1d313b',outline='#6c8795',width=S)
 label(9.75,42.6,'QD',19);label(9.75,41.7,'4.3 mm',12,'#9fb4c0')
 label(15.2,29,'R1 / C1',13,'#d7bd87');label(16.1,37,'SMP2',13,'#8da5b1');label(16.1,24.5,'SMP1',13,'#8da5b1')
 if col==0:
  dr.rounded_rectangle((*xy(12.45,32.5),*xy(15.0,28.5)),radius=5*S,outline='#e99b88',width=2*S)
 else:
  dr.rectangle((*xy(6.0,30.0),*xy(12.9,26.5)),outline='#76bead',width=S)
 if col==1:
  label(14.9,32.35,'ZIF21 → R1',12,'#e3cfff')
 for p in data['pads']:
  if p['component']=='Q1' and p['number'] in ['2','3']:
   label(11.2,p['y'],p['number'],12)
 dr.rectangle((0,0,cw-1,ch-1),outline='#4a626e',width=S);im.paste(canvas,(ox*S,oy*S))
text(40,1160,'비아 사이를 지나던 우회',21,'#e99b88',True)
text(650,1160,'R1으로 가는 선만 오른쪽 분기',21,'#ce99f2',True)
text(1260,1160,'L4와 같은 중앙 XY 통로 사용',21,'#62c3e6',True)
text(40,1245,'ZIF 핀 재배정',23,bold=True)
text(40,1291,'17 → QD 3       19 → QD 2       21 → R1 DC 바이어스',23)
text(40,1346,'중앙 평행 구간: 선폭 0.125 mm / 피치 0.6 mm / 구리 간격 약 0.475 mm',22,'#a7c8d6')
text(40,1401,'RF·부품·홀 위치 유지 / 비아 추가 0개 / DC 꺾임은 모두 45° 이하',22,'#a7c8d6')
text(40,1456,'저장 후 다시 열어 DRC: 13개 규칙, 위반 0건',23,'#84d8b0',True)
text(40,1541,'같은 층의 간격을 검사하며, 다른 층의 배선은 겹쳐 사용합니다. 관통 비아는 두 층 모두에서 피합니다.',19,'#9eb6c4')
text(40,1590,'현재 PCB SHA-256  '+n['source_sha256'][:24]+'…',15,'#7894a3')
assert hashlib.sha256(Path(n['source']).read_bytes()).hexdigest()==n['source_sha256']
im.resize((1850,1640),Image.Resampling.LANCZOS).save(D/'DC_direct_comparison.png');print(D/'DC_direct_comparison.png')
