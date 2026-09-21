from pathlib import Path
import json,math,hashlib
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');D=P/'docs'
n=json.loads((H/'native_render_snapshot.json').read_text());S=2;BG='#101820';BOARD='#14242d';GREY='#344b58';WHITE='#e4edf2'
im=Image.new('RGB',(1800*S,1510*S),BG);d=ImageDraw.Draw(im)
def font(sz,bold=False):return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf',sz*S)
def text(x,y,s,size=20,color=WHITE,bold=False,anchor='lt'):d.text((x*S,y*S),s,font=font(size,bold),fill=color,anchor=anchor)
text(40,25,'DC는 중앙으로 · 두 배선층의 XY 공간을 함께 사용',34,bold=True)
text(40,80,'저장된 Altium 배선 좌표 | 모든 배선도는 위에서 본 공통 좌표 | GND 면은 숨김',21,'#a4bdcb')
text(40,145,'QD 면 → 반대 면',26,bold=True)
stack=[('L6 · Bottom','RF / QD · R · C','#edbd65'),('L5','GND','#72c39c'),('L4','DC_B · 12개','#ce99f2'),('L3','GND','#72c39c'),('L2','DC_A · 12개','#62c3e6'),('L1 · Top','GND / ZIF · SMP','#72c39c')]
for j,(a,b,c) in enumerate(stack):
 y=201+j*106;d.rounded_rectangle((40*S,y*S,364*S,(y+88)*S),radius=8*S,fill='#1b2d36',outline=c,width=2*S)
 text(59,y+12,a,20,c,True);text(59,y+45,b,23,WHITE,True)
text(40,886,'RF',22,'#edbd65',True);text(40,924,'0.214 mm / 곡선 코너',20)
text(40,985,'DC',22,'#62c3e6',True);text(40,1023,'0.125 mm / 45° 코너',20)
text(40,1085,'ZIF Top 인출부',20,'#b7c9d3',True);text(40,1123,'짧은 0.15 mm 배선 유지',19)
text(40,1162,'중앙 DC 간격: 0.475 mm',19,'#9bc8d8')
text(40,1210,'저장 후 다시 열어 검사',19,'#a4bdcb');text(40,1249,'DRC 13개 규칙 · 위반 0',21,'#84d8b0',True)
colors={32:'#edbd65',4:'#ce99f2',2:'#62c3e6'}
def corners(p):
 a=math.radians(p['rotation']);co,si=math.cos(a),math.sin(a)
 return [(p['x']+dx*co-dy*si,p['y']+dx*si+dy*co) for dx,dy in [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),(p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]]
for col,layer in enumerate([32,4,2]):
 ox=414+col*454;oy=202;scale=18.;color=colors[layer]
 text(ox,148,{32:'L6 · RF 6개',4:'L4 · DC' ,2:'L2 · DC'}[layer],25,color,True)
 def xy(x,y):return ((ox+x*scale)*S,(oy+(67.9-y)*scale)*S)
 def circ(x,y,r,fill):
  xx,yy=xy(x,y);rr=r*scale*S;d.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill=fill)
 def pad(p,fill):
  if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:circ(p['x'],p['y'],p['size_x']/2,fill)
  else:d.polygon([xy(*p0) for p0 in corners(p)],fill=fill)
  if p['hole']:circ(p['x'],p['y'],p['hole']/2,BG)
 d.rectangle((*xy(0,67.9),*xy(19.5,0)),fill=BOARD,outline='#57727e',width=S)
 tracks=[t for t in n['tracks'] if t['layer']==layer];arcs=[a for a in n['arcs'] if a['layer']==layer];nets={t['net'] for t in tracks}
 for p in n['pads']:pad(p,GREY)
 for t in tracks:d.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])],fill=color,width=max(S,round(t['width']*scale*S)))
 for a in arcs:
  sw=(a['end_angle']-a['start_angle'])%360;steps=max(10,math.ceil(sw))
  d.line([xy(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sw*i/steps)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sw*i/steps))) for i in range(steps+1)],fill=color,width=max(S,round(a['width']*scale*S)))
 for p in n['pads']:
  if p['net'] in nets:pad(p,color)
 for v in n['vias']:
  if v['net'] in nets:circ(v['x'],v['y'],v['diameter']/2,color);circ(v['x'],v['y'],v['hole']/2,BG)
 d.rectangle((*xy(7.6,44.65),*xy(11.9,40.35)),fill='#1c313c',outline='#688491',width=S)
 d.text(xy(9.75,42.5),'QD',font=font(16,True),fill=WHITE,anchor='mm')
 text(ox+9.75*scale,oy+(67.9-64)*scale,'19.5 × 67.9 mm',17,'#95afbc',anchor='mt')
 text(ox+9.75*scale,oy+(67.9-61.5)*scale,'SMP·QD·기구 홀 유지',16,'#7898a9',anchor='mt')
 if layer==32:
  for i in range(1,7):
   c=next(c for c in n['components'] if c['designator']==f'SMP{i}')
   d.text(xy(c['x'],c['y']+2.5),f'SMP{i}',font=font(13,True),fill=WHITE,anchor='mm')
 else:d.text(xy(9.75,57.8),'중앙 구간 서로 겹침',font=font(16),fill=color,anchor='mm')
 text(ox+9.75*scale,1450,{32:'SMP → C → R 패드 → QD',4:'중앙 12개 / 층 전환 없음',2:'중앙 12개 / 층 전환 없음'}[layer],16,color,anchor='mt')
assert hashlib.sha256((P/'QSTL_24DC_4MW_PCB.PcbDoc').read_bytes()).hexdigest()==n['source_sha256']
im.resize((1800,1510),Image.Resampling.LANCZOS).save(D/'Routing_layers.png')
print(str(D/'Routing_layers.png'))
