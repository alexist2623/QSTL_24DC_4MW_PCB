from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');D=P/'docs'
n=json.loads((H/'native_render_snapshot.json').read_text());new={'SMP5','R5','C5','SMP6','R6','C6'}
im=Image.new('RGB',(1100,1500),'#101821');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16);title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',29)
d.text((40,22),'Current R / C / SMP placement',font=title,fill='white');d.text((40,66),'Top-view projection. SMP: Top. R0603 / C0402: Bottom.',font=font,fill='#c2d2da');d.text((40,98),'Amber: new placement-only parts; their signal pads are unassigned.',font=small,fill='#ffd483')
scale=47.;x0=92;y0=172;top=50.7;bottom=24.4
def xy(x,y):return x0+x*scale,y0+(top-y)*scale
def corners(p):
 a=math.radians(p['rotation']);ca,sa=math.cos(a),math.sin(a)
 return [(p['x']+dx*ca-dy*sa,p['y']+dx*sa+dy*ca) for dx,dy in [(-p['size_x']/2,-p['size_y']/2),(p['size_x']/2,-p['size_y']/2),(p['size_x']/2,p['size_y']/2),(-p['size_x']/2,p['size_y']/2)]]
d.rectangle((*xy(0,top),*xy(19.5,bottom)),fill='#16342e',outline='#87a39a',width=2)
for yy in range(int(xy(9.75,top)[1]),int(xy(9.75,bottom)[1]),16):d.line((xy(9.75,top)[0],yy,xy(9.75,top)[0],yy+8),fill='#79958d',width=1)
d.text((xy(9.75,top)[0],145),'X = 9.75 mm',font=small,fill='#adc3b9',anchor='mm')
for b in n['bodies']:
 if not b['points'] or not all(bottom<y<top for x,y in b['points']):continue
 d.polygon([xy(*p) for p in b['points']],outline='#c99439' if b['component'] in new else '#537369',width=2)
for p in n['pads']:
 if not bottom<p['y']<top:continue
 color='#ffc56b' if p['component'] in new else '#c4b780'
 if p['net'] and p['net'].startswith('MW'):color='#e985c7'
 if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:
  x,y=xy(p['x'],p['y']);r=p['size_x']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill=color)
 else:d.polygon([xy(*v) for v in corners(p)],fill=color)
 if p['hole']:
  x,y=xy(p['x'],p['y']);r=p['hole']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='#08191b')
for v in n['vias']:
 if not bottom<v['y']<top:continue
 x,y=xy(v['x'],v['y']);r=v['hole']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='#08191b')
labelpos={'SMP1':(16.4,26.0),'SMP5':(3.1,26.0),'SMP2':(16.4,33.1),'SMP6':(3.1,33.1),'SMP3':(16.4,49.9),'SMP4':(3.1,49.9),'R1':(13.65,32.6),'C1':(15.2,29.15),'R5':(5.85,32.6),'C5':(4.3,29.15),'R2':(16.,44.75),'C2':(17.55,41.2),'R6':(3.5,44.75),'C6':(1.95,41.2),'R3':(13.65,48.8),'C3':(15.2,45.45),'R4':(5.85,48.8),'C4':(4.3,45.45)}
for name,(x,y) in labelpos.items():
 d.text(xy(x,y),name,font=font,fill='#ffd483' if name in new else '#e6eee9',anchor='mm')

d.rectangle((*xy(7.6,44.65),*xy(11.9,40.35)),fill='#1c3834',outline='#78958a',width=2)
d.text(xy(9.75,42.65),'QD24',font=font,fill='white',anchor='mm');d.text(xy(9.75,42.05),'4.3 x 4.3 mm',font=small,fill='#b7cdc3',anchor='mm')
d.text((40,1440),'SMP1/R1/C1 -> SMP5/R5/C5     |     SMP2/R2/C2 -> SMP6/R6/C6',font=font,fill='#ffd483')
d.text((40,1472),'Current native PCB placement. R pads lie on the RF path; existing pin assignments retained.',font=small,fill='#b5c7cf')
im.save(D/'placement_detail.png')
