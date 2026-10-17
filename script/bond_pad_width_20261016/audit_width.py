"""Verify widened native QD pads and the strictly local change boundary."""
from pathlib import Path
import sys,json,hashlib,math,struct
from shapely.geometry import Point,box
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,olefile,binary_records
from prepare_native_revision_rules import read_rules
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pcb=P/(N+'.PcbDoc');digest=sha(pcb);sch=json.loads((P/'schematic_validation.json').read_text())
before=read_snapshot(H/'baseline'/(N+'.PcbDoc'),sch);after=read_snapshot(pcb,sch)
pads,regions,tracks,vias,outline=after;plan=json.loads((H/'candidate.json').read_text())
spec=json.loads((H/'preparation_audit.json').read_text());rows=[];issues=[]
def check(ok,label,detail=None):
    row=dict(check=label,passed=bool(ok),detail=detail);rows.append(row)
    if not ok:issues.append(row)
sig=lambda tt:sorted((t['net'] or '',t['layer'],t['width'],t['geometry'].wkb_hex) for t in tt)
check(sig(before[2])==sig(tracks),'All RF/DC/mechanical routes exactly preserved')
old={(p['ref'],p['pin']):p for p in before[0]};qd=[]
check(len(old)==len(pads)==241,'241 pad identities retained')
for p in pads:
    a=old[(p['ref'],p['pin'])]
    for k in ('x','y','sx','hole','rotation','layer','net','shape'):
        check(a[k]==p[k],'Preserved pad '+k,[p['ref'],p['pin']])
    check(abs(p['sy']-(.26 if p['ref']=='Q1' else a['sy']))<.000003,'Correct pad short width',[p['ref'],p['pin'],p['sy']])
    if p['ref']=='Q1':qd.append(p)
check(len(qd)==38,'Exactly 38 widened QD pads')
via_key=lambda v:(v['net'],v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high'])
check(sorted(via_key(v) for v in before[3] if v['net']!='GND')==sorted(via_key(v) for v in vias if v['net']!='GND'),'All 76 terminal vias preserved')
expected=[];moves=spec['moved_shields'];move_count=0
for v in before[3]:
    if v['net']!='GND':continue
    q=dict(v)
    matches=[m for m in moves if math.dist(m['before'],(v['x'],v['y']))<.000001]
    if matches:q['x'],q['y']=matches[0]['after'];move_count+=1
    expected.append(q)
actual=[v for v in vias if v['net']=='GND'];used=set()
for v in expected:
    i,a=min(enumerate(actual),key=lambda it:math.dist((it[1]['x'],it[1]['y']),(v['x'],v['y'])))
    used.add(i)
    check(math.dist((a['x'],a['y']),(v['x'],v['y']))<.000003 and all(a[k]==v[k] for k in ('diameter','hole','low','high')),'Expected shield position and span',[v['x'],v['y']])
check(move_count==5 and len(used)==len(actual)==1514,'Exactly five local shield moves; total 1514')
check(before[4].equals_exact(outline,1e-10),'Outline preserved')
for ll in sorted({r['layer'] for r in before[1]}):
    for net in {r['net'] for r in before[1] if r['layer']==ll}:
        if ll==32 and net=='GND':continue
        a=unary_union([r['geometry'] for r in before[1] if r['layer']==ll and r['net']==net])
        b=unary_union([r['geometry'] for r in regions if r['layer']==ll and r['net']==net])
        check(a.equals_exact(b,1e-10),'Unchanged region geometry',[ll,net])
gnd={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll and r['net']=='GND']) for ll in (5,32)}
oldgnd=unary_union([r['geometry'] for r in before[1] if r['layer']==32 and r['net']=='GND'])
qp=unary_union([p['geometry'] for p in qd])
check(gnd[32].difference(oldgnd.buffer(.000003)).area<1e-8,'No added L6 ground')
removed=oldgnd.difference(gnd[32])
outside_local=removed.difference(qp.buffer(.201))
# Recreating native region contours rounds pre-existing double-precision region
# vertices onto the 2.54 nm Altium coordinate lattice. Only this boundary band
# may differ outside the intentional local pad-clearance subtraction.
outside_grid=outside_local.difference(oldgnd.boundary.buffer(.000003))
check(outside_grid.area<1e-8,'L6 removal confined to widened pad clearance or native grid rounding',dict(outside_local_area_mm2=outside_local.area,outside_3nm_boundary_band_mm2=outside_grid.area))
minima={}
pp=min((a['geometry'].distance(b['geometry']),a['pin'],b['pin']) for i,a in enumerate(qd) for b in qd[i+1:])
minima['pad_to_pad_mm']=pp[0];minima['limiting_pad_pair']=pp[1:]
check(pp[0]>=.15,'JLCPCB SMD different-net pad spacing',pp)
cx,cy=plan['sample_center'];cavity=box(cx-2.15+.5,cy-2.65+.5,cx+2.15-.5,cy+2.65-.5).buffer(.5,quad_segs=128)
minima['pad_to_pocket_mm']=min(p['geometry'].distance(cavity) for p in qd)
check(minima['pad_to_pocket_mm']>=.2-.000003,'Preserved cavity clearance',minima['pad_to_pocket_mm'])
minima['pad_to_L6_ground_mm']=qp.distance(gnd[32])
check(minima['pad_to_L6_ground_mm']>=.2,'L6 pad-to-ground clearance',minima['pad_to_L6_ground_mm'])
foreign=[];groundvia=[]
for p in qd:
    for v in vias:
        if v['high']!=32 or v['net']==p['net']:continue
        gap=p['geometry'].distance(Point(v['x'],v['y']))-v['diameter']/2
        (groundvia if v['net']=='GND' else foreign).append(gap)
    for t in tracks:
        if t['layer']==32 and t['net'] and t['net']!=p['net']:
            foreign.append(p['geometry'].distance(t['geometry'])-t['width']/2)
