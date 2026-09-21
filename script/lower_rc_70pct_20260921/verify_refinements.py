"""Independent saved-file checks for rectangles, ring geometry and solid mounts."""
from pathlib import Path
import sys,json,math,importlib.util
from shapely.geometry import Point,Polygon,shape,box,LineString
from shapely.ops import unary_union
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from build_routed_copy import snapshot
from native_metadata_helpers import properties,UNIT,sha
from verify_final_native_v2 import read_regions
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=P/(B+'.PcbDoc');n=m.read_native();plan=json.loads((H/'plan.json').read_text());s=snapshot(m.SOURCE);regions=read_regions(s['Regions6/Data']);ns=properties(s['Nets6/Data']);polys=properties(s['Polygons6/Data']);errors=[]
def check(ok,msg):
    if not ok:errors.append(msg)
def padshape(p):
    if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:return Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=128)
    return Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
opens={l:unary_union([r['geometry'] for r in regions if r['layer']==l and r['name'].startswith('SURFACE_MASK_OPEN_')]) for l in (37,38)}
for name,rect in plan['RC_mask_rectangles'].items():
    rect=shape(rect);check(rect.equals(box(*rect.bounds)),'Nonrectangular RC mask '+name)
    check(rect.buffer(-5*UNIT).intersection(opens[38]).area<1e-7,'RC mask coverage '+name)
    group=unary_union([padshape(p) for p in n['pads'] if p['component'] in name.split('/')]);a,b,c,d=group.bounds
    check(rect.symmetric_difference(box(a-.9,b-.9,c+.9,d+.9)).area<.0001,'RC 0.9 mm margin '+name)
zrect=shape(plan['ZIF_bottom_mask_rectangle']);check(zrect.equals(box(*zrect.bounds)),'ZIF mask not rectangular');check(zrect.buffer(-5*UNIT).intersection(opens[38]).area<1e-7,'ZIF mask not covered')
check(all(zrect.covers(Point(v['x'],v['y']).buffer(v['diameter']/2)) for v in n['vias'] if v['y']<10),'ZIF via outside mask rectangle')
shield=[v for v in n['vias'] if v['net']=='GND'];hulls={name:unary_union([padshape(p) for p in n['pads'] if p['component']==name]).convex_hull for name in [f'{k}{i}' for k in 'RC' for i in range(1,7)]}
intrusions=[name for name,hull in hulls.items() if any(hull.intersects(Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32)) for v in shield)];check(not intrusions,'Shield vias cross R/C body envelopes')
ring_reports=[]
for k in range(1,7):
    p=next(p for p in n['pads'] if p['component']==f'SMP{k}' and p['number']=='1');radius=p['size_x']/2+.33+.05
    ring=[v for v in shield if abs(math.dist((v['x'],v['y']),(p['x'],p['y']))-radius)<6*UNIT]
    check(len(ring)==11,'SMP ring count '+str(k));angles=sorted(math.degrees(math.atan2(v['y']-p['y'],v['x']-p['x']))%360 for v in ring);steps=sorted((angles[(i+1)%len(angles)]-a)%360 for i,a in enumerate(angles))
    check(all(abs(a-360/13)<.002 for a in steps[:-1]) and abs(steps[-1]-3*360/13)<.002,'Unequal ring '+str(k));ring_reports.append(dict(component=f'SMP{k}',count=len(ring),radius_mm=radius,regular_step_degrees=360/13))
mounts=[p for p in n['pads'] if p['component'] is None];mount_report=[]
for p in mounts:
    disk=padshape(p).buffer(.3,quad_segs=64)
    check(all(opens[l].buffer(6*UNIT).covers(disk) for l in (37,38)),'Mount still masked')
for layer in (1,3,5,32):
    pieces=[]
    for r in regions:
        ni=r['net_index']
        if ni==65535 and r['polygon_index']!=65535:ni=int(polys[r['polygon_index']]['NET'])
        if r['layer']==layer and ni!=65535 and ns[ni]['NAME']=='GND':pieces.append(r['geometry'])
    ground=unary_union(pieces)
    for p in mounts:
        pt=Point(p['x'],p['y']);radius=p['size_x']/2;annulus=pt.buffer(radius+.2,quad_segs=128).difference(pt.buffer(radius+.02,quad_segs=128));missing=annulus.difference(ground.buffer(5*UNIT)).area
        check(missing<1e-7,f'Mount thermal relief remains on layer {layer} at {p["x"]},{p["y"]}');mount_report.append(dict(layer=layer,x=p['x'],y=p['y'],missing_copper_mm2=missing))
