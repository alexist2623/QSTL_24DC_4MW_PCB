"""Render three clear views from one hash-anchored saved native PCB snapshot."""
from pathlib import Path
import sys,json,struct,math,hashlib,collections,re
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;W=P.parent;ROOT=W.parent
sys.path.insert(0,str(W/'pcb_python'))
import olefile
SOURCE=ROOT/'outputs'/'QSTL_ZIF24_V2_project'/'QSTL_ZIF24_V2.PcbDoc'
DEST=ROOT/'outputs'/'QSTL_ZIF24_V2_layout.png'
OUT=P/'preview';UNIT=2.54e-6
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def props(data):
 out=[];i=0
 while i<len(data):
  n=struct.unpack_from('<I',data,i)[0]&0xffffff;i+=4
  text=data[i:i+n].rstrip(b'\0').decode('cp1252');i+=n
  out.append(dict(v.split('=',1) for v in text.split('|') if '=' in v))
 return out
def binary(data,kind):
 i=0
 while i<len(data):
  assert data[i]==kind;n=struct.unpack_from('<I',data,i+1)[0]&0xffffff
  yield data[i+5:i+5+n];i+=n+5
def mm(s):return float(s.removesuffix('mil'))*.0254
def read_native():
 before=sha(SOURCE)
 with olefile.OleFileIO(SOURCE) as ole:
  blobs={'/'.join(k):ole.openstream(k).read() for k in ole.listdir()}
 assert sha(SOURCE)==before,'Native PCB changed during snapshot'
 cs=props(blobs['Components6/Data']);ns=props(blobs['Nets6/Data']);board=props(blobs['Board6/Data'])[0]
 def net(b):
  i=struct.unpack_from('<H',b,3)[0];return None if i==65535 else ns[i]['NAME']
 components=[dict(index=i,designator=c['SOURCEDESIGNATOR'],x=mm(c['X']),y=mm(c['Y']),rotation=float(c['ROTATION']),side=c['LAYER'],pattern=c['PATTERN']) for i,c in enumerate(cs)]
 pads=[];data=blobs['Pads6/Data'];i=0
 while i<len(data):
  assert data[i]==2;i+=1;blocks=[]
  for j in range(6):
   n=struct.unpack_from('<I',data,i)[0]&0xffffff;blocks.append(data[i+4:i+4+n]);i+=4+n
  b=blocks[4];ci=struct.unpack_from('<H',b,7)[0];vals=[v*UNIT for v in struct.unpack_from('<9i',b,13)]
  pads.append(dict(component=None if ci==65535 else components[ci]['designator'],number=blocks[0][1:].decode(),net=net(b),layer=b[0],x=vals[0],y=vals[1],size_x=vals[2],size_y=vals[3],hole=vals[8],rotation=struct.unpack_from('<d',b,52)[0],shape=b[49]))
 tracks=[];arcs=[];vias=[];bodies=[]
 for b in binary(blobs['Tracks6/Data'],4):
  if b[0] not in [1,2,4,32] or net(b) in [None,'GND']:continue
  vals=[v*UNIT for v in struct.unpack_from('<5i',b,13)]
  tracks.append(dict(net=net(b),layer=b[0],native_layer_code=struct.unpack_from('<I',b,41)[0],**dict(zip(['x1','y1','x2','y2','width'],vals))))
 for b in binary(blobs['Arcs6/Data'],1):
  if b[0] not in [1,2,4,32] or net(b) in [None,'GND']:continue
  cx,cy,r=[v*UNIT for v in struct.unpack_from('<3i',b,13)];a0,a1=struct.unpack_from('<2d',b,25)
  arcs.append(dict(net=net(b),layer=b[0],cx=cx,cy=cy,radius=r,start_angle=a0,end_angle=a1,width=struct.unpack_from('<i',b,41)[0]*UNIT))
 for b in binary(blobs['Vias6/Data'],3):
  vals=[v*UNIT for v in struct.unpack_from('<4i',b,13)];vias.append(dict(net=net(b),**dict(zip(['x','y','diameter','hole'],vals))))
 for b in binary(blobs['ComponentBodies6/Data'],12):
  ci=struct.unpack_from('<H',b,7)[0]
  if ci==65535:continue
  a=b.index(b'V7_LAYER=');n=struct.unpack_from('<I',b,a-4)[0]&0xffffff;tail=b[a+n:];count=struct.unpack_from('<I',tail)[0]
  if len(tail)==4+count*16:
   points=[tuple(v*UNIT for v in struct.unpack_from('<2d',tail,4+j*16)) for j in range(count)]
   bodies.append(dict(component=components[ci]['designator'],points=points))
 outline=[(mm(board['VX'+str(i)]),mm(board['VY'+str(i)])) for i in range(4)]
 layers=[board[k[:-len('COPTHICK')]+'NAME'] for k in board if re.fullmatch(r'V9_STACK_LAYER\d+_COPTHICK',k)]
 return dict(source=str(SOURCE),source_sha256=before,components=components,pads=pads,tracks=tracks,arcs=arcs,vias=vias,bodies=bodies,board_outline=outline,copper_layers=layers)

