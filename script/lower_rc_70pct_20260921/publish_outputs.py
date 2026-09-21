"""Publish saved-PCB previews and hash-bound fabrication companion files."""
from pathlib import Path
import importlib.util,json,math,hashlib,shutil,runpy,sys
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape,box,LineString,Point
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';D=P/'docs';W=H.parent/'_support'
v=json.loads((H/'validation.json').read_text());assert v['passed']
spec=importlib.util.spec_from_file_location('native_reader',W/'zif_revision_v2/render_native_layout.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=P/'QSTL_24DC_4MW_PCB.PcbDoc';n=m.read_native()
assert n['source_sha256']==v['pcb_sha256'];plan=json.loads((H/'plan.json').read_text())
(H/'native_render_snapshot.json').write_text(json.dumps(n,indent=2))
colors={1:'#f5ba59',2:'#54bdf2',3:'#ec88bc',4:'#69d4bd',5:'#ba9df5',6:'#f88f76'}
def netcolor(net):return colors[int(net[-1])] if net and net.startswith(('MW','S')) and net[-1:].isdigit() else '#d9bd76'
def font(size):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)
def render(bounds,out,title,subtitle,layers=(32,),scale=64,labels=True):
    xmin,ymin,xmax,ymax=bounds;left,top=60,110;width=round((xmax-xmin)*scale+120);bottom=round((ymax-ymin)*scale+top);im=Image.new('RGB',(width,bottom+130),'#101820');dr=ImageDraw.Draw(im)
    xy=lambda x,y:(left+(x-xmin)*scale,top+(ymax-y)*scale)
    clip=box(*bounds)
    def fit(s,size):
        while font(size).getlength(s)>width-2*left and size>9:size-=1
        return font(size)
    dr.text((left,22),title,font=fit(title,30),fill='white');dr.text((left,67),subtitle,font=fit(subtitle,17),fill='#9bb5c4')
    dr.rectangle((left,top,width-left,bottom),fill='#152832',outline='#49616c',width=2)
    def line(points,color,w=1):
        g=LineString(points).intersection(clip)
        for q in g.geoms if hasattr(g,'geoms') else [g]:
            if q.geom_type=='LineString' and not q.is_empty:dr.line([xy(*z) for z in q.coords],fill=color,width=max(1,round(w*scale)),joint='curve')
    cav=shape(plan['cavity']['geometry']);inner=shape(plan['QD_exclusion'])
    for geom,color in [(inner,'#3e525b'),(cav,'#8299a3')]:
        line(list(geom.exterior.coords),color,.023)
    for t in n['tracks']:
        if t['layer'] in layers:line([(t['x1'],t['y1']),(t['x2'],t['y2'])],netcolor(t['net']) if t['layer']==32 else {1:'#bbc2c6',2:'#49b3db',4:'#c58ae6'}[t['layer']],t['width'])
    for a in n['arcs']:
        if a['layer'] not in layers:continue
        sweep=(a['end_angle']-a['start_angle'])%360;k=max(4,math.ceil(sweep*2))
        line([(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*j/k)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*j/k))) for j in range(k+1)],netcolor(a['net']),a['width'])
    def circ(x,y,r,c):
        a,b=xy(x,y);r*=scale;dr.ellipse((a-r,b-r,a+r,b+r),fill=c)
    for pad in n['pads']:
        if not clip.contains(Point(pad['x'],pad['y'])):continue
        if pad['layer']==1 and 1 not in layers and not pad['hole']:continue
        color=netcolor(pad['net']) if pad['net']!='GND' else '#527c6f'
        if pad['shape']==1 and abs(pad['size_x']-pad['size_y'])<1e-5:circ(pad['x'],pad['y'],pad['size_x']/2,color)
        else:dr.polygon([xy(*pt) for pt in m.corners(pad['x'],pad['y'],pad['size_x'],pad['size_y'],pad['rotation'])],fill=color)
        if pad['hole']:circ(pad['x'],pad['y'],pad['hole']/2,'#101820')
    for via in n['vias']:
        if not clip.contains(Point(via['x'],via['y'])):continue
        if via['net']=='GND':
            if not any(l in layers for l in (5,32)):continue
            circ(via['x'],via['y'],via['diameter']/2,'#82efbd')
        circ(via['x'],via['y'],via['hole']/2,'#101820')
    def label(x,y,s,c='#d5e4eb',size=17):
        a,b=xy(x,y);dr.text((a,b),s,font=font(size),fill=c,anchor='mm',stroke_width=1,stroke_fill='#101820')
    if ymin<42.5<ymax:
        label(9.75,42.8,'4.3 x 4.3 mm',size=max(9,round(scale*.32)));label(9.75,42.3,'Bottom pocket, depth 1.2',size=max(7,round(scale*.2)))
    if labels:
        for pad in n['pads']:
            if pad['component']!='Q1' or not clip.contains(Point(pad['x'],pad['y'])):continue
            pin=int(pad['number']);x,y=pad['x'],pad['y']
            if pin in (1,24):y-=.83
            elif 2<=pin<=8:x-=.83
            elif 9<=pin<=16:y+=.78
            else:x+=.83
            label(x,y,pad['number'],netcolor(pad['net']),14)
        for c in n['components']:
            if c['designator'].startswith('SMP') and clip.contains(Point(c['x'],c['y']+2.8)):label(c['x'],c['y']+2.8,c['designator'])
        for ch in range(1,7):
            for pref in ('R','C'):
                c=next(a for a in n['components'] if a['designator']==pref+str(ch));dx=(-.9 if c['x']<9.75 else .9);yy=c['y']+(.2 if pref=='R' else .3)
                if clip.contains(Point(c['x']+dx,yy)):label(c['x']+dx,yy,c['designator'],colors[ch],14)
    for dy,s,size,c in [(18,'RF: 0.110 mm | CPW GND gap: 0.200 mm | green vias: L6-L5 only',17,'#c5d6df'),(47,'Top-coordinate projection; QD / R / C are on Bottom. GND pours and masks omitted.',15,'#9bb5c4'),(77,'Saved PCB SHA-256: '+n['source_sha256'][:32],14,'#718e9d')]:dr.text((left,bottom+dy),s,font=fit(s,size),fill=c)
    im.save(out)
