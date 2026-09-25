"""Verify requested invariants and render the saved original DC geometry."""
from pathlib import Path
import json,sys,math,collections,importlib.util,csv,shutil
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent; R=H.parents[1]; P=R/'QSTL_24DC_4MW_PCB'; D=P/'docs'; W=H.parent/'_support'; B='QSTL_24DC_4MW_PCB'; U=2.54e-6
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','zif_revision_v2/schematic','pcb_python')]
from native_metadata_helpers import sha
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=P/(B+'.PcbDoc');n=m.read_native()
(H/'after_native.json').write_text(json.dumps(n,indent=2))
expected=json.loads((H/'expected.json').read_text());old=json.loads((H/'before_native.json').read_text());plan=json.loads((H/'plan.json').read_text())
scope={'__file__':str(W/'zif_revision_v2/schematic/validate_v2_schematic.py'),'__name__':'saved_even_validator'}
exec(compile((H.parent/'rf_six_inward_20260920/validator_source.py').read_text(),scope['__file__'],'exec'),scope)
sch=scope['validate'](P/(B+'.SchDoc'),expected,H/'schematic_compile.txt',m.SOURCE)
assert sch['passed'],sch['errors'];assert sch['native_compile']['summary']['VIOLATION_COUNT']=='0'
(H/'schematic_validation.json').write_text(json.dumps(sch,indent=2));(D/'schematic_validation.json').write_text(json.dumps(sch,indent=2))
def canonical(items):return collections.Counter(json.dumps(x,sort_keys=True) for x in items)
assert n['components']==old['components'] and json.dumps(n['board_outline'])==json.dumps(old['board_outline'])
assert canonical([t for t in n['tracks'] if t['layer']==32])==canonical([t for t in old['tracks'] if t['layer']==32])
assert canonical(n['arcs'])==canonical(old['arcs'])
assert canonical([v for v in n['vias'] if v['net']=='GND'])==canonical([v for v in old['vias'] if v['net']=='GND'])
assert [{k:v for k,v in p.items() if k!='net'} for p in n['pads']]==[{k:v for k,v in p.items() if k!='net'} for p in old['pads']]
used=sorted(int(p['number']) for p in n['pads'] if p['component']=='J1' and p['net'])
assert used==list(range(2,49,2))
layers={net:{t['layer'] for t in n['tracks'] if t['net']==net and t['layer']!=1} for net in expected['nets'] if net.startswith('ZIF')}
assert collections.Counter(tuple(x) for x in layers.values())=={(2,):12,(4,):12}
maxturn=0
for net,ls in layers.items():
    ts=[t for t in n['tracks'] if t['net']==net and t['layer']!=1];nodes=collections.defaultdict(list)
    for t in ts:
        a,b=(t['x1'],t['y1']),(t['x2'],t['y2']);dx,dy=b[0]-a[0],b[1]-a[1]
        assert min(abs(dx),abs(dy),abs(abs(dx)-abs(dy)))<8*U
        for u,v in ((a,b),(b,a)):nodes[tuple(round(z/U) for z in u)].append((v[0]-u[0],v[1]-u[1]))
    for vectors in nodes.values():
        assert len(vectors)<=2
        if len(vectors)==2:
            a,b=vectors;dot=sum(x*y for x,y in zip(a,b))/(math.hypot(*a)*math.hypot(*b));turn=180-math.degrees(math.acos(max(-1,min(1,dot))));maxturn=max(maxturn,turn);assert turn<45.01
report=dict(passed=True,pcb_sha256=n['source_sha256'],used_ZIF_contacts=used,pin50_NC=True,all_odd_contacts_NC=True,DC_nets=24,DC_internal_layer_counts={'L2':12,'L4':12},maximum_DC_turn_degrees=maxturn,added_transition_vias=0,RF_geometry_unchanged=True,component_and_pad_geometry_unchanged=True,shield_geometry_unchanged=True,schematic_pin_map_matches_saved_PCB=True,schematic_native_compile_return=sch['native_compile']['summary']['COMPILE_RESULT'],schematic_native_reported_violations=0)
(H/'request_validation.json').write_text(json.dumps(report,indent=2));(D/'DC_Even_ZIF.json').write_text(json.dumps(report,indent=2))
# Recover mapping CSV from the saved board, retaining the read-only reference column.
rows=list(csv.DictReader((D/'PIN_MAPPING.csv').open(newline='',encoding='utf-8-sig')))
for row in rows:
    q=row['QD_pad'];p=next(p for p in n['pads'] if p['component']=='Q1' and p['number']==q);row['QD_net']=p['net']
    row['ZIF_pin']=str(int((expected['pin_net_map'][row['Bias_resistor']+'-2'] if row['Bias_resistor'] else p['net'])[3:]))