qd=unary_union([padshape(p) for p in n['pads'] if p['component']=='Q1']);upper_gap=min(g.distance(qd) for name,g in hulls.items() if name in ('R3','C3','R4','C4'));check(upper_gap>=2.0,'Upper RC too close to QD')
report=dict(passed=not errors,errors=errors,pcb_sha256=sha(m.SOURCE),upper_RC_to_QD_pad_gap_mm=upper_gap,RC_mask_margin_mm=.9,ZIF_bottom_rectangle_mm=list(zrect.bounds),RC_interpad_via_intrusions=intrusions,SMP_rings=ring_reports,mount_solid_copper_checks=mount_report)
(H/'refinements_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
# Render actual saved mask regions as a 2D inspection artifact; not a 3D view.
def render(bounds,path,title,scale=95):
    xmin,ymin,xmax,ymax=bounds;ox=55;oy=90;w=round((xmax-xmin)*scale)+110;h=round((ymax-ymin)*scale)+145;im=Image.new('RGB',(w,h),'#17212b');d=ImageDraw.Draw(im);font=lambda sz:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',sz);xy=lambda x,y:(ox+(x-xmin)*scale,oy+(ymax-y)*scale)
    clip=box(*bounds);protected=clip.difference(opens[38]);d.rectangle((ox,oy,w-ox,h-55),fill='#c6b53a')
    def poly(geom,color,holecolor=None):
        for g in geom.geoms if hasattr(geom,'geoms') else [geom]:
            if g.geom_type!='Polygon' or g.is_empty:continue
            d.polygon([xy(*p) for p in g.exterior.coords],fill=color)
            if holecolor:
                for ring in g.interiors:d.polygon([xy(*p) for p in ring.coords],fill=holecolor)
    poly(protected,'#4c7538','#c6b53a')
    for t in n['tracks']:
        if t['layer']==32:
            g=LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2).intersection(clip);poly(g,'#315929')
    for a in n['arcs']:
        if a['layer']!=32:continue
        sweep=(a['end_angle']-a['start_angle'])%360;count=max(8,math.ceil(sweep*2));points=[(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)),a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)];poly(LineString(points).buffer(a['width']/2).intersection(clip),'#315929')
    for p in n['pads']:
        if p['layer'] not in (32,74):continue
        g=padshape(p).intersection(clip);poly(g,'#ddc873')
        if p['hole'] and clip.contains(Point(p['x'],p['y'])):
            a,b=xy(p['x'],p['y']);rr=p['hole']/2*scale;d.ellipse((a-rr,b-rr,a+rr,b+rr),fill='#f2f2e8')
    for v in n['vias']:
        if not clip.contains(Point(v['x'],v['y'])):continue
        a,b=xy(v['x'],v['y']);rr=v['diameter']/2*scale;d.ellipse((a-rr,b-rr,a+rr,b+rr),outline='#8fab76',width=1);rr=v['hole']/2*scale;d.ellipse((a-rr,b-rr,a+rr,b+rr),fill='#93ac88')
    for c in n['components']:
        if c['designator'][:1] in ('R','C') and clip.contains(Point(c['x'],c['y'])):
            p=next(p for p in n['pads'] if p['component']==c['designator']);a,b=xy(c['x'],c['y']);d.text((a,b),c['designator'],font=font(20),fill='white',anchor='mm')
    d.text((ox,25),title,font=font(27),fill='white');d.text((ox,h-38),'Saved Bottom mask geometry | top-coordinate projection | '+sha(m.SOURCE)[:16],font=font(17),fill='#c0d0d8');im.save(path)
render((.2,26,19.3,53),P/'docs/RC_mask_detail.png','R/C placement and rectangular solder-control masks',65)
render((.2,.2,19.3,10),P/'docs/ZIF_mask_detail.png','ZIF rear fanout: rectangular solder-mask coverage',85)
raise SystemExit(0 if not errors else 1)