render((0,25,19.5,54),D/'RF_only.png','RF6 | 50-ohm geometry and blind-via fences','QD/R/C RF pads: no vias | 480 GND shields | 0.15 mm land-edge spacing')
render((.5,37,19,53.5),D/'QD_detail.png','QD24 | 4.3 mm pocket / 4.7 mm pad-end opening','0.2 mm pad-to-pocket clearance | 18 QD DC vias retained | RF pads via-free',scale=73)
render((0,0,19.5,67.9),D/'layout.png','QSTL | RF6 + DC24 | saved native PCB','19.5 x 67.9 mm | RF L6 / GND L5 / DC L4 / GND L3 / DC L2 / GND L1',layers=(1,2,4,32),scale=27,labels=False)
runpy.run_path(str(H/'fabrication_notes.py'),run_name='__main__')
F=H/'fabrication';shield=[q for q in n['vias'] if q['net']=='GND'];assert len(shield)==480
drill=['M48',';L6-L5 LASER BLIND MICROVIAS ONLY - NOT THROUGH DRILL',';UNMIRRORED PCB XY; MM WITH EXPLICIT DECIMAL POINTS','METRIC','T01C0.100','%','G90','G05','T01']+[f"X{q['x']:.6f}Y{q['y']:.6f}" for q in shield]+['M30']
(F/'L6_L5_laser_microvias.drl').write_text('\n'.join(drill)+'\n',encoding='ascii')
dest=P/'fabrication'/'RF50_QD_cavity';dest.mkdir(parents=True,exist_ok=True)
for f in F.iterdir():
    if f.is_file():shutil.copy2(f,dest/f.name)
manifest=dict(status='Validated design companion; complete production CAM export not included',pcb_sha256=n['source_sha256'],pcblib_sha256=v['pcblib_sha256'],schematic_sha256=v['schematic_sha256'],files={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in dest.iterdir() if f.is_file() and f.name!='manifest.json'},validation='../../docs/Lower_RC_70pct_validation.json')
(dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copy2(H/'native_paste_audit.txt',D/'native_paste_audit.txt')
shutil.copy2(P/'work/lower_rc_70pct_reopen_check.txt',D/'native_reopen_check.txt')
(D/'RF50_render.json').write_text(json.dumps(dict(pcb_sha256=n['source_sha256'],images=['RF_only.png','QD_detail.png','layout.png'],ground_pours_shown=False,masks_shown=False),indent=2))
print('Published previews and fabrication companions for',n['source_sha256'])
