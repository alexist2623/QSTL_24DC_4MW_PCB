"""Inspect actual Altium mask output and render mask/ground review images."""
from pathlib import Path
import sys,json,hashlib,struct
from shapely.geometry import Point,LineString,Polygon,box,shape
from shapely.ops import unary_union
from shapely import wkb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OUT=P/'SMP_Rounded_Entries_20261016'
sys.path[:0]=[str(ROOT/'script/qd38_rotation_20261011'),str(ROOT/'script/fpc_gerber_20261005/work/deps')]
from audit_saved_revision_surface import read_snapshot,pad_shape,olefile,pads_stream,UNIT
from prepare_native_revision_rules import read_rules
from gerbonara import GerberFile
from gerbonara.utils import MM
pcb=P/(P.name+'.PcbDoc');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();digest=sha(pcb)
pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
with olefile.OleFileIO(pcb) as doc:np=pads_stream(doc.openstream('Pads6/Data').read())
rules=read_rules(pcb);rule=next(r for r in rules.values() if r['RULEKIND']=='SolderMaskExpansion');default=float(rule['EXPANSION'].removesuffix('mil'))*.0254
def parse(path):
    result=Polygon();pending=[];polarity=True
    for obj in GerberFile.open(path).objects:
        for p in obj.to_primitives(unit=MM):
            if p.polarity_dark!=polarity and pending:
                joined=unary_union(pending);result=result.union(joined) if polarity else result.difference(joined);pending=[]
            polarity=p.polarity_dark;kind=type(p).__name__
            if kind=='Circle':s=Point(p.x,p.y).buffer(p.r,quad_segs=128)
            elif kind=='Line':s=LineString([(p.x1,p.y1),(p.x2,p.y2)]).buffer(p.width/2,quad_segs=128)
            elif kind=='Rectangle':s=Polygon(p.to_arc_poly().outline)
            elif kind=='ArcPoly':s=Polygon(p.approximate_arcs(max_error=.00001).outline)
            else:raise ValueError(kind)
            pending.append(s if s.is_valid else s.buffer(0))
    if pending:
        joined=unary_union(pending);result=result.union(joined) if polarity else result.difference(joined)
    return result
cam={};results=[]
for ext,ll,ml in [('GTS',1,37),('GBS',32,38)]:
    path=H/'paste_verification/Native_CAM'/(P.name+'.'+ext);assert path.stat().st_mtime>pcb.stat().st_mtime
    g=parse(path);cam[ml]=g;(H/(ext+'.wkb')).write_bytes(wkb.dumps(g))
    shapes=[r['geometry'] for r in regions if r['layer']==ml];normal=[]
    for p,n in zip(pads,np):
        if p['layer'] not in (ll,74):continue
        b=n['blocks'][4];ex=struct.unpack_from('<i',b,90 if ll==1 else 121)[0]*UNIT if b[102] in (1,2) else default
        pp=dict(p,sx=p['sx']+2*ex,sy=p['sy']+2*ex)
        if min(pp['sx'],pp['sy'])<=0:continue
        land=pad_shape(pp);shapes.append(land)
        if p['ref'] and p['ref'][0] in 'RCJ':normal.append(p)
    expected=unary_union(shapes);missing=expected.difference(g.buffer(.0003)).area;extra=g.difference(expected.buffer(.0003)).area
    results.append(dict(layer=ext,passed=missing<1e-6 and extra<1e-6,missing_opening_mm2=missing,extra_opening_mm2=extra,normal_SMD_openings=len(normal),sha256=sha(path)))
    for p in normal:assert p['geometry'].buffer(-.0003).difference(g).area<1e-8,(ext,p['ref'],p['pin'])
plan=json.loads((H/'candidate.json').read_text());qd=[v for v in plan['vias'] if v['label'].startswith('Q1-')]
for v in qd:assert Point(v['x'],v['y']).buffer(v['diameter']/2-.0003).intersection(cam[37]).area<1e-8
assert sha(pcb)==digest
report=dict(passed=all(r['passed'] for r in results),source_sha256=digest,layers=results,QD_top_vias_fully_masked=len(qd),CAM_geometry_tolerance_mm=.0003)
(H/'mask_cam_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
def draw(ax,g,color,alpha=1,z=1):
    for p in ([g] if g.geom_type=='Polygon' else list(g.geoms)):
        if p.is_empty or p.geom_type!='Polygon':continue
        verts=[];codes=[]
        for ring in [p.exterior]+list(p.interiors):
            xy=list(ring.coords);verts.extend(xy);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(xy)-2)+[MPath.CLOSEPOLY])
        ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor='none',alpha=alpha,zorder=z))
fig,axes=plt.subplots(1,3,figsize=(14,14),layout='constrained')
for ax,ml,title in zip(axes[:2],(38,37),('Bottom / L6: RF and component solder mask','Top: QD via frame and exposed centre')):
    draw(ax,outline,'#dcb953');draw(ax,outline.difference(cam[ml]),'#377c56')
    for d in pads:
        if d['layer'] in ((32 if ml==38 else 1),74):draw(ax,d['geometry'],'#f7d888',z=3)
    for d in pads:
        if d['hole']>0:draw(ax,Point(d['x'],d['y']).buffer(d['hole']/2),'#10232c',z=4)
    for v in vias:
        if v['net']!='GND':
            pt=Point(v['x'],v['y']);color='#10232c' if cam[ml].covers(pt) else '#5c9971'
            draw(ax,pt.buffer(v['hole']/2),color,z=4)
    ax.set_title(title,fontsize=10)
ax=axes[2];draw(ax,outline,'#10232c');ground=unary_union([r['geometry'] for r in regions if r['net']=='GND' and r['layer']==5]);draw(ax,ground,'#81aba0')
for ref,gj in plan['L5_component_cutouts'].items():
    g=shape(gj);draw(ax,g,'#ffcc76',z=3);c=g.centroid;ax.text(c.x,c.y,ref,ha='center',va='center',fontsize=5)
for d in pads:
    if d['hole']>0:draw(ax,Point(d['x'],d['y']).buffer(d['hole']/2),'#10232c',z=4)
ax.set_title('L5: 32 C/R pad-hull copper openings',fontsize=10)
for ax in axes:ax.set_aspect('equal');ax.set_xlim(-7.2,26.7);ax.set_ylim(-12.2,88.1);ax.set_xlabel('X (mm)');ax.grid(alpha=.1)
axes[0].set_ylabel('Y (mm)');fig.suptitle('Saved native mask output and L5 ground | 16 RF / 38 DC',fontsize=15)
fig.supxlabel('Green = solder mask; gold = exposed area. Right: orange = L5 copper removed, substrate retained.\n'+digest[:16],fontsize=10)
fig.savefig(OUT/'Solder_Mask_and_L5_Openings.png',dpi=180);plt.close(fig)
