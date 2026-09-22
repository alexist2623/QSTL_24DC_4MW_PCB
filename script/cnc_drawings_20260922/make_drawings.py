"""Create dimensioned A3 CNC and assembly sheets from verified STEP projections."""
from pathlib import Path
import json, math, textwrap, hashlib, shutil, csv, zipfile
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
MODEL=ROOT/'QSTL_24DC_4MW_PCB'/'Mechanical_Assembly'/'Rod_Holder_Adapter_Drop8p5'
OUT=MODEL/'Manufacturing'
OUT.mkdir(exist_ok=True)
GEOM=json.loads((HERE/'drawing_geometry.json').read_text(encoding='utf-8'))
VERIFY=json.loads((MODEL/'geometry_verification.json').read_text())
PDF=OUT/'QSTL_Split_Mount_CNC_and_Assembly_RevA.pdf'
MM=72/25.4
for name,file in [('Arial','arial.ttf'),('Arial-Bold','arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(Path('C:/Windows/Fonts')/file)))
C=canvas.Canvas(str(PDF),pagesize=(420*MM,297*MM),pageCompression=1)
C.setTitle('QSTL split mounting plate - CNC and assembly drawings - Rev A')
C.setAuthor('QSTL engineering')
INK=HexColor('#172b3a');BLUE=HexColor('#236e88');TEAL=HexColor('#28998d');GRAY=HexColor('#687786');LIGHT=HexColor('#e7edf1');RED=HexColor('#aa3b31')
TEXT_BOXES=[]

def line(x1,y1,x2,y2,w=.22,color=INK,dash=None):
    C.setStrokeColor(color);C.setLineWidth(w*MM);C.setDash([v*MM for v in dash] if dash else [])
    C.line(x1*MM,y1*MM,x2*MM,y2*MM);C.setDash([])
def rect(x,y,w,h,fill=None,stroke=INK,lw=.22):
    C.setStrokeColor(stroke);C.setLineWidth(lw*MM);C.setFillColor(fill or white)
    C.rect(x*MM,y*MM,w*MM,h*MM,stroke=1,fill=bool(fill))
def text(x,y,s,size=9,bold=False,color=INK,align='left',angle=0):
    C.saveState();C.setFillColor(color);C.setFont('Arial-Bold' if bold else 'Arial',size)
    C.translate(x*MM,y*MM);C.rotate(angle)
    getattr(C,{'left':'drawString','center':'drawCentredString','right':'drawRightString'}[align])(0,0,str(s));C.restoreState()
def para(x,y,s,width,size=9,leading=4.7,color=INK,bold=False):
    font='Arial-Bold' if bold else 'Arial';words=s.split();out=[];cur=''
    for word in words:
        trial=(cur+' '+word).strip()
        if pdfmetrics.stringWidth(trial,font,size)>width*MM and cur:out.append(cur);cur=word
        else:cur=trial
    if cur:out.append(cur)
    for row in out:text(x,y,row,size,bold,color);y-=leading
    return y
def circle(x,y,r,fill=None,stroke=INK,lw=.22):
    C.setLineWidth(lw*MM);C.setStrokeColor(stroke);C.setFillColor(fill or white)
    C.circle(x*MM,y*MM,r*MM,stroke=1,fill=bool(fill))
def poly(points,fill=None,stroke=INK,lw=.25,close=True):
    p=C.beginPath();p.moveTo(points[0][0]*MM,points[0][1]*MM)
    for x,y in points[1:]:p.lineTo(x*MM,y*MM)
    if close:p.close()
    C.setFillColor(fill or white);C.setStrokeColor(stroke);C.setLineWidth(lw*MM);C.drawPath(p,stroke=1,fill=bool(fill))
def arrow(tip,tail,size=1.8,color=INK):
    dx=tail[0]-tip[0];dy=tail[1]-tip[1];length=math.hypot(dx,dy)
    if length==0:return
    ux,uy=dx/length,dy/length
    poly([tip,(tip[0]+size*ux+.32*size*uy,tip[1]+size*uy-.32*size*ux),(tip[0]+size*ux-.32*size*uy,tip[1]+size*uy+.32*size*ux)],fill=color,stroke=color,lw=.1)
def dimh(x1,x2,y,ref,label,size=8.5):
    line(x1,ref,x1,y+2,.13);line(x2,ref,x2,y+2,.13);line(x1,y,x2,y,.15)
    arrow((x1,y),(x2,y));arrow((x2,y),(x1,y))
    tw=pdfmetrics.stringWidth(label,'Arial',size)/MM
    C.setFillColor(white);C.rect(((x1+x2-tw)/2-1)*MM,(y-1.2)*MM,(tw+2)*MM,4*MM,stroke=0,fill=1)
    text((x1+x2)/2,y-.1,label,size,align='center')
def dimv(y1,y2,x,ref,label,size=8.5):
    line(ref,y1,x-2,y1,.13);line(ref,y2,x-2,y2,.13);line(x,y1,x,y2,.15)
    arrow((x,y1),(x,y2));arrow((x,y2),(x,y1))
    text(x-1.4,(y1+y2)/2,label,size,align='center',angle=90)
def leader(label,tx,ty,px,py,width=90,size=9):
    y=para(tx,ty,label,width,size,4.5)
    ex=tx+min(width,28);ey=y+3
    line(px,py,ex,ey,.18);arrow((px,py),(ex,ey),1.5)
def cross(x,y,r=3):
    line(x-r,y,x+r,y,.13,GRAY,[2,.7,.5,.7]);line(x,y-r,x,y+r,.13,GRAY,[2,.7,.5,.7])
def table(x,top,width,headers,rows,colfracs,size=8.6,rowh=7):
    widths=[width*f/sum(colfracs) for f in colfracs]
    rect(x,top-rowh,width,rowh,LIGHT,lw=.18)
    left=x
    for w,h in zip(widths,headers):text(left+2,top-rowh+2,h,size,True);left+=w
    y=top-rowh
    for row in rows:
        y-=rowh;rect(x,y,width,rowh,stroke=LIGHT,lw=.16);left=x
        for w,v in zip(widths,row):text(left+2,y+2,str(v),size);left+=w
    return y
def projection(part,view,x,y,scale=1,hidden=True):
    data=GEOM[part]['projections'][view]
    for kind in (['hidden','visible'] if hidden else ['visible']):
        for points in data[kind]:
            if len(points)<2:continue
            C.setLineWidth((.12 if kind=='hidden' else .28)*MM)
            C.setStrokeColor(GRAY if kind=='hidden' else INK);C.setDash([2*MM,1*MM] if kind=='hidden' else [])
            p=C.beginPath();p.moveTo((x+scale*points[0][0])*MM,(y+scale*points[0][1])*MM)
            for a,b in points[1:]:p.lineTo((x+scale*a)*MM,(y+scale*b)*MM)
            C.drawPath(p)
    C.setDash([])
def imagefit(path,x,y,w,h):
    reader=ImageReader(str(path));iw,ih=reader.getSize();s=min(w/iw,h/ih)
    C.drawImage(reader,(x+(w-iw*s)/2)*MM,(y+(h-ih*s)/2)*MM,iw*s*MM,ih*s*MM,mask='auto')
def header(sheet,number,title,scale='AS SHOWN',material='OFC',qty='1 / assembly'):
    rect(7,7,406,283,lw=.35)
    text(13,281,'QSTL  /  CRYOGENIC DEVICE MOUNT',10,True,BLUE)
    text(13,269,title,17,True)
    rect(286,277,120,8,HexColor('#fff0e8'),RED,.2)
    text(346,279.5,'FOR QUOTATION / DFM - NOT RELEASED',8,True,RED,'center')
    line(13,264,407,264,.25)
    # Stable title block separates part identification from release status.
    rect(7,7,406,26,lw=.3);line(7,20,413,20,.2)
    for xx in (72,170,260,328,373):line(xx,7,xx,33,.18)
    text(11,27,'DRAWING',6.5,color=GRAY);text(11,22,sheet,10,True)
    text(76,27,'PART / SUBJECT',6.5,color=GRAY);text(76,22,number,9,True)
    text(174,27,'MATERIAL / SURFACE TREATMENT',6.5,color=GRAY);text(174,22,material+' / NONE',9)
    text(264,27,'UNITS / SCALE',6.5,color=GRAY);text(264,22,'mm / '+scale,9)
    text(332,27,'QTY',6.5,color=GRAY);text(332,22,qty,8.5)
    text(377,27,'REV / SHEET',6.5,color=GRAY);text(377,22,'A / '+str(PAGE)+' of 7',9,True)
    text(11,12,'2026-09-22',9);text(76,12,'DO NOT SCALE DRAWING',8.5,True)
    text(174,12,'Production conditions: sheet G01',8.5);text(264,12,'A3 landscape',9)
    text(332,12,'CAD verified',8.5);text(377,12,'DRAFT',8.5,True,RED)
def end():C.showPage()
def note_block(x,y,title,items,width=170):
    text(x,y,title,10,True,BLUE);y-=7
    for i,item in enumerate(items,1):y=para(x,y,f'{i}. {item}',width,9,4.8)-3
    return y

# Sheet G01: all production assumptions and release holds are explicit.
PAGE=1;header('QSTL-G01','GENERAL','Manufacturing scope and drawing register',qty='Batch TBD')
text(15,252,'SCOPE',11,True,BLUE)
para(15,245,'CNC manufacture three parts for one mounting set. The existing flat plate and the source carrier, PCB, rods and sleeve are unchanged. Supply the three STEP parts together with this drawing set.',184,10,5.3)
text(15,220,'DRAWING REGISTER',10,True,BLUE)
table(15,213,181,['Sheet','Subject'],[
    ['P01','Central plate - geometry and hole coordinates'],['P02','Central plate - thread and countersink details'],
    ['P03','Left rod support - machining drawing'],['P04','Right rod support - machining drawing'],
    ['A01','Exploded assembly, BOM and assembly sequence'],['A02','Installation, centre alignment and checks']], [1,5],9,8)
note_block(15,150,'COORDINATES AND DIMENSION RULES',[
    'All dimensions are millimetres. Dimensions govern; do not measure printed images. View directions are named explicitly.',
    'Each part has a local O origin. X/Y/Z values and hole schedules use that origin. STEP origin offsets are printed on each part sheet.',
    'Solid lines: visible CAD edges. Dashed lines: hidden edges. Sections show nominal geometry; threads are simplified.',
    'Three-decimal dimensions are nominal registration coordinates, not implied micrometre tolerances. No general tolerance has been approved.'
],184)
text(219,252,'FABRICATION RELEASE CHECKLIST',11,True,RED)
items=[
('01  Confirmed material / no treatment','All three machined parts: oxygen-free copper (OFC); no plating, coating or other surface treatment. Supplier shall declare the exact OFC grade and temper and provide a material certificate. Fastener material remains separate.'),
('02  Tolerances and contact faces','Agree linear/position tolerances, flatness and contact-face roughness. Suggested RFQ basis only: general ±0.10 mm; critical heights / hole coordinates ±0.05 mm; flatness 0.05 mm; contact Ra 1.6 µm.'),
('03  Blind-thread tooling','CAD has flat-bottom pilot bores with nominal thread depth equal to bore depth. Shop must confirm usable thread, runout and tool clearance. Do not add drill depth through the opposed 1.5 mm boss web.'),
('04  Countersunk screws','Select M3 x 10, 90° heads compatible with the Ø6.2 seats. Current envelope uses head Ø6.0. Larger-head variants require reassessment; a generic standard name is insufficient.'),
('05  Sleeve / frame envelope','Existing rods, support outer corners and original rod screw heads intersect the Ø51 sleeve. Do not force the sleeve onto the assembly. Resolve that fit before installation release.'),
('06  Edges and process','Remove burrs. No burrs, coating buildup or uncontrolled corner radii on mating faces. Propose machining radii, thread entry breaks and pilot-bottom method at DFM review.')]
y=244
for title,body in items:
    text(219,y,title,9.6,True);y=para(219,y-5,body,185,8.8,4.4)-6
text(15,43,'Status: complete nominal drawing package for quotation and DFM; manufacturing release requires closure of the listed items.',9,True,RED)
end()

# P01: central plate, exact visible / hidden edges from source STEP.
PAGE=2;header('QSTL-P01','CP-01','Central plate with integral device boss','1.8:1 / 2:1')
ox,oy,s=52,82,1.8
projection('Centre_Plate','xy_boss',ox,oy,s)
text(ox+35,238,'BOSS-FACE PLAN (+Z)',10,True,align='center')
text(ox+35,231,'Scale 1.8:1; countersinks on opposite face A',8,align='center')
dimh(ox,ox+39*s,70,oy,'39.000')
dimv(oy,oy+80*s,34,ox,'80.000')
for x in (3.5,35.5):
    for y in (10,30,50,70):cross(ox+x*s,oy+y*s,3.5)
text(ox-2,oy-5,'O',8,True)
line(ox,oy,ox+12,oy,.2,BLUE);arrow((ox+12,oy),(ox,oy),1.6,BLUE);text(ox+13,oy-1,'+X',8,color=BLUE)
line(ox,oy,ox,oy+12,.2,BLUE);arrow((ox,oy+12),(ox,oy),1.6,BLUE);text(ox-6,oy+14,'+Y',8,color=BLUE)
projection('Centre_Plate','end',ox,43,s)
text(ox+35,37,'END VIEW (-Y), scale 1.8:1',8,align='center')
dimv(43,43+10*s,138,ox+39*s,'10.000')
text(160,248,'SIDE VIEW (+X) - five threads visible, opposite five hidden',9.5,True)
projection('Centre_Plate','side',170,211,2)
dimh(178,322,241,231,'72.000 boss length')
text(170,203,'Boss starts at Y=4.000; ends at Y=76.000. Side thread centre Z=7.000.',8.5)
text(163,188,'H1: 8 x COUNTERSUNK CLEARANCE',10,True,BLUE)
text(163,181,'Ø3.400 THRU; Ø6.200 x 90° from outer face A (Z=0).',9)
table(163,175,237,['Row','X left','X right','Y'],[[str(i+1),'3.500','35.500',f'{y:.3f}'] for i,y in enumerate((10,30,50,70))],[1,1.5,1.5,2],9,7)
text(163,132,'H2: 5 x M3 x 0.5 - 6H PER SIDE (10 TOTAL)',10,True,BLUE)
text(163,125,'Entries at X=13.933375831 and 27.433375831; axes ±X; Z=7.000.',8.5)
table(163,119,237,['Hole row','Y from end C','Y pitch','Nominal depth'],[[str(i+1),f'{9.828023665+16*i:.3f}','16.000','6.000 each side'] for i in range(5)],[1,2,1.5,2.5],9,7)
note_block(163,70,'PART NOTES',[
    'Deck thickness 4.000; boss height above deck 6.000. See P02 for sections and blind-thread requirements.',
    'Local O = model (6, 0, 0). A: outer deck face Z=0; B: X=0 edge; C: Y=0 end. Use model for unrounded registration.'
],237)
end()

# P02: deliberate enlarged sections keep machining depth unambiguous.
PAGE=3;header('QSTL-P02','CP-01 DETAILS','Central plate - sections and machining details','4:1 / 8:1')
text(18,251,'SECTION S1 - THROUGH A BOSS THREAD ROW',11,True,BLUE)
text(18,244,'Nominal section at Y=25.828023665; viewed toward +Y. Scale 4:1.',9)
x,y,k=27,174,4
bx=13.933375831;bw=13.5
poly([(x,y),(x+39*k,y),(x+39*k,y+4*k),(x+(bx+bw)*k,y+4*k),(x+(bx+bw)*k,y+10*k),(x+bx*k,y+10*k),(x+bx*k,y+4*k),(x,y+4*k)],LIGHT)
for xx in (bx,bx+bw-6):rect(x+xx*k,y+5.75*k,6*k,2.5*k,white,lw=.25)
line(x+(bx-2)*k,y+7*k,x+(bx+bw+2)*k,y+7*k,.12,GRAY,[3,1,.5,1])
dimh(x+bx*k,x+(bx+bw)*k,226,y+10*k,'13.500')
dimh(x+bx*k,x+(bx+6)*k,162,y+5.75*k,'6.000')
dimh(x+(bx+7.5)*k,x+(bx+bw)*k,162,y+5.75*k,'6.000')
dimv(y,y+4*k,18,x,'4.000');dimv(y+4*k,y+10*k,194,x+39*k,'6.000')
leader('1.500 solid web between nominal bore bottoms',45,147,x+(bx+6.75)*k,y+7*k,135,9)
text(220,251,'DETAIL S2 - H1 COUNTERSINK',11,True,BLUE)
text(220,244,'Outer face A shown at bottom; scale 8:1.',9)
xx,yy,kk=274,185,8
rect(xx-5*kk,yy,10*kk,4*kk,LIGHT)
poly([(xx-3.1*kk,yy),(xx+3.1*kk,yy),(xx+1.7*kk,yy+1.4*kk),(xx+1.7*kk,yy+4*kk),(xx-1.7*kk,yy+4*kk),(xx-1.7*kk,yy+1.4*kk)],white)
line(xx,yy-6,xx,yy+4*kk+6,.13,GRAY,[3,1,.5,1])
dimh(xx-3.1*kk,xx+3.1*kk,yy-10,yy,'Ø6.200')
dimh(xx-1.7*kk,xx+1.7*kk,yy+4*kk+10,yy+4*kk,'Ø3.400 THRU')
dimv(yy,yy+4*kk,xx+5*kk+13,xx+5*kk,'4.000')
text(274,194,'90°',10,True,align='center')
text(220,162,'Countersink axial depth = 1.400 REF.',9)
text(220,155,'Nominal head Ø6.000 -> 0.100 recess REF.',9)
text(220,148,'Current small edge ligament: 0.400 REF at the seat.',9)
note_block(18,122,'H2 BLIND-THREAD PROCESS REQUIREMENT',[
    '10 x M3 x 0.5 - 6H, right-hand, nominal depth 6.000 from each boss side face. Model pilot Ø2.500 has a flat bottom at the same depth.',
    'Do not interpret the model as permission to add a conventional drill tip beyond 6.000. Opposed holes leave only a 1.500 nominal central web.',
    'Vendor must confirm a flat-bottom boring / thread-milling process and usable thread. Standard tapping requires a separate runout / depth review.',
    'No through-drilling, cross-connection of opposed holes or extra depth without a revised drawing. Inspect both rows with agreed thread gauges.'
],185)
note_block(220,122,'H1 FASTENER AND EDGE REQUIREMENT',[
    'M3 x 10 length includes the countersunk head. Specify 90° included angle and verify actual head diameter against the Ø6.200 seats.',
    'Do not substitute a larger-head screw based only on the M3 designation. Verify head flushness, thread engagement and driver access before tightening.',
    'Preserve boss / deck contact faces. Agree corner radii and edge breaks with the mating holder; do not remove the narrow seat-to-edge ligament.',
    'Oxygen-free copper; no surface treatment. Final production tolerances and tooling remain subject to G01.'
],184)
end()

def support_sheet(side,page):
    global PAGE
    PAGE=page;left=side=='Left';part=side+'_Rod_Support';code='LS-01' if left else 'RS-01'
    header('QSTL-P03' if left else 'QSTL-P04',code,side+' rod support - separate machined part','2:1 / 4:1')
    ox,oy,s=59,77,2
    projection(part,'xy_boss',ox,oy,s)
    text(ox+12,249,'ROD-FACE PLAN (+Z)',10,True,align='center')
    text(ox+12,243,'Scale 2:1; blind threads enter from opposite face',8,align='center')
    dimh(ox,ox+24,64,oy,'12.000');dimv(oy,oy+160,38,ox,'80.000')
    cx=3 if left else 9;tx=9.5 if left else 2.5
    for yy in (5,25,45,65):cross(ox+cx*s,oy+yy*s,3)
    for yy in (10,30,50,70):cross(ox+tx*s,oy+yy*s,3)
    text(ox-2,oy-5,'O',8,True)
    text(112,251,'END PROFILE (-Y)',11,True,BLUE)
    projection(part,'end',139,191,4)
    dimh(139,187,180,191,'12.000')
    dimv(191,225,204,187,'8.500')
    dimv(209,225,120,139,'4.000 flange')
    dimh(139+(6 if left else 0)*4,139+(12 if left else 6)*4,235,225,'6.000 web')
    text(113,169,'Deck joint face A: local Z=0.',9)
    text(113,163,'Rod contact face: local Z=8.500.',9)
    text(230,251,'SECTION T - BLIND DECK THREAD',11,True,BLUE)
    text(230,244,'Section along thread axis; scale 4:1.',9)
    xx,yy,kk=283,192,4
    rect(xx-3*kk,yy,6*kk,8.5*kk,LIGHT)
    rect(xx-1.25*kk,yy,2.5*kk,6.5*kk,white)
    line(xx,yy-5,xx,yy+8.5*kk+4,.12,GRAY,[3,1,.5,1])
    dimv(yy,yy+6.5*kk,318,xx+3*kk,'6.500 nominal')
    dimv(yy+6.5*kk,yy+8.5*kk,341,xx+3*kk,'2.000 wall REF')
    text(240,182,'4 x M3 x 0.5 - 6H; right-hand.',9,True)
    text(240,175,'Entry from A; Ø2.500 flat-bottom pilot.',9)
    text(112,145,'H1 - ROD SCREW CLEARANCE',10,True,BLUE)
    table(112,137,128,['Count','X','Y positions'],[['4',f'{cx:.3f}','5 / 25 / 45 / 65']],[1,1.2,4],9,8)
    text(112,113,'Ø3.400 THRU the 4.000 flange.',9)
    text(263,145,'H2 - DECK JOIN THREADS',10,True,BLUE)
    table(263,137,138,['Count','X','Y positions'],[['4',f'{tx:.3f}','10 / 30 / 50 / 70']],[1,1.2,4],9,8)
    text(263,113,'M3 x 0.5 - 6H, 6.500 nominal.',9)
    note_block(112,98,'PART NOTES',[
        f'Local O = model ({0 if left else 39}, 0, 4). A: deck joint Z=0; B: X=0 side; C: Y=0 end. Do not interchange left / right coordinates.',
        'G01 blind-thread process hold applies. Nominal screw engagement 6.100; bore-bottom clearance 0.400. Confirm usable thread with the actual screw.',
        'Retain full 6 x 80 rod-contact footprint and full deck-contact strip. No burrs or uncontrolled fillets on these interfaces.'
    ],288)
    end()
support_sheet('Left',4);support_sheet('Right',5)

# Assembly drawing: exploded CAD image, precise hardware schedule and ordered instructions.
PAGE=6;header('QSTL-A01','ASM-01','Exploded assembly and assembly method','NTS',material='CP/LS/RS: OFC',qty='1 set')
imagefit(HERE/'tmp'/'cnc_exploded.png',17,82,186,174)
text(21,251,'EXPLODED VIEW - THREE MACHINED PARTS',10,True,BLUE)
text(32,80,'2  LS-01',9,True,TEAL,'center')
text(110,80,'1  CP-01',9,True,BLUE,'center')
text(185,80,'3  RS-01',9,True,TEAL,'center')
leader('4  M3 x 10 (8x)',21,225,89,208,46,8.5)
text(25,73,'Boss faces away from this view. Screws enter the outer deck face.',8)
table(213,252,190,['Item','Qty','Description'],[
    ['1','1','CP-01 central plate with boss'],['2','1','LS-01 left rod support'],['3','1','RS-01 right rod support'],
    ['4','8','M3 x 10 countersunk deck screws'],['5','8','Existing M3 x 8 rod screws'],['6','2','Existing M3 x 8 device screws'],
    ['7','1','Existing carrier + PCB assembly'],['8','1','Existing H frame'],['9','1','Ø51 ID / Ø54 OD sleeve, fit hold']], [1,1,7],8.7,7)
text(213,174,'ASSEMBLY SEQUENCE',10,True,BLUE)
steps=[
    'Inspect and clean all contact faces; remove chips from blind holes. Verify handedness using P03 / P04. Keep the sleeve off.',
    'Place the central plate outer/countersunk face downward. Put left and right supports against the two deck strips, with rod flanges outward.',
    'Insert eight item-4 screws from the countersunk face. Align all holes and start each by hand. Tighten progressively, alternating sides and middle / end rows.',
    'Attach the device through its existing side slots with two item-6 screws. Preserve the confirmed ZIF-up orientation. Do not clamp the PCB or use the boss as a cover.',
    'Locate the assembly on the back faces of the rods. Start eight item-5 screws in the existing rows, then align and tighten uniformly.',
    'Verify contact gaps, head seating and the pocket reference point. Apply final torque only after screw material, substrate and lubrication are specified.',
    'Fit the sleeve only after the existing envelope clashes on A02 have been resolved. Do not force assembly or use screws to pull an interference fit together.'
]
y=167
for i,body in enumerate(steps,1):y=para(213,y,f'{i:02d}  {body}',190,8.6,4.35)-3.2
note_block(18,62,'HARDWARE CONTROL',[
    'Item 4: M3 x 10, 90°, head diameter compatible with Ø6.2 seat. Actual screw specification / material TBD; simplified CAD is not a procurement specification.',
    'No torque value, lubricant, threadlocker or washer substitution is authorized by this drawing. Batch quantity remains TBD.'
],187)
end()

# A02: installation locations, nominal alignment and real envelope limitation.
PAGE=7;header('QSTL-A02','ASM-01 INSTALL','Installation, section and final inspection','AS SHOWN',material='CP/LS/RS: OFC',qty='1 set')
text(18,251,'INSTALLATION ON THE UNCHANGED H FRAME',10,True,BLUE)
ox,oy,sc=32,75,1.7
rect(ox,oy,51*sc,80*sc,fill=HexColor('#f1f7f8'))
rect(ox,oy,6*sc,80*sc,fill=HexColor('#d9c0aa'))
rect(ox+45*sc,oy,6*sc,80*sc,fill=HexColor('#d9c0aa'))
for x in (3,48):
    for yy in (5,25,45,65):circle(ox+x*sc,oy+yy*sc,1.7*sc);cross(ox+x*sc,oy+yy*sc,3)
for x in (9.5,41.5):
    for yy in (10,30,50,70):circle(ox+x*sc,oy+yy*sc,1.25*sc,fill=LIGHT)
dimh(ox,ox+51*sc,64,oy,'51.000 overall')
dimh(ox+3*sc,ox+48*sc,232,oy+80*sc,'45.000 rod axes')
dimv(oy,oy+80*sc,19,ox,'80.000')
text(ox,218,'Y=215 at upper plate end',8.5)
text(ox,68,'Y=135 at lower plate end',8.5)
text(22,244,'Rod-screw axes / deck-screw axes; scale 1.7:1',8.5)
text(142,251,'SPLIT JOINT SECTION',10,True,BLUE)
imagefit(MODEL/'Split_joint_section.png',137,146,265,99)
text(144,140,'Section at deck-screw row Y=165; illustration NTS. Dimensions / hardware per P01-P04 and A01.',8)
table(145,132,255,['Feature','Assembly coordinates / nominal condition'],[
    ['Rod screw rows','X=3, 48; Y=140, 160, 180, 200; enter +Z'],
    ['Deck screw rows','X=9.5, 41.5; Y=145, 165, 185, 205; enter +Z'],
    ['Device screw axes','Y=160.828, 176.828; Z=-5.500; enter +X'],
    ['Tube axis','X=25.500; Z=3.000; direction parallel Y'],
    ['Pocket reference P','X=25.500; Y=175.691382; Z=3.000'],
    ['Definition of P','Pocket floor centre + 0.300 toward cavity opening (-Z)']], [2,6],8.8,7)
text(145,79,'ACCEPTANCE CHECKS',9.5,True,BLUE)
para(145,73,'Confirm zero visible gaps at rod and deck interfaces; no rocking; all countersunk heads seated; actual screw engagement and no bottoming; ZIF orientation correct. Inspect P relative to the cylinder axis after tightening. Model coincidence is not a production tolerance.',255,8.8,4.5)
text(18,53,'SLEEVE FIT HOLD',9.5,True,RED)
para(18,47,'Existing sleeve clashes remain at rod corners, outer support corners and original rod screw heads. New deck screws and lowered carrier are clear. Resolve clashes before installation; this package does not alter the sleeve or rods.',383,8.8,4.5,RED)
end();C.save()

# Supply immutable geometry copies and an auditable source manifest with the PDF.
steps_dir=OUT/'STEP';steps_dir.mkdir(exist_ok=True)
manifest=[]
for name,code in [('Centre_Plate','CP-01'),('Left_Rod_Support','LS-01'),('Right_Rod_Support','RS-01'),('Rod_Holder_Assembly_Drop8p5','ASM-01')]:
    src=MODEL/(name+'.step');dest=steps_dir/(code+'_'+name+'.step');shutil.copy2(src,dest)
    manifest.append(dict(part=code,source=str(src),file='STEP/'+dest.name,sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
rows=[['Item','Part','Description','Quantity_per_assembly','Procurement_status'],
      [1,'CP-01','Central plate with integral boss',1,'Oxygen-free copper; no surface treatment'],
      [2,'LS-01','Left rod support',1,'Oxygen-free copper; no surface treatment'],
      [3,'RS-01','Right rod support',1,'Oxygen-free copper; no surface treatment'],
      [4,'HW-01','M3 x 10 countersunk 90 deg, compatible head diameter',8,'Actual screw grade / head specification TBD'],
      [5,'EX-01','Existing M3 x 8 rod screws',8,'Existing assembly'],
      [6,'EX-02','Existing M3 x 8 device screws',2,'Existing assembly']]
with (OUT/'BOM.csv').open('w',newline='',encoding='utf-8-sig') as f:csv.writer(f).writerows(rows)
(OUT/'source_manifest.json').write_text(json.dumps(dict(revision='A',status='For quotation / DFM; not released',date='2026-09-22',units='mm',part_hole_count=34,geometry_files=manifest),indent=2),encoding='utf-8')
(OUT/'README.md').write_text('''# CNC quotation and assembly package - Rev A

The seven-sheet A3 PDF includes general manufacturing requirements, two central-plate sheets, separate left/right support drawings, exploded assembly/BOM/sequence, and installation/inspection details. All geometry projections were computed directly from the saved STEP solids. All 34 hole locations were independently checked. Native CAD and source STEP geometry were not modified.

Supply the PDF and all three part STEP files together. The complete assembly STEP is a fit reference, not an additional machined item. Do not scale the PDF. The attached coordinate schedules use part-local origins printed on each sheet; supplied STEP files retain their original shared coordinate system.

## Release status

This is a complete nominal drawing set for quotation and design-for-manufacture review, not an approved fabrication release. The user confirmed oxygen-free copper (OFC) with no surface treatment for all three machined parts. The supplier must declare the exact grade/temper and provide a material certificate. Batch quantity and tolerances await confirmation. Flat-bottom blind-thread processing, actual countersunk screws, edge conditions and existing sleeve/rod interference also require closure. No supplier was contacted, purchase placed, model geometry changed or Git push performed.

The RFQ tolerance values on G01 are explicit proposals only. They are not approved acceptance limits. Existing CAD thread metadata has equal nominal bore and thread depths; a generic drill-and-tap interpretation would be misleading. P02 and P03/P04 therefore state the actual geometry and require a tooling review. Actual screw heads must fit the 6.2 mm countersinks; a generic M3 / ISO designation is not sufficient.

## Technical source checks

- Bossard's small-head M3 example lists a 6.0 mm maximum head and 90-degree angle: https://americas.bossard.com/products/1022792.html . This linked 14 mm product is a head-dimension reference only, not the required 10 mm procurement item.
- Wuerth's ISO 10642-type M3 x 10 example lists a 6.72 mm head: https://eshop.wuerth.de/Sicherheitsschraube-mit-Innensechsrund-u-Pin-ISO-10642-aehnlich-aufgrund-des-TX-Antrieb-Edelstahl-A2-blank-SHR-ISO10642-A2/070-TX10-PIN-M3X10/028403%2010.sku/de/DE/EUR/ . It is not an approved substitute.
- Sandvik Coromant, Threading Application Guide, thread-milling discussion: https://cdn2.sandvik.coromant.com/files/a53b485b-be0f-019d-8100-3f0d1619b9fa/5370939c-6de5-4b34-a938-2fa290a42316/c-2920-031.pdf . Bottom access depends on tool and process; supplier feasibility is required for these small blind holes.

Source files and SHA-256 hashes are recorded in source_manifest.json. Helpers live in repository-root script/cnc_drawings_20260922/.
''',encoding='utf-8')
reader=PdfReader(str(PDF));assert len(reader.pages)==7
for i,p in enumerate(reader.pages):
    txt=p.extract_text();assert 'QSTL-' in txt and 'NOT RELEASED' in txt,(i,txt)
    assert abs(float(p.mediabox.width)-420*MM)<.01
    assert abs(float(p.mediabox.height)-297*MM)<.01
for name in ('Centre_Plate','Left_Rod_Support','Right_Rod_Support'):
    assert hashlib.sha256((MODEL/(name+'.step')).read_bytes()).hexdigest()==GEOM[name]['sha256']
archive=OUT.parent/'QSTL_Split_Mount_CNC_Package_RevA.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(OUT))
print(json.dumps(dict(pdf=str(PDF),sheets=7,package=str(archive),source_models_unchanged=True),indent=2))
