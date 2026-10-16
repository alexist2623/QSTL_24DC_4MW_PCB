"""Read-only reference carrier mounting-hole extraction and annotated drawing."""
import importlib.util
import json
from pathlib import Path
import re
import struct
import zipfile
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, Rectangle

ROOT = Path(__file__).resolve().parents[2]
REF = Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/PCB/Sample_Holder')
OUT = ROOT / 'QSTL_QD4_2SET_38PAD/Reference12_Mounting_Holes_20261015'
spec = importlib.util.spec_from_file_location('native_reader', ROOT/'script/_support/zif_revision_v2/render_native_layout.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def extract():
    path = REF/'Sample_Holder.PcbDoc'
    before = reader.sha(path)
    with reader.olefile.OleFileIO(path) as ole:
        components = reader.props(ole.openstream('Components6/Data').read())
        board = reader.props(ole.openstream('Board6/Data').read())[0]
        data = ole.openstream('Pads6/Data').read()
    pads = []
    offset = 0
    while offset < len(data):
        assert data[offset] == 2
        offset += 1
        blocks = []
        for _ in range(6):
            size = struct.unpack_from('<I', data, offset)[0] & 0xffffff
            blocks.append(data[offset+4:offset+4+size])
            offset += size + 4
        b = blocks[4]
        ci = struct.unpack_from('<H', b, 7)[0]
        values = [v * reader.UNIT for v in struct.unpack_from('<9i', b, 13)]
        pads.append(dict(component_index=ci, component=None if ci==65535 else components[ci].get('SOURCEDESIGNATOR'),
            number=blocks[0][1:].decode(), layer=b[0], x=values[0], y=values[1],
            size_x=values[2], size_y=values[3], hole=values[8],
            rotation=struct.unpack_from('<d', b, 52)[0], shape=b[49]))
    vertices = [(reader.mm(board['VX'+str(i)]), reader.mm(board['VY'+str(i)]))
                for i in range(len([k for k in board if k.startswith('VX') and k[2:].isdigit()]))]
    assert reader.sha(path)==before
    return dict(source=str(path), sha256=before, components=components, pads=pads, vertices=vertices)


def drill_mounts(archive):
    with zipfile.ZipFile(archive) as z:
        text = z.read('Sample_Holder.TXT').decode('ascii')
        outline = z.read('Sample_Holder.GM').decode('ascii')
        report = z.read('Sample_Holder.DRR').decode('ascii')
    assert ';FILE_FORMAT=4:4' in text and 'METRIC,LZ' in text
    tool = None
    size_by_tool = {}
    points = []
    x = y = None
    def number(s):
        sign = -1 if s.startswith('-') else 1
        return sign * int(s.lstrip('+-').ljust(8,'0')) / 10000
    for line in text.splitlines():
        definition = re.match(r'T(\d+)F\d+S\d+C([0-9.]+)',line)
        if definition:
            size_by_tool[int(definition[1])] = float(definition[2])
        elif re.fullmatch(r'T\d+',line):
            tool = int(line[1:])
        elif line.startswith(('X','Y')):
            xv = re.search(r'X(-?\d+)',line)
            yv = re.search(r'Y(-?\d+)',line)
            if xv: x=number(xv[1])
            if yv: y=number(yv[1])
            if size_by_tool.get(tool,0)>1.5:
                points.append((x,y,size_by_tool[tool]))
    assert len(points)==4 and all(abs(p[2]-3.2)<1e-9 for p in points)
    outline_points=[]
    x=y=None
    for line in outline.splitlines():
        if not line.startswith(('X','Y')):continue
        xv=re.search(r'X(-?\d+)',line);yv=re.search(r'Y(-?\d+)',line)
        if xv:x=int(xv[1])/10000
        if yv:y=int(yv[1])/10000
        if x is not None and y is not None:outline_points.append((x,y))
    lo=np.min(outline_points,axis=0)
    return dict(points_mm=points, normalized_points_mm=[(x-lo[0],y-lo[1],d) for x,y,d in points],
                tool_sizes_mm=size_by_tool, report=report)


def draw(data,holes):
    lo=np.min(data['vertices'],axis=0)
    vertices=np.asarray(data['vertices'])-lo
    fig=plt.figure(figsize=(11,13),dpi=210)
    ax=fig.add_axes((.065,.12,.48,.77))
    note=fig.add_axes((.60,.18,.37,.68));note.axis('off')
    ax.add_patch(Polygon(vertices,fc='#eaf1ef',ec='#527b70',lw=1.5))
    for p in data['pads']:
        x,y=p['x']-lo[0],p['y']-lo[1]
        color='#d4b56e' if p['component']=='S1' else '#9aafb1'
        if p['hole']>1.5:continue
        if p['shape']==1 and abs(p['size_x']-p['size_y'])<1e-5:
            ax.add_patch(Circle((x,y),p['size_x']/2,fc=color,ec='none',alpha=.8))
        else:
            pts=reader.corners(x,y,p['size_x'],p['size_y'],p['rotation'])
            ax.add_patch(Polygon(pts,fc=color,ec='none',alpha=.8))
        if p['hole']>0:
            ax.add_patch(Circle((x,y),p['hole']/2,fc='#eaf1ef',ec='none'))
    for c in data['components']:
        name=c.get('SOURCEDESIGNATOR','')
        x=reader.mm(c['X'])-lo[0];y=reader.mm(c['Y'])-lo[1]
        if c.get('PATTERN')=='SMPFSSBPCT':
            cp=[p for p in data['pads'] if p['component']==name]
            bounds=(min(p['x']-p['size_x']/2 for p in cp)-lo[0],
                    min(p['y']-p['size_y']/2 for p in cp)-lo[1],
                    max(p['x']+p['size_x']/2 for p in cp)-lo[0],
                    max(p['y']+p['size_y']/2 for p in cp)-lo[1])
            ax.add_patch(Rectangle(bounds[:2],bounds[2]-bounds[0],bounds[3]-bounds[1],
                                   fill=False,ec='#acbabb',lw=.6,ls=':'))
            ax.text(x,y,name,ha='center',va='center',fontsize=7,color='#60747a')
        elif name in ('J1','J2'):
            ax.text(x,y-4,f'{name} / ZIF',ha='center',va='top',fontsize=9,color='#60747a')
        elif name=='S1':
            ax.text(x,y,'Sample\narea',ha='center',va='center',fontsize=10,color='#647a78')
    for h in holes:
        x,y=h['x_mm'],h['y_mm']
        ax.add_patch(Circle((x,y),2.75,fc='#f1b789',ec='#c15a24',lw=1.5,zorder=8))
        ax.add_patch(Circle((x,y),1.6,fc='white',ec='#c15a24',lw=1,zorder=9))
        ax.plot([x-.55,x+.55],[y,y],color='#c15a24',lw=.7,zorder=10)
        ax.plot([x,x],[y-.55,y+.55],color='#c15a24',lw=.7,zorder=10)
        tx=-2.2 if x<16.3 else 34.8
        ax.text(tx,y,h['id'],ha='right' if x<16.3 else 'left',va='center',
                fontsize=11,color='#ae491c',weight='bold')
    def dim(a,b,label,textpos,rotation=0):
        ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='<->',lw=1,color='#415d67'))
        ax.text(*textpos,label,rotation=rotation,ha='center',va='center',fontsize=10,
                color='#415d67',bbox=dict(fc='white',ec='none',pad=2))
    for y in (3.5,79.1):
        ax.plot([3.5,29.1],[y,y],ls=':',color='#c28467',lw=.7,zorder=0)
    dim((3.5,83.6),(29.1,83.6),'25.60 mm',(16.3,85.0))
    ax.plot([3.5,3.5],[79.1,83.6],lw=.6,color='#c28467')
    ax.plot([29.1,29.1],[79.1,83.6],lw=.6,color='#c28467')
    dim((-5.8,3.5),(-5.8,79.1),'75.60 mm',(-7.2,41.3),90)
    dim((0,111),(32.6,111),'32.60 mm',(16.3,112.8))
    ax.set(xlim=(-9.3,40),ylim=(-4,116),aspect='equal',xlabel='X from left edge (mm)',ylabel='Y from lower edge (mm)')
    ax.set_xticks([0,10,20,32.6]);ax.set_yticks([0,20,40,60,79.1,100,107.1])
    ax.tick_params(labelsize=8)
    ax.spines[['top','right']].set_visible(False)
    note.text(0,1,'4 mounting holes',fontsize=20,weight='bold',color='#ae491c',va='top')
    note.text(0,.93,'All four: diameter 3.20 mm\nPlated through holes (PTH)\nPad diameter: 5.50 mm',fontsize=12,va='top',linespacing=1.6)
    note.text(0,.76,'No separate M2 / M2.5 hole sizes\nare stored in this reference PCB.\nFastener intent is not encoded.',fontsize=11,va='top',linespacing=1.5,color='#405a62')
    rows=[[h['id'],f"{h['x_mm']:.2f}",f"{h['y_mm']:.2f}"] for h in holes]
    table=note.table(cellText=rows,colLabels=['Hole','X (mm)','Y (mm)'],cellLoc='center',bbox=(0,.42,.99,.22))
    table.auto_set_font_size(False);table.set_fontsize(11)
    for (i,j),cell in table.get_celld().items():
        cell.set_edgecolor('#d2dddc')
        if i==0:cell.set_facecolor('#e6edeb')
    note.text(0,.36,'Coordinate origin: lower-left PCB corner\nBoard: 32.60 x 107.10 mm',fontsize=10.5,va='top',linespacing=1.5)
    note.text(0,.25,'Hole-centre offsets\nLeft / right edges: 3.50 mm\nLower edge to lower pair: 3.50 mm\nUpper edge to upper pair: 28.00 mm',fontsize=11,va='top',linespacing=1.6)
    note.text(0,.065,'Native PCB and NC drill agree.\nReference files unchanged.',fontsize=10.5,va='top',color='#527b70',linespacing=1.5)
    fig.suptitle('12-RF Sample_Holder: mounting-hole locations',fontsize=19,y=.96)
    fig.text(.5,.918,'Saved XY projection, not mirrored | Orange = mounting holes | Grey / gold = component pads',ha='center',fontsize=10)
    fig.text(.5,.057,'Source: Carrier_12MW_72DC / PCB / Sample_Holder / Sample_Holder.PcbDoc',ha='center',fontsize=9.5,color='#50626b')
    fig.text(.5,.036,'Cross-check: Sample_Holder_gerbers_new_2025.08.21.zip / Sample_Holder.TXT, tool T04',ha='center',fontsize=9.5,color='#50626b')
    fig.savefig(OUT/'Reference12_Mounting_Holes.png')
    plt.close(fig)


