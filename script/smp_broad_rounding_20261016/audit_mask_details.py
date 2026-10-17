"""Check saved solder-control regions by feature; normal pad apertures are intentional."""
from pathlib import Path
import sys,json,hashlib
from shapely.geometry import Point,box,shape
from shapely.ops import unary_union
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
pcb=P/(P.name+'.PcbDoc');digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
plan=json.loads((H/'candidate.json').read_text());routes=json.loads((H/'entry_routes.json').read_text())
opening={ll:unary_union([r['geometry'] for r in regions if r['layer']==ll]) for ll in (37,38)}
field=shape(plan['qd_mask_field']);mount=unary_union([p['geometry'].buffer(.101) for p in pads if p['ref'] is None])
rows=[]
def protect(label,g,ll,tol=.003):
    area=g.difference(mount).buffer(-tol).intersection(opening[ll]).area
    rows.append(dict(feature=label,layer=ll,intrusion_mm2=area,passed=area<1e-8))
for group in routes['groups']:
    rr=group['row'];rc=box(*unary_union([p['geometry'] for p in pads if p['ref'] in (rr['resistor'],rr['capacitor'])]).bounds).buffer(.9,join_style='mitre')
    smp=unary_union([p['geometry'] for p in pads if p['ref']==rr['smp']]).convex_hull.buffer(.3,quad_segs=96)
    for ll in (37,38):
        protect(rr['resistor']+'/'+rr['capacitor'],rc.difference(field) if ll==38 else rc,ll)
        protect(rr['smp'],smp.difference(field) if ll==38 else smp,ll)
zv=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in plan['vias'] if v['label'].startswith('J1-')])
protect('ZIF bottom via rectangle, 0.40 mm margin',box(*zv.bounds).buffer(.4,join_style='mitre'),38)
zt=box(*unary_union([zv]+[p['geometry'] for p in pads if p['ref']=='J1']).bounds).buffer(.3,join_style='mitre')
protect('ZIF top solder-control rectangle',zt,37)
rf=unary_union([t['geometry'] for t in tracks if t['layer']==32 and t['net'] and t['net'].startswith(('S','MW'))])
protect('RF protected strip, 0.71 mm from centreline',rf.buffer(.71,quad_segs=96).difference(field),38)
qdv=[v for v in plan['vias'] if v['label'].startswith('Q1-')]
for v in qdv:protect('QD via '+v['label'],Point(v['x'],v['y']).buffer(v['diameter']/2),37,.000025)
cx,cy=plan['sample_center'];centre=box(cx-2.15,cy-2.65,cx+2.15,cy+2.65)
for name,g,ll in [('QD Bottom wire-bond field',field,38),('QD Top centre metal',centre,37)]:
    missing=g.difference(opening[ll].buffer(.000025)).area
    rows.append(dict(feature=name,layer=ll,missing_opening_mm2=missing,passed=missing<1e-8))
assert digest==hashlib.sha256(pcb.read_bytes()).hexdigest()
result=dict(passed=all(r['passed'] for r in rows),source_sha256=digest,checks=rows,QD_top_protected_vias=len(qdv),scope='Saved general mask openings; normal component-pad openings are intentional and checked by native mask export.')
(H/'mask_detail_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(dict(passed=result['passed'],checks=len(rows),QD_top_protected_vias=len(qdv),issues=[r for r in rows if not r['passed']]),indent=2))
