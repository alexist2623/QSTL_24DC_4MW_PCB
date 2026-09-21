"""Saved native DC paths around the two large GND mounting holes."""
from pathlib import Path
import json,hashlib,math
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB';D=P/'docs'
n=json.loads((H/'native_render_snapshot.json').read_text());audit=json.loads((D/'DC_simplified.json').read_text())
assert n['source_sha256']==audit['pcb_sha256']==hashlib.sha256((P/'QSTL_24DC_4MW_PCB.PcbDoc').read_bytes()).hexdigest()
S=2;BG='#101820';BOARD='#172a34';MUTED='#435b68';WHITE='#dce9ef'
im=Image.new('RGB',(1640*S,920*S),BG);d=ImageDraw.Draw(im)
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/malgunbd.ttf' if bold else 'C:/Windows/Fonts/malgun.ttf',size*S)
def text(x,y,s,size=20,color=WHITE,bold=False,anchor='lt'):d.text((x*S,y*S),s,font=font(size,bold),fill=color,anchor=anchor)
text(40,24,'GND 홀 사이 DC 배선 · 불필요한 꺾임과 층 전환 제거',30,bold=True)
text(40,77,'저장된 PcbDoc 좌표 | 두 층의 중앙 배선은 같은 XY 위치를 사용 | 위에서 본 좌표',20,'#a8c0cd')
for i,layer in enumerate((2,4)):
    ox=40+i*810;oy=155;scale=37;left=0;right=19.5;top=24;bottom=7.6;color='#62c3e6' if layer==2 else '#ce99f2'
    text(ox,121,f'L{layer} DC · 12개 넷',23,color,True)
    size=(round((right-left)*scale*S),round((top-bottom)*scale*S));panel=Image.new('RGB',size,BOARD);dr=ImageDraw.Draw(panel)
    def xy(x,y):return ((x-left)*scale*S,(top-y)*scale*S)
    def circ(x,y,r,fill):
        xx,yy=xy(x,y);rr=r*scale*S;dr.ellipse((xx-rr,yy-rr,xx+rr,yy+rr),fill=fill)
    for p in n['pads']:
        if p['layer']==74:
            circ(p['x'],p['y'],p['size_x']/2,MUTED);circ(p['x'],p['y'],p['hole']/2,BG)
    for v in n['vias']:circ(v['x'],v['y'],v['diameter']/2,MUTED);circ(v['x'],v['y'],v['hole']/2,BG)
    for t in n['tracks']:
        if t['layer']==layer:dr.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])],fill=color,width=max(2,round(t['width']*scale*S)))
    for x in (3.425,16.075):dr.text(xy(x,18.09),'GND',font=font(17,True),fill='#9bb2be',anchor='mm')
    dr.text(xy(9.75,22.5),'0.475 mm',font=font(20,True),fill=WHITE,anchor='mm')
    dr.text(xy(3.55,21.2),'간격 ≥ 0.36 mm',font=font(16),fill='#b8cbd4',anchor='mm')
    dr.text(xy(16.0,21.2),'간격 ≥ 0.56 mm',font=font(16),fill='#b8cbd4',anchor='mm')
    im.paste(panel,(ox*S,oy*S));text(ox,oy+(top-bottom)*scale+18,'추가 층 전환 비아 0개 · DC 선폭 0.125 mm',19,color)
text(40,838,'ZIF23 → R3 바이어스 / ZIF25 → R2 바이어스 · 회로도와 PCB 함께 변경',22,bold=True)
text(40,886,'실제 구리 연결 37개 넷 정상 · 저장 후 미연결 0개 · DRC 위반 0건',18,'#8bcbaa')
text(1600,886,'SHA-256 '+n['source_sha256'][:16]+'…',14,'#7896a6',anchor='rt')
im.resize((1640,920),Image.Resampling.LANCZOS).save(D/'DC_simplified.png')
print(D/'DC_simplified.png')