def corners(x,y,w,h,rotation):
 a=math.radians(rotation);c,s=math.cos(a),math.sin(a)
 return [(x+dx*c-dy*s,y+dx*s+dy*c) for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
def render(n):
 scale=18.;pane=420;header=145;foot=165;boardh=67.9*scale;bottom=header+boardh
 im=Image.new('RGB',(pane*3,int(bottom+foot)),'#101821');d=ImageDraw.Draw(im)
 font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
 title=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27);label=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12);pinfont=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',11)
 blue='#52c8ff';pink='#f18bd2';gold='#e7c786';ground='#529d74';boardcolor='#142e2a'
 d.text((25,19),'QSTL  |  ZIF51 + QD24  |  RF4 / DC20',fill='white',font=title)
 d.text((25,57),'19.5 x 67.9 mm  /  6 layers  /  saved Altium PCB geometry',fill='#c8d6df',font=font)
 def text_at(point,text,fill='white',f=small,anchor='mm',bg=True):
  if bg:
   bb=d.textbbox(point,text,font=f,anchor=anchor);d.rectangle((bb[0]-2,bb[1]-1,bb[2]+2,bb[3]+1),fill='#101d24')
  d.text(point,text,font=f,fill=fill,anchor=anchor)
 for panel in range(3):
  flip=panel==1
  def xy(x,y):return panel*pane+34+(19.5-x if flip else x)*scale,bottom-y*scale
  titletext=['TOP: ZIF / SMP','BOTTOM: QD24 / R / C','INNER SIGNALS: L2 + L4'][panel]
  d.text((panel*pane+34,99),titletext,fill='white',font=font)
  d.text((panel*pane+34,121),'X mirrored, looking at underside' if flip else 'Top-view board coordinates',fill='#93acb8',font=small)
  rect=[xy(0,67.9),xy(19.5,0)];d.rectangle((min(q[0] for q in rect),rect[0][1],max(q[0] for q in rect),rect[1][1]),fill=boardcolor,outline='#8fac9f',width=2)
  # Native body contours for Top, plus a clearly outlined full QD land envelope.
  for body in n['bodies']:
   if panel==2:continue
   c=next(c for c in n['components'] if c['designator']==body['component'])
   if c['side']!=('BOTTOM' if panel==1 else 'TOP'):continue
   d.polygon([xy(*p) for p in body['points']],fill='#233d40',outline='#627b7f')
  q=next(c for c in n['components'] if c['designator']=='Q1');cx,cy=q['x'],q['y']
  if panel in [1,2]:
   d.polygon([xy(*p) for p in corners(cx,cy,7.,7.,0)],fill='#23333a',outline='#728d96')
   d.line([xy(*p) for p in corners(cx,cy,8.4,8.4,0)+[corners(cx,cy,8.4,8.4,0)[0]]],fill='#596c72',width=1)
  if panel==0:
   # Projection only, does not imply a Top-mounted QD body.
   pts=[xy(*p) for p in corners(cx,cy,8.4,8.4,0)]
   for a,b in zip(pts,pts[1:]+pts[:1]):
    dist=math.dist(a,b)
    for j in range(0,int(dist),10):
     t0=j/dist;t1=min(1,(j+5)/dist);d.line([(a[0]+(b[0]-a[0])*t0,a[1]+(b[1]-a[1])*t0),(a[0]+(b[0]-a[0])*t1,a[1]+(b[1]-a[1])*t1)],fill='#405856')
   text_at(xy(cx,cy),'QD on opposite side',fill='#75918d',f=label)
  layers=[{1},{32},{2,4}][panel]
  for t in n['tracks']:
   if t['layer'] not in layers:continue
   color=(blue if t['layer']==2 else pink) if panel==2 else gold
   d.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])],fill=color,width=max(2,round(t['width']*scale)))
  for a in n['arcs']:
   if a['layer'] not in layers:continue
   sweep=(a['end_angle']-a['start_angle'])%360 or 360;count=max(8,math.ceil(sweep/2))
   pts=[xy(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)]
   d.line(pts,fill=pink if panel==2 else gold,width=max(2,round(a['width']*scale)))
  for v in n['vias']:
   x,y=xy(v['x'],v['y']);r=v['diameter']*scale/2;h=v['hole']*scale/2
   d.ellipse((x-r,y-r,x+r,y+r),fill=ground if v['net']=='GND' else gold)
   d.ellipse((x-h,y-h,x+h,y+h),fill='#0c191c')
  for p in n['pads']:
   if panel==0 and p['layer']==32:continue
   if panel==1 and p['layer']==1:continue
   color=gold if panel!=2 or p['hole'] else '#9b957e'
   if p['component']=='Q1' and p['net'] in ['MW1','MW2','MW3','MW4']:color='#ff8fd4'
   x,y=xy(p['x'],p['y']);rx,ry=p['size_x']*scale/2,p['size_y']*scale/2
   if p['shape']==1 and abs(rx-ry)<1e-4:d.ellipse((x-rx,y-ry,x+rx,y+ry),fill=color)
   else:d.polygon([xy(*pt) for pt in corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=color)
   if p['hole']:
    h=p['hole']*scale/2;d.ellipse((x-h,y-h,x+h,y+h),fill='#0c191c')
  if panel==0:
   for c in n['components']:
    if c['side']!='TOP':continue
    name=c['designator'];x,y=c['x'],c['y']
    if name=='J1':text_at(xy(x,8.9),'J1 / ZIF51',f=font)
    elif name.startswith('SMP'):text_at(xy(x,y+3.05),name,f=small)
    else:text_at(xy(x,y+1.2),name,f=label)
  elif panel==1:
   text_at(xy(cx,cy+1.1),'QD24',f=font)
   text_at(xy(cx,cy),'BOTTOM',fill='#9cafbb',f=small)
   for p in [p for p in n['pads'] if p['component']=='Q1']:
    dx,dy=p['x']-cx,p['y']-cy
    # Pin labels inside the array avoid routing and neighboring lands.
    tx=p['x']-.60*math.copysign(1,dx) if abs(dx)>3 else p['x']
    ty=p['y']+(.67 if int(p['number'])%2 else 1.18) if dy<-3 else p['y']
    text_at(xy(tx,ty),p['number'],fill='#ff9ada' if p['net'] and p['net'].startswith('MW') else '#c4ced4',f=pinfont,bg=False)
   for c in n['components']:
    if c['side']=='BOTTOM' and c['designator']!='Q1':text_at(xy(c['x'],c['y']+1.15),c['designator'],f=small)
   text_at(xy(9.75,31),'RF1 -> 24   RF2 -> 21',fill='#ff9ada',f=small)
   text_at(xy(9.75,29.7),'RF3 -> 14   RF4 -> 11',fill='#ff9ada',f=small)
   text_at(xy(9.75,5),'ZIF on opposite side',fill='#75918d',f=label)
  else:
   text_at(xy(cx,cy),'QD24',fill='#a5b7bd',f=small)
   for c in n['components']:
    if c['designator'].startswith('SMP'):text_at(xy(c['x'],c['y']+3.05),c['designator'],f=small)
  text_at(xy(1.2 if not flip else 18.3,1.0),'0',fill='#95b0a7',f=label,bg=False)
 y=bottom+24;counts=collections.Counter(t['layer'] for t in n['tracks']);ng=sum(v['net']=='GND' for v in n['vias'])
 d.text((25,y),'BLUE  L2 DC routing',font=font,fill=blue);d.text((240,y),'PINK  L4 RF routing',font=font,fill=pink);d.text((550,y),'GREEN  GND vias',font=font,fill=ground)
 d.text((25,y+29),f"Native signal copper: {len(n['tracks'])} tracks + {len(n['arcs'])} arcs  |  {len(n['vias'])} vias ({ng} GND)  |  16 components / 129 pads",font=small,fill='#bccbd1')
 d.text((25,y+53),'GND: L1/L3/L5/L6, solid stitching. Every via: Top + Bottom paste opening. QD interior: no signal tracks.',font=small,fill='#9dafb9')
 d.text((25,y+77),'Bottom view is mirrored across X; Top and inner views share the saved board-coordinate projection.',font=small,fill='#9dafb9')
 d.text((25,y+101),'Saved PCB SHA-256: '+n['source_sha256'],font=label,fill='#77909c')
 return im

def main():
 n=read_native();assert len(n['components'])==16 and len(n['pads'])==129
 assert next(c for c in n['components'] if c['designator']=='Q1')['side']=='BOTTOM'
 assert all(p['layer']==32 for p in n['pads'] if p['component']=='Q1')
 assert all(t['native_layer_code']==0x0100ffff for t in n['tracks'] if t['layer']==32),'Bottom stub layer code not normalized'
 im=render(n);assert sha(SOURCE)==n['source_sha256'],'PCB changed before render completed'
 OUT.mkdir(exist_ok=True);(OUT/'final_native_snapshot.json').write_text(json.dumps(n,indent=2));im.save(DEST)
 report={'source':str(SOURCE),'source_sha256':n['source_sha256'],'preview':str(DEST),'signal_track_layers':dict(collections.Counter(t['layer'] for t in n['tracks'])),'signal_arcs':len(n['arcs']),'vias':len(n['vias']),'ground_vias':sum(v['net']=='GND' for v in n['vias']),'components':len(n['components']),'pads':len(n['pads']),'copper_layers':n['copper_layers'],'bottom_view':'X-mirrored actual underside','ground_pours_shown':False}
 (OUT/'render_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