def main():
    data=extract()
    OUT.mkdir(exist_ok=True)
    archive=REF/'Sample_Holder_gerbers_new_2025.08.21.zip'
    archive_hash=reader.sha(archive)
    drill=drill_mounts(archive)
    lo=np.min(data['vertices'],axis=0)
    mounts=sorted([p for p in data['pads'] if p['hole']>1.5],key=lambda p:(-p['y'],p['x']))
    assert len(mounts)==4
    holes=[dict(id=f'H{i+1}',x_mm=p['x']-lo[0],y_mm=p['y']-lo[1],diameter_mm=p['hole'],pad_diameter_mm=p['size_x']) for i,p in enumerate(mounts)]
    for h in holes:
        assert any(abs(h['x_mm']-x)<.00002 and abs(h['y_mm']-y)<.00002 and abs(h['diameter_mm']-d)<.00002
                   for x,y,d in drill['normalized_points_mm'])
    draw(data,holes)
    assert reader.sha(REF/'Sample_Holder.PcbDoc')==data['sha256'] and reader.sha(archive)==archive_hash
    (OUT/'native_reference_snapshot.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    audit=dict(source=data['source'],source_sha256=data['sha256'],mounting_holes=holes,
        coordinate_origin='Lower-left PCB outline corner; saved XY projection, not mirrored',
        native_pad_hole_counts=Counter(round(p['hole'],3) for p in data['pads'] if p['hole']>0),
        drill_archive=str(archive),drill_archive_sha256=archive_hash,drill_cross_check=drill,
        source_files_unchanged=True,fastener_intent='Not encoded; do not relabel holes as M2 or M2.5 from diameter alone')
    (OUT/'mounting_hole_audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(holes=holes,native_and_drill_agree=True,source_files_unchanged=True,image=str(OUT/'Reference12_Mounting_Holes.png')),indent=2))


if __name__=='__main__':
    main()
