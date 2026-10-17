"""Verify compact-mask scope, per-feature protection and unchanged copper."""
from pathlib import Path
import sys,json,hashlib,struct
from shapely.geometry import Point,shape,box
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,olefile,binary_records
from prepare_native_revision_rules import read_rules
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pcb=P/(N+'.PcbDoc');digest=sha(pcb);sch=json.loads((P/'schematic_validation.json').read_text())
before=read_snapshot(H/'baseline'/(N+'.PcbDoc'),sch);after=read_snapshot(pcb,sch)
pads,regions,tracks,vias,outline=after;plan=json.loads((H/'candidate.json').read_text());spec=plan['compact_mask_spec'];issues=[];rows=[]
def check(ok,name,detail=None):
    rows.append(dict(check=name,passed=bool(ok),detail=detail))
    if not ok:issues.append(rows[-1])
signature=lambda tt:sorted((t['net'] or '',t['layer'],t['width'],t['geometry'].wkb_hex) for t in tt)
check(signature(before[2])==signature(tracks),'All RF/DC/mechanical routes exactly preserved')
for key in ('x','y','sx','sy','hole','rotation','layer','net','shape'):
    a={(p['ref'],p['pin']):p[key] for p in before[0]};b={(p['ref'],p['pin']):p[key] for p in pads}
    check(a==b,'Unchanged pad '+key)
sig=lambda vv:sorted((v['net'],v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in vv)
check(sig(before[3])==sig(vias),'All 1590 vias preserved')
check(before[4].equals_exact(outline,1e-10),'Outline preserved')
for ll in sorted({r['layer'] for r in before[1] if r['layer'] not in (38,)}):
    for net in {r['net'] for r in before[1] if r['layer']==ll}:
        a=unary_union([r['geometry'] for r in before[1] if r['layer']==ll and r['net']==net]);b=unary_union([r['geometry'] for r in regions if r['layer']==ll and r['net']==net])
        check(a.equals_exact(b,1e-10),'Nonmask region preserved',[ll,net])
for name in (N+'.SchDoc','pin_mapping.csv'):
    check(sha(P/name)==sha(H/'baseline'/name),'Preserved '+name)
check(read_rules(pcb)==read_rules(H/'baseline'/(N+'.PcbDoc')),'All native rules preserved')
# Binary equality of owned component primitives, embedded models and electrical objects.
with olefile.OleFileIO(H/'baseline'/(N+'.PcbDoc')) as a,olefile.OleFileIO(pcb) as b:
    for path in a.listdir():
        if path[0] in ('Models','ModelsNoEmbed','ComponentBodies6','Components6','Pads6','Vias6','Tracks6','Arcs6','Rules6','LayerStackManager'):
            check(b.exists(path) and a.openstream(path).read()==b.openstream(path).read(),'Native stream preserved','/'.join(path))
    cuts=[]
    for rec in binary_records(b.openstream('Regions6/Data').read(),11):
        data=rec['body'];start=data.index(b'V7_LAYER=');length=struct.unpack_from('<I',data,start-4)[0]&0xffffff
        f=dict(t.split('=',1) for t in data[start:start+length].rstrip(b'\0').decode('cp1252').split('|') if '=' in t)
        if f.get('NAME','').startswith('L5_RC_PAD_VOID_'):cuts.append((f['NAME'],data[0],f.get('KIND'),struct.unpack_from('<H',data,3)[0]))
check(len(cuts)==32 and all(r[1:]==(5,'1',65535) for r in cuts),'32 persistent L5-only cutouts preserved')
gnd=unary_union([r['geometry'] for r in regions if r['layer']==5 and r['net']=='GND'])
for ref in spec['RC_contours']:
    hull=unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull
    check(hull.intersection(gnd).area<1e-8,'L5 void '+ref,hull.intersection(gnd).area)
opening={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll]) for ll in (37,38)}
field=shape(plan['qd_mask_field']);cx,cy=plan['sample_center'];centre=box(cx-2.15,cy-2.65,cx+2.15,cy+2.65)
mount=unary_union([p['geometry'].buffer(.101) for p in pads if p['ref'] is None])
def protect(label,g,ll,tol=.0003):
    g=g.difference(mount)
    if ll==38:g=g.difference(field)
    area=g.buffer(-tol).intersection(opening[ll]).area
    check(area<1e-8,label,[ll,area])
for ref,gj in spec['RC_contours'].items():protect('Compact rotated footprint '+ref,shape(gj),38)
for ref,gj in spec['Top_local_via_contours'].items():protect('Top local via cover '+ref,shape(gj),37)
for i,gj in enumerate(spec['SMP']):
    for ll in (37,38):protect('SMP solder control '+str(i),shape(gj),ll,.001)
protect('Top ZIF protection',shape(spec['Top_ZIF']),37)
protect('Bottom ZIF via protection',shape(spec['Bottom_ZIF']),38)
protect('RF strip preserved',shape(spec['RF_protection']),38,.001)
protect('Bottom local via protection',shape(spec['Bottom_via_contours']),38)
for name,ll,g in [('Top central metal',37,centre),('Bottom bond field',38,field),('Top mounts',37,mount.buffer(-.002)),('Bottom mounts',38,mount.buffer(-.002))]:
    check(g.difference(opening[ll].buffer(.0003)).area<1e-8,name+' exposed')
check(digest==sha(pcb),'Stable native source')
result=dict(passed=not issues,source_sha256=digest,checks=rows,issues=issues)
(H/'compact_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(passed=result['passed'],checks=len(rows),issues=issues),indent=2))