minima['pad_to_shield_land_mm']=min(groundvia);minima['pad_to_foreign_signal_mm']=min(foreign)
check(min(groundvia)>=.2,'QD pad-to-shield land clearance',min(groundvia))
check(min(foreign)>=.15,'QD pad-to-foreign trace/via clearance',min(foreign))
moved_saved=[min(actual,key=lambda v:math.dist((v['x'],v['y']),m['after'])) for m in moves]
minima['moved_shield_to_shield_land_mm']=min(math.dist((v['x'],v['y']),(a['x'],a['y']))-(v['diameter']+a['diameter'])/2 for v in moved_saved for a in actual if a is not v)
minima['moved_shield_to_signal_via_land_mm']=min(math.dist((v['x'],v['y']),(a['x'],a['y']))-(v['diameter']+a['diameter'])/2 for v in moved_saved for a in vias if a['net']!='GND')
check(minima['moved_shield_to_shield_land_mm']>=.15,'Moved shield-to-shield clearance',minima['moved_shield_to_shield_land_mm'])
check(minima['moved_shield_to_signal_via_land_mm']>=.15,'Moved shield-to-foreign-via clearance',minima['moved_shield_to_signal_via_land_mm'])
for name in (N+'.SchDoc','pin_mapping.csv'):
    check(sha(P/name)==sha(H/'baseline'/name),'Preserved '+name)
check(read_rules(pcb)==read_rules(H/'baseline'/(N+'.PcbDoc')),'All native rules preserved')
with olefile.OleFileIO(H/'baseline'/(N+'.PcbDoc')) as a,olefile.OleFileIO(pcb) as b:
    for path in a.listdir():
        if path[0] in ('Models','ModelsNoEmbed','ComponentBodies6','Components6','Tracks6','Arcs6','Rules6','LayerStackManager'):
            check(b.exists(path) and a.openstream(path).read()==b.openstream(path).read(),'Native stream preserved','/'.join(path))
    cuts=[]
    for rec in binary_records(b.openstream('Regions6/Data').read(),11):
        data=rec['body'];start=data.index(b'V7_LAYER=');length=struct.unpack_from('<I',data,start-4)[0]&0xffffff
        f=dict(t.split('=',1) for t in data[start:start+length].rstrip(b'\0').decode('cp1252').split('|') if '=' in t)
        if f.get('NAME','').startswith('L5_RC_PAD_VOID_'):cuts.append((f['NAME'],data[0],f.get('KIND'),struct.unpack_from('<H',data,3)[0]))
check(len(cuts)==32 and all(r[1:]==(5,'1',65535) for r in cuts),'32 persistent L5-only C/R cutouts preserved')
for ref in plan['compact_mask_spec']['RC_contours']:
    hull=unary_union([p['geometry'] for p in pads if p['ref']==ref]).convex_hull
    check(hull.intersection(gnd[5]).area<1e-8,'No L5 GND below '+ref)
check(sha(pcb)==digest,'Native stable during audit')
result=dict(passed=not issues,source_sha256=digest,minima=minima,checks=rows,issues=issues)
(H/'width_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(passed=not issues,checks=len(rows),minima=minima,issues=issues),indent=2))
