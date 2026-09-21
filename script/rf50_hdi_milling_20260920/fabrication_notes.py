"""Create fabrication companion files after saved-board validation."""
from pathlib import Path
import json,math,csv
from PIL import Image,ImageDraw,ImageFont
from shapely.geometry import shape
H=Path(__file__).resolve().parent;F=H/'fabrication';F.mkdir(exist_ok=True)
p=json.loads((H/'plan.json').read_text());n=json.loads((H/'planned_native.json').read_text())
assert json.loads((H/'validation.json').read_text())['passed']
points=list(shape(p['cavity']['geometry']).exterior.coords)
gerber=['G04 NON-PLATED BOTTOM BLIND SLOT - DEPTH 1.2 MM*','G04 4.3 X 4.3 MM ENVELOPE - R0.5 INTERNAL CORNERS*','G04 COORDINATES MATCH PCB - DO NOT MIRROR - NOT A THROUGH CUTOUT*','%FSLAX46Y46*%','%MOMM*%','%LPD*%','%ADD10C,0.010*%','D10*','G01*','G36*']
for i,(x,y) in enumerate(points):gerber.append(f'X{round(x*1e6):010d}Y{round(y*1e6):010d}D{2 if i==0 else 1:02d}*')
gerber+=['G37*','M02*'];(F/'bottom blind slots layer.gbr').write_text('\n'.join(gerber)+'\n',encoding='ascii')
with (F/'L5_L6_shield_microvias.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['x_mm','y_mm','start_layer','stop_layer','drill_mm','land_mm','net','type'])
    for v in p['shield_vias']:w.writerow([f"{v['x']:.6f}",f"{v['y']:.6f}",'L6','L5','.100','.250','GND',v['kind']])
with (F/'stackup.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['layer','function','copper_mm','dielectric_below_mm','dielectric_material'])
    for i,(cu,di,mat) in enumerate(zip(p['stack']['copper_mm'],p['stack']['dielectric_mm']+[''],['1078RC69%','0.55 mm core','7628RC50%','0.55 mm core','1078RC69%','']),1):w.writerow([f'L{i}',['GND','DC_A','GND','DC_B','GND reference','RF/QD/RC'][i-1],cu,di,mat])
notes='''# JLCPCB fabrication companion package

Status: saved PCB and footprint verified after reopening; 37 connected nets and zero violations across 15 enabled Altium DRC rules. This is a fabrication companion package, not a complete production CAM release. See manifest.json for the source PCB revision.

## QD cavity

- Keep the central QD cavity 4.3 x 4.3 mm, centred at PCB coordinates (9.75, 42.50) mm.
- Nominal envelope: X=7.60 to 11.90 mm; Y=40.35 to 44.65 mm. Internal corner radius: 0.50 mm.
- Mill from Bottom/L6, the QD wire-bonding side, to a depth of 1.20 mm. Non-plated. Do not make a through cutout.
- Move all QD pad rows radially outward by 0.20 mm. Pad-end opening becomes 4.70 x 4.70 mm; nominal cavity-to-pad clearance is 0.20 mm. Pad sizes remain 1.00 x 0.50 mm.
- Keep L1/Top GND under the pocket floor. Exclude GND from the 4.70 mm pad-end square on L2/L3/L4/L5/L6.
- Nominal copper-plus-dielectric thickness is 1.5884 mm; material remaining after 1.20 mm milling is 0.3884 mm, and the distance from the pocket floor to the inner face of L1 copper is 0.3534 mm. Manufacturing tolerances must be included in the fabricator's review.
- `bottom blind slots layer.gbr` contains the pocket area only, in the same unmirrored XY coordinates as the PCB. Do not merge it with the board outline Gerber. `QD_cavity_drawing.png` gives location and depth.

## RF and HDI

- Controlled impedance target: 50 ohms single-ended coplanar waveguide on L6 with L5 reference. Set 0.110 mm nominal trace width and 0.200 mm coplanar copper gap, following the supplied JLCPCB calculator geometry. Component pads, connectors and bond wires are transitions and are not represented by this uniform-line calculation.
- Requested calculator stack: JLCH06161HN1-1078, nominal 1.6 mm, 6 layers, outer 1 oz and inner 0.5 oz. See `stackup.csv`. The fabricator must confirm material Dk, finished copper, mask and any width compensation; the legacy Altium dielectric constants are not an impedance simulation result.
- GND shield vias: laser blind L6-L5 only, 0.100 mm nominal hole, 0.250 mm land, copper-filled and planarized. No L4/L2/DC drilling. No paste; solid GND connections without thermal relief.
- RF fence: nominal 2.0 mm pitch. Straight sections have 0.510 mm centre offset: 0.055 mm half-trace + 0.330 mm copper-edge gap + 0.125 mm land radius. Four diagonal vias form each active SMP signal ring, with the same nominal 0.330 mm gap from the signal-pad copper edge.
- Remove C1-C6 pad through-vias: both capacitor terminals are routed on L6. Preserve normal capacitor pads and stencil apertures. Preserve QD via-in-pad and required resistor/DC vias.
- QD wire-bonding field is unmasked on Bottom. RF outside that field and solder-control areas retain mask. No via, SMP or mounting-pad paste apertures.

## JLCPCB upload and ordering fields

For production, export the six copper Gerbers, both solder-mask layers, silkscreen as desired, board outline, separate through-drill and L6-L5 laser-drill data, and include the companion blind-slot layer. Include paste Gerbers only when ordering a stencil/assembly. Do not combine laser and through drills. This companion package includes L6_L5_laser_microvias.drl, generated from the 78 saved L5-L6 vias with decimal millimetre coordinates; it is not a through-drill file. Reconcile all final CAM origins and revision hashes before release.

Select Blind Slots = Yes, Bottom entry, non-plated, depth 1.2 mm; attach the location/section drawing. Select the matching HDI stack and impedance control. Use an order remark such as:

> Bottom non-plated blind pocket is specified in bottom blind slots layer.gbr: 4.3 x 4.3 mm, R0.5, 1.2 mm depth from Bottom/QD face. Retain Top copper and the pocket floor. QD pad edge clearance is 0.2 mm nominal. RF is L6 50-ohm coplanar with L5 reference; GND laser vias connect L6-L5 only. Please review the combined HDI, cavity, remaining floor and bond-pad finish before production.

The combined cavity/HDI process and finish suitability for the user's wire-bond material have not been accepted by JLCPCB. No files have been uploaded and no order or supplier contact has been made.

## Official sources checked 2026-09-20

- [Blind-slot file preparation and ordering](https://jlcpcb.com/help/article/how-to-place-an-order-with-blind-slots)
- [Manufacturing capabilities: blind slots and routing](https://jlcpcb.com/capabilities/Capab)
- [HDI capabilities: laser hole, annular ring and impedance tolerance](https://jlcpcb.com/help/article/hdi-pcb-capabilities-faq)
- [Impedance calculator](https://jlcpcb.com/pcb-impedance-calculator/)
- [Calculator assumptions](https://jlcpcb.com/help/article/user-guide-to-the-jlcpcb-impedance-calculator)
'''
(F/'README.md').write_text(notes,encoding='utf-8')
im=Image.new('RGB',(1700,1120),'#f8fafc');d=ImageDraw.Draw(im)
font=lambda s:ImageFont.truetype('C:/Windows/Fonts/arial.ttf',s)
d.text((60,38),'QD blind pocket | fabrication drawing',font=font(38),fill='#14273b');d.text((60,95),'All dimensions in mm. Unmirrored PCB coordinates. Entry from Bottom / L6.',font=font(22),fill='#526578')
scale=91;ox=470;oy=660
xy=lambda x,y:(ox+(x-9.75)*scale,oy-(y-42.5)*scale)
for pad in n['pads']:
    if pad['component']!='Q1':continue
    x,y=pad['x'],pad['y'];a=math.radians(pad['rotation']);cs,sn=math.cos(a),math.sin(a)
    pts=[xy(x+dx*cs-dy*sn,y+dx*sn+dy*cs) for dx,dy in [(-.5,-.25),(.5,-.25),(.5,.25),(-.5,.25)]]
    d.polygon(pts,fill='#b38227');px,py=xy(x,y);d.text((px-8,py-9),pad['number'],font=font(15),fill='white')
cp=[xy(x,y) for x,y in points];d.polygon(cp,fill='#d6e2f0',outline='#244b78',width=3)
d.text((353,635),'4.3 x 4.3',font=font(32),fill='#244b78');d.text((392,678),'R0.50',font=font(23),fill='#244b78')
d.text((66,176),'BOTTOM ENTRY PLAN',font=font(24),fill='#14273b')
def dimension(x1,y1,x2,y2,label):
    d.line((x1,y1,x2,y2),fill='#36556f',width=2)
    if y1==y2:
        for x in (x1,x2):d.line((x,y1-9,x,y1+9),fill='#36556f',width=2)
        d.text(((x1+x2)/2-35,y1-31),label,font=font(22),fill='#36556f')
dimension(*xy(7.6,46.7),*xy(11.9,46.7),'4.30')
dimension(*xy(7.4,46.2),*xy(12.1,46.2),'4.70')
d.text((70,1000),'0.20 nominal clearance from pocket edge to pad end.',font=font(24),fill='#244b78')
d.text((930,176),'SECTION THROUGH CAVITY',font=font(24),fill='#14273b')
sx0,sx1,sy0,sy1=950,1590,340,610
d.rectangle((sx0,sy0,sx1,sy1),fill='#d7e3cd',outline='#77866b',width=2)
d.rectangle((sx0,sy1-7,sx1,sy1),fill='#ae802c')
floor=sy0+270*1.2/1.5884
d.rectangle((1080,sy0,1460,floor),fill='#f8fafc',outline='#244b78',width=2)
d.text((1100,290),'QD / Bottom (L6)',font=font(23),fill='#244b78')
d.text((1100,sy1+17),'Retain Top GND (L1)',font=font(23),fill='#244b78')
d.text((1163,420),'1.20 depth',font=font(22),fill='#244b78')
d.line((1250,365,1250,floor-15),fill='#244b78',width=2);d.polygon([(1243,floor-24),(1257,floor-24),(1250,floor-10)],fill='#244b78')
d.text((935,695),'Non-plated pocket; not a through opening.',font=font(23),fill='#14273b')
d.text((935,735),'Nominal remaining material: 0.3884',font=font(23),fill='#14273b')
d.text((935,775),'Nominal floor-to-L1 copper: 0.3534',font=font(23),fill='#14273b')
d.text((935,865),'Separate file:',font=font(22),fill='#526578');d.text((935,900),'bottom blind slots layer.gbr',font=font(23),fill='#244b78')
d.text((935,1000),'Verified PCB geometry | fabrication companion',font=font(22),fill='#244b78')
im.save(F/'QD_cavity_drawing.png');print('Created fabrication companion files in',F)
