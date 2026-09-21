"""Read-only RF export from the saved PCB's native primitives."""
from pathlib import Path
import importlib.util, json, math, hashlib
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
PROJECT = Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB')
SOURCE = PROJECT / 'QSTL_24DC_4MW_PCB.PcbDoc'
DEST = PROJECT / 'docs' / 'RF_only.png'
spec = importlib.util.spec_from_file_location('native_reader', WORK / 'zif_revision_v2' / 'render_native_layout.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
reader.SOURCE = SOURCE
n = reader.read_native()
(HERE/'native_render_snapshot.json').write_text(json.dumps(n,indent=2))
rf = {f'{prefix}{i}' for prefix in ('S', 'MW') for i in range(1, 5)}
tracks = [t for t in n['tracks'] if t['layer'] == 32 and t['net'] in rf]
arcs = [a for a in n['arcs'] if a['layer'] == 32 and a['net'] in rf]
assert len(tracks) == 19 and len(arcs) == 11
expected = {'MW1': '9', 'MW2': '6', 'MW3': '1', 'MW4': '24'}
assert {p['net']: p['number'] for p in n['pads'] if p['component'] == 'Q1' and p['net'] in rf} == expected

SS = 2
SCALE = 64
MARGIN = 62
TOP = 125
YMAX, YMIN = 50.5, 25.5
WIDTH = round(19.5 * SCALE + 2 * MARGIN)
BOTTOM = round(TOP + (YMAX - YMIN) * SCALE)
HEIGHT = BOTTOM + 117
im = Image.new('RGB', (WIDTH * SS, HEIGHT * SS), '#101820')
d = ImageDraw.Draw(im)
font_path = 'C:/Windows/Fonts/malgun.ttf'
bold_path = 'C:/Windows/Fonts/malgunbd.ttf'
def font(size, bold=False):
    return ImageFont.truetype(bold_path if bold else font_path, round(size * SS))
def xy(x, y):
    return ((MARGIN + x * SCALE) * SS, (TOP + (YMAX - y) * SCALE) * SS)
def text(px, py, content, size=20, fill='#d6e1e9', bold=False, anchor='lt'):
    d.text((px * SS, py * SS), content, font=font(size, bold), fill=fill, anchor=anchor)
def label(x, y, content, color='#d6e1e9', size=19, anchor='mm', bg=True):
    pt = xy(x, y)
    f = font(size, True)
    if bg:
        b = d.textbbox(pt, content, font=f, anchor=anchor)
        d.rounded_rectangle((b[0]-5*SS, b[1]-3*SS, b[2]+5*SS, b[3]+3*SS), radius=3*SS, fill='#101c24')
    d.text(pt, content, font=f, fill=color, anchor=anchor)
def circle(x, y, radius, fill, outline=None, width=1):
    px, py = xy(x, y)
    r = radius * SCALE * SS
    d.ellipse((px-r, py-r, px+r, py+r), fill=fill, outline=outline, width=width*SS)
def poly(points, fill=None, outline=None, width=1):
    points = [xy(*p) for p in points]
    d.polygon(points, fill=fill)
    if outline:
        d.line(points + [points[0]], fill=outline, width=width*SS, joint='curve')
def rectpad(p, fill, outline=None):
    if p['shape'] == 1 and abs(p['size_x']-p['size_y']) < 1e-5:
        circle(p['x'], p['y'], p['size_x']/2, fill, outline)
    else:
        poly(reader.corners(p['x'], p['y'], p['size_x'], p['size_y'], p['rotation']), fill, outline)

colors = {1: '#f5ba59', 2: '#54bdf2', 3: '#ec88bc', 4: '#69d4bd'}
def color(net):
    return colors[int(net[-1])]

text(MARGIN, 27, 'RF 주 경로에 R 패드를 배치', 31, '#ffffff', True)
text(MARGIN, 76, 'L6 RF / QD 면 · 위에서 본 좌표  |  SMP: Top  /  R·C·QD: Bottom', 20, '#a7bac7')
d.rounded_rectangle((MARGIN*SS, TOP*SS, (WIDTH-MARGIN)*SS, BOTTOM*SS), radius=9*SS, fill='#14232c', outline='#344953', width=SS)

# QD's native lands provide orientation without drawing any DC copper.
for p in n['pads']:
    if p['component'] == 'Q1':
        rectpad(p, '#334650')
opening = [(7.60000004,40.34999804),(11.9000016,40.34999804),(11.9000016,44.6499996),(7.60000004,44.6499996)]
poly(opening, '#172a33', '#47606c')
label(9.75,43.05,'QD', '#b8cbd6',24,bg=False)
label(9.75,42.47,'4.3 × 4.3 mm', '#7e99a7',16,bg=False)

# Project the component bodies only as context; copper paths below are native Bottom.
active_rc = {f'{prefix}{i}' for prefix in ('R','C') for i in range(1,5)}
for c in n['components']:
    if c['designator'] not in active_rc:
        continue
    is_cap = c['designator'].startswith('C')
    w,h = (1.0,0.5) if is_cap else (1.6,0.8)
    poly(reader.corners(c['x'],c['y'],w,h,c['rotation']), '#2c3d47', '#65747d')

for t in tracks:
    d.line([xy(t['x1'],t['y1']),xy(t['x2'],t['y2'])], fill=color(t['net']), width=round(t['width']*SCALE*SS))
for a in arcs:
    sweep=(a['end_angle']-a['start_angle'])%360 or 360
    count=max(16,math.ceil(sweep))
    pts=[xy(a['cx']+a['radius']*math.cos(math.radians(a['start_angle']+sweep*i/count)), a['cy']+a['radius']*math.sin(math.radians(a['start_angle']+sweep*i/count))) for i in range(count+1)]
    d.line(pts,fill=color(a['net']),width=round(a['width']*SCALE*SS),joint='curve')

for p in n['pads']:
    if p['net'] in rf:
        rectpad(p, color(p['net']))
        if p['hole']:
            circle(p['x'],p['y'],p['hole']/2,'#101820')
    elif p['component'] in active_rc:
        rectpad(p, '#68757d')
for v in n['vias']:
    if v['net'] in rf:
        circle(v['x'],v['y'],v['diameter']/2,color(v['net']))
        circle(v['x'],v['y'],v['hole']/2,'#101820')

# Label offsets are annotations only; they do not alter the geometry.
labels = [
    (3.1,49.75,'SMP4',4),(16.4,49.75,'SMP3',3),
    (4.3,45.45,'C4',4),(15.2,45.45,'C3',3),
    (5.85,48.8,'R4',4),(13.65,48.8,'R3',3),
    (16.4,33.15,'SMP2',2),(17.55,41.20,'C2',2),(15.05,43.05,'R2',2),
    (16.4,26.23,'SMP1',1),(15.20,29.15,'C1',1),(13.65,32.6,'R1',1),
    (8.05,44.24,'24',4),(11.45,44.24,'1',3),(11.20,42.15,'6',2),(13.10,39.85,'9',1),
]
for x,y,s,ch in labels:
    label(x,y,s,colors[ch],21 if s.startswith('SMP') else 19)
label(11.75,33.2,'MW1',colors[1],17,anchor='rm')
label(14.1,42.63,'MW2',colors[2],17)
label(12.93,46.70,'MW3',colors[3],17)
label(6.50,46.70,'MW4',colors[4],17)

# Compact, exact connection key in the empty lower-left region.
label(1.0,35.25,'현재 연결', '#cbdce6',19,anchor='lm',bg=False)
for ch,y in [(1,34.45),(2,33.73),(3,33.01),(4,32.29)]:
    label(1.0,y,f'SMP{ch} → C{ch} → QD {expected[f"MW{ch}"]}  ·  R{ch}',colors[ch],18,anchor='lm',bg=False)

text(MARGIN, BOTTOM+23, 'RF가 R의 RF측 패드 중심을 통과. R 가지 배선 없음. R–C 패드 간격 약 0.21 mm.', 18, '#a7bac7')
text(MARGIN, BOTTOM+57, '저장된 PcbDoc의 실제 좌표로 렌더링', 17, '#7e99a7')
text(WIDTH-MARGIN, BOTTOM+57, f'SHA-256  {n["source_sha256"][:16]}…',15,'#708a99',anchor='rt')

assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == n['source_sha256']
im.resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS).save(DEST)
report = {'source':str(SOURCE),'source_sha256':n['source_sha256'],'image':str(DEST),'layer':32,'tracks':len(tracks),'arcs':len(arcs),'nets':sorted(rf),'qd_pins':expected,'view':'top coordinates; bottom RC and QD projected','design_modified':False}
(HERE/'RF_only_export.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