with (D/'PIN_MAPPING.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for src,dst in [('native_paste_audit.txt','native_paste_audit.txt'),('reopen_check.txt','native_reopen_check.txt'),('schematic_compile.txt','native_schematic_compile.txt'),('refinements_validation.json','placement_mask_validation.json')]:shutil.copy2(H/src,D/dst)
# Geometric previews use actual saved primitives; they are not screen captures.
font=lambda s:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s)
colors={1:'#e8c675',2:'#36d6e6',4:'#f583c9'};back='#111c26';board='#182b32';muted='#637781'
def draw_board(im,origin,scale,bounds,showlayers,labelpins=False):
    d=ImageDraw.Draw(im);x0,y0,x1,y1=bounds;ox,oy=origin;xy=lambda x,y:(ox+(x-x0)*scale,oy+(y1-y)*scale)
    d.rectangle((ox,oy,ox+(x1-x0)*scale,oy+(y1-y0)*scale),fill=board,outline='#6c8793',width=2)
    for p in n['pads']:
        if p['hole'] and x0<=p['x']<=x1 and y0<=p['y']<=y1:
            x,y=xy(p['x'],p['y']);r=p['size_x']*scale/2;h=p['hole']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill='#233c42',outline=muted);d.ellipse((x-h,y-h,x+h,y+h),fill=back)
    if y1>45:
        a,b=xy(7.6,44.65),xy(11.9,40.35);d.rectangle((*a,*b),outline='#8aa0a8',width=2);d.text(xy(9.75,42.5),'QD',fill='#a6b5be',font=font(17),anchor='mm')
    for t in n['tracks']:
        if not t['net'].startswith('ZIF') or t['layer'] not in showlayers:continue
        if not(layers[t['net']]&showlayers):continue
        if max(t['y1'],t['y2'])<y0 or min(t['y1'],t['y2'])>y1:continue
        a,b=(t['x1'],t['y1']),(t['x2'],t['y2'])
        if a[1]!=b[1]:
            aa,bb=a,b
            if a[1]>y1:a=(aa[0]+(bb[0]-aa[0])*(y1-aa[1])/(bb[1]-aa[1]),y1)
            if b[1]>y1:b=(aa[0]+(bb[0]-aa[0])*(y1-aa[1])/(bb[1]-aa[1]),y1)
        d.line([xy(*a),xy(*b)],fill=colors[t['layer']],width=max(2,round(scale*t['width'])))
    for p in n['pads']:
        if not(x0<=p['x']<=x1 and y0<=p['y']<=y1) or p['hole']:continue
        active=p['net'] in layers and bool(layers[p['net']]&showlayers);col=colors[next(iter(layers[p['net']]))] if active else '#40545c'
        if p['component']=='J1' and not p['net']:col='#535351'
        d.polygon([xy(*v) for v in m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=col)
        if labelpins and p['component']=='J1' and int(p['number'])<=51:
            num=int(p['number']);lab=xy(p['x'],p['y']+(-.85 if num%2 else -.62));d.text(lab,p['number'],font=font(15),fill='#ffffff' if active else '#a8adb0',anchor='mm')
    for v in n['vias']:
        if v['net'] not in layers or not(layers[v['net']]&showlayers) or not(x0<=v['x']<=x1 and y0<=v['y']<=y1):continue
        x,y=xy(v['x'],v['y']);r=v['diameter']*scale/2;h=v['hole']*scale/2;col=colors[next(iter(layers[v['net']]))];d.ellipse((x-r,y-r,x+r,y+r),fill=col);d.ellipse((x-h,y-h,x+h,y+h),fill=back)
    if y1>45:
        for c in n['components']:
            if c['designator'].startswith('R'):
                d.text(xy(c['x'],c['y']+.85),c['designator'],font=font(13),fill='#c5d0d7',anchor='mm')
        d.text(xy(9.75,1.1),'J1 / ZIF',font=font(16),fill='white',anchor='mm')
    if labelpins:
        p=next(p for p in n['pads'] if p['component']=='J1' and p['number']=='50');a=xy(p['x'],p['y']);b=xy(18.05,9.0);d.line([a,(b[0],a[1]-30),b],fill='#ffd47f',width=2);d.text((b[0],b[1]-15),'50 NC',font=font(20),fill='#ffd47f',anchor='mm')
scale=22;pane=475;top=155;bottom=top+67.9*scale
im=Image.new('RGB',(pane*3,int(bottom+94)),back);d=ImageDraw.Draw(im)
d.text((30,22),'DC ROUTING | EVEN ZIF CONTACTS 2-48',font=font(30),fill='white')
d.text((30,68),'Pin 50 and all odd contacts: NC  |  24 DC nets  |  Top-view coordinates',font=font(20),fill='#c2d0d8')
for k,(ls,title) in enumerate([({1,2,4},'L2 + L4 OVERLAY'),({1,2},'L2 DC_A - 12 NETS'),({1,4},'L4 DC_B - 12 NETS')]):
    d.text((k*pane+25,118),title,font=font(21),fill='white');draw_board(im,(k*pane+23,top),scale,(0,0,19.5,67.9),ls)
d.text((28,bottom+22),'Cyan: L2  |  Magenta: L4  |  Gold: Top escapes  |  DC 0.125 mm / Top 0.15 mm',font=font(19),fill='#c2d0d8')
d.text((28,bottom+52),'Saved PCB geometry: '+n['source_sha256'][:20]+'  |  RF and GND fill hidden for clarity',font=font(17),fill='#8fa6b2')
im.save(D/'DC_only.png');im.save(D/'DC_Even_ZIF.png')
scale=64;im=Image.new('RGB',(1328,960),back);d=ImageDraw.Draw(im);d.text((40,22),'ZIF DETAIL | ONLY EVEN CONTACTS 2-48 CONNECTED',font=font(28),fill='white');d.text((40,66),'Gold: Top escapes  |  Cyan: L2  |  Magenta: L4  |  Existing 24 fanout vias relocated',font=font(18),fill='#c2d0d8');draw_board(im,(40,115),scale,(0,0,19.5,12),{1,2,4},True);d.text((40,912),'All odd contacts and contact 50 remain unconnected. No added DC layer-transition vias.',font=font(20),fill='#c2d0d8');im.save(D/'DC_Even_ZIF_detail.png')
print(json.dumps({'request_validation':report,'schematic':sch['passed'],'images':[str(D/'DC_Even_ZIF.png'),str(D/'DC_Even_ZIF_detail.png')]},indent=2))
