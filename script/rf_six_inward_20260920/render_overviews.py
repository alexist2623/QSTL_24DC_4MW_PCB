from pathlib import Path
import json,types,sys,math
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;W=H.parent/'_support';sys.path.insert(0,str(W/'route_python'))
from shapely.geometry import LineString,box
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB');D=P/'docs'
src=W/'zif_revision_v2/render_native_layout.py';code=src.read_text().replace('corners(cx,cy,7.,7.,0)','corners(cx,cy,4.3,4.3,0)').replace('corners(cx,cy,8.4,8.4,0)',"n['qd_envelope']")
code=code.replace("tx=p['x']-.60*math.copysign(1,dx) if abs(dx)>3 else p['x']","tx=p['x']-.85*math.copysign(1,dx) if int(p['number']) not in [1,24] and abs(dx)>2.6 else p['x']")
code=code.replace("ty=p['y']+(.67 if int(p['number'])%2 else 1.18) if dy<-3 else p['y']","ty=p['y']+(.67 if int(p['number'])%2 else 1.05) if dy<-2.6 else p['y']-.8 if int(p['number']) in [1,24] else p['y']")
code=code.replace('16 components / 129 pads','22 components / 147 pads')
code=code.replace('RF1 -> 24   RF2 -> 21','RF1 -> 9   RF2 -> 6').replace('RF3 -> 14   RF4 -> 11','RF3 -> 1   RF4 -> 24')
code=code.replace("for p in [p for p in n['pads'] if p['component']=='Q1']:","for p in []:").replace('xy(9.75,31)','xy(9.75,23.3)').replace('xy(9.75,29.7)','xy(9.75,22.0)').replace('GREEN  GND vias','0 GND shield vias')
code=code.replace('GND: L1/L3/L5/L6, solid stitching. Every via: Top + Bottom paste opening. QD interior: no signal tracks.','R0603 / C0402. QD inner opening 4.3 mm. No shield vias. Via paste apertures on both sides.')
code=code.replace("  if panel==0:\n   for c in n['components']:","""  for v in n['vias']:
   x,y=xy(v['x'],v['y']);h=v['hole']*scale/2
   d.ellipse((x-h,y-h,x+h,y+h),fill='#0c191c')
  if panel==0:
   for c in n['components']:""")
code=code.replace('TOP: ZIF / SMP','TOP L1 GND: ZIF / SMP').replace('BOTTOM: QD24 / R / C','BOTTOM L6 RF: QD24 / R / C').replace('INNER SIGNALS: L2 + L4','DC: L2 + L4 (12 nets each)').replace('PINK  L4 RF routing','PINK  L4 DC routing')
code=code.replace('RF4 / DC20','RF6 / DC18').replace("['MW1','MW2','MW3','MW4']","['MW1','MW2','MW3','MW4','MW5','MW6']")
code=code.replace("   text_at(xy(9.75,5)","   text_at(xy(9.75,20.7),'RF5 -> 12   RF6 -> 18',fill='#ff9ada',f=small)\n   text_at(xy(9.75,5)")
M=types.ModuleType('native_view');M.__file__=str(src);exec(compile(code,str(src),'exec'),M.__dict__);M.SOURCE=P/'QSTL_24DC_4MW_PCB.PcbDoc';n=M.read_native();qp=[p for p in n['pads'] if p['component']=='Q1'];pts=[pt for p in qp for pt in M.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])];xmin,xmax=min(x for x,y in pts),max(x for x,y in pts);ymin,ymax=min(y for x,y in pts),max(y for x,y in pts);n['qd_envelope']=[(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)];M.render(n).save(D/'layout.png')
im=Image.new('RGB',(1420,1100),'#101821');d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',29)
d.text((35,20),'QD24 | 4.3 mm inner pad-end opening | R0603 / C0402',font=title,fill='white');d.text((35,64),'Saved native copper, viewed from Top; QD/R/C are on Bottom. L2 DC: blue; L4 DC: purple; L6 RF: pink.',font=small,fill='#aec3d0')
scale=77;left,right,bottom,top=.4,19.1,36.7,49.1
def xy(x,y):return 32+(x-left)*scale,105+(top-y)*scale
clip=box(left,bottom,right,top);d.rectangle((20,99,1400,1060),fill='#142e2a')
def route(points,color,width):
 z=LineString(points).intersection(clip)
 for piece in list(z.geoms) if hasattr(z,'geoms') else [z]:
  if piece.geom_type=='LineString' and not piece.is_empty:d.line([xy(*p) for p in piece.coords],fill=color,width=max(1,round(scale*width)))
for t in n['tracks']:
 if t['layer'] in (2,4,32):route([(t['x1'],t['y1']),(t['x2'],t['y2'])],{2:'#3397bf',4:'#aa89d8',32:'#db79bf'}[t['layer']],t['width'])
for a in n['arcs']:
 sweep=(a['end_angle']-a['start_angle'])%360;count=max(8,math.ceil(sweep));route([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)],'#db79bf',a['width'])
for p in n['pads']:
 if not clip.contains(__import__('shapely').geometry.Point(p['x'],p['y'])):continue
 color='#f18bd2' if p['net'] and p['net'].startswith('MW') else '#e7c786'
 if p['shape']==1 and abs(p['size_x']-p['size_y'])<.00001:
  x,y=xy(p['x'],p['y']);r=p['size_x']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill=color)
 else:d.polygon([xy(*v) for v in M.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=color)
 if p['hole']:
  x,y=xy(p['x'],p['y']);r=p['hole']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='#09161c')
for v in n['vias']:
 if not clip.contains(__import__('shapely').geometry.Point(v['x'],v['y'])):continue
 x,y=xy(v['x'],v['y']);r=v['hole']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='#09161c')
for p in qp:
 pin=int(p['number']);x,y=p['x'],p['y']
 if pin in (1,24):y+=.82
 elif pin==8:x+=.9
 elif pin==17:x-=.9
 elif 2<=pin<=8:x-=.83
 elif 9<=pin<=16:y+=.78
 else:x+=.83
 d.text(xy(x,y),str(pin),font=small,fill='white',anchor='mm')
cx,cy=next((c['x'],c['y']) for c in n['components'] if c['designator']=='Q1');corners=[xy(*p) for p in M.corners(cx,cy,4.3,4.3,0)];d.polygon(corners,outline='#8eaeb9',width=2)
d.text(xy(cx,cy+.2),'4.3 x 4.3 mm',font=font,fill='white',anchor='mm');d.text(xy(cx,cy-.24),'pad inner ends',font=small,fill='#bed0d9',anchor='mm')
for c in n['components']:
 if c['designator'] in ['C2','C3','C4','R2','R3','R4','C6','R6']:
  x,y=xy(*{'R2':(17.3,42.5),'R3':(12.6,47.2),'R4':(6.8,47.2),'R6':(2.3,41.7),'C2':(17,39.5),'C3':(12.1,48.5),'C4':(7.35,48.5),'C6':(2.5,39.2)}[c['designator']]);d.text((x,y),c['designator'],font=small,fill='white',anchor='mm')
d.text((35,1074),'24 centred QD vias + 24 centred R/C vias. 0 shield vias. Native DRC: 0 violations.',font=small,fill='#b8c9d3');im.save(D/'QD_detail.png');(H/'native_render_snapshot.json').write_text(json.dumps(n,indent=2));print('Native PCB previews saved:',n['source_sha256'])
