"""Read-only Top copper/solder-mask plan view of the current original PCB."""
from pathlib import Path
import sys,json,importlib.util,math
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','pcb_python')]
from native_metadata_helpers import sha,properties
from build_routed_copy import snapshot
from verify_final_native_v2 import read_regions,read_rules
spec=importlib.util.spec_from_file_location('native_reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=P/(B+'.PcbDoc');n=m.read_native();digest=n['source_sha256'];s=snapshot(m.SOURCE);rs=read_regions(s['Regions6/Data']);rules=read_rules(s['Rules6/Data'])
board=Polygon(n['board_outline']);shape=lambda p: Point(p['x'],p['y']).buffer(p['size_x']/2,quad_segs=96) if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5 else Polygon(m.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation']))
pads=[p for p in n['pads'] if p['layer'] in (1,74)];vias=[v for v in n['vias'] if v['net']!='GND']
copper=unary_union([r['geometry'] for r in rs if r['layer']==1 and not r.get('is_cutout',False)]+[shape(p) for p in pads]+[Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=48) for v in vias]+[LineString([(t['x1'],t['y1']),(t['x2'],t['y2'])]).buffer(t['width']/2,quad_segs=32) for t in n['tracks'] if t['layer']==1]).intersection(board)
explicit=unary_union([r['geometry'] for r in rs if r['layer']==37 and r['name'].startswith('SURFACE_MASK_OPEN_')])
rule=next(r for r in rules if r['RULEKIND']=='SolderMaskExpansion' and r.get('SCOPE1EXPRESSION')=='All');exp=float(rule['EXPANSION'].removesuffix('mil'))*.0254
apertures=unary_union([shape(p).buffer(exp,quad_segs=32) for p in pads]);opening=unary_union([explicit,apertures]).intersection(board);mask=board.difference(opening)
# Render the real copper and mask as separate flat layers, without 3D bodies.
scale=22;left=58;top=132;width=550;height=round(67.9*scale)+top+115
im=Image.new('RGB',(width,height),'#f1f3f4');d=ImageDraw.Draw(im);font=lambda sz:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',sz);xy=lambda x,y:(left+x*scale,top+(67.9-y)*scale)
def paint(geom,color):
    layer=Image.new('L',im.size,0);dr=ImageDraw.Draw(layer)
    for g in geom.geoms if hasattr(geom,'geoms') else [geom]:
        if g.is_empty or g.geom_type!='Polygon':continue
        dr.polygon([xy(*p) for p in g.exterior.coords],fill=255)
        for ring in g.interiors:dr.polygon([xy(*p) for p in ring.coords],fill=0)
    im.paste(color,(0,0),layer)
paint(board,'#ad9c48');paint(copper,'#cabc3f');paint(mask,'#365b2e');paint(mask.intersection(copper),'#668b37')
for p in pads:
    if p['hole']:
        x,y=xy(p['x'],p['y']);r=p['hole']/2*scale;d.ellipse((x-r,y-r,x+r,y+r),fill='#f1f3f4')
for v in vias:
    x,y=xy(v['x'],v['y']);covered=mask.covers(Point(v['x'],v['y']));r=v['hole']/2*scale
    d.ellipse((x-r,y-r,x+r,y+r),fill='#45662c' if covered else '#f1f3f4')
d.line([xy(*p) for p in list(board.exterior.coords)],fill='#304a34',width=3)
# Component designators are view annotations, not new silkscreen primitives.
for c in n['components']:
    if c['designator'].startswith('SMP'):d.text(xy(c['x'],c['y']-2.12),c['designator'],font=font(16),fill='#ffffff',anchor='mm',stroke_width=1,stroke_fill='#436029')
    if c['designator']=='J1':
        body=next((b for b in n['bodies'] if b['component']=='J1'),None)
        if body:d.line([xy(*p) for p in body['points']+[body['points'][0]]],fill='#e4e8e4',width=1)
        d.text(xy(9.75,4.65),'J1 / ZIF',font=font(18),fill='#ffffff',anchor='mm')
d.text((38,22),'PCB TOP VIEW',font=font(31),fill='#172935');d.text((38,64),'L1 / SMP + ZIF side',font=font(19),fill='#536574');d.text((38,94),'19.5 x 67.9 mm | 2D mask + copper',font=font(16),fill='#536574')
base=top+67.9*scale+21
d.rectangle((40,base,58,base+18),fill='#668b37');d.text((68,base-1),'Solder mask',font=font(16),fill='#30444e');d.rectangle((280,base,298,base+18),fill='#cabc3f');d.text((308,base-1),'Exposed copper',font=font(16),fill='#30444e')
d.text((38,base+31),'Component bodies omitted; designators annotated.',font=font(14),fill='#536574');d.text((38,base+53),'Saved PCB: '+digest[:20],font=font(14),fill='#536574')
out=P/'docs/PCB_Top_current.png';im.save(out);assert sha(m.SOURCE)==digest
(H/'top_view.json').write_text(json.dumps(dict(source=str(m.SOURCE),sha256=digest,image=str(out),view='Top L1 2D copper and solder mask, no 3D bodies',pad_aperture_expansion_mm=exp,signal_through_vias_on_Top=len(vias),blind_vias_hidden=480),indent=2));print(str(out))
