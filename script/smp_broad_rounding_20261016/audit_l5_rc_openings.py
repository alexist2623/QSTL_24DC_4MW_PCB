"""Measure actual saved L5 copper under every individual R/C pad-pair hull."""
from pathlib import Path
import sys,json,hashlib,struct
from shapely.ops import unary_union
H=Path(__file__).resolve().parent; ROOT=H.parents[1]; P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot,binary_records,olefile
pcb=P/(P.name+'.PcbDoc'); digest=hashlib.sha256(pcb.read_bytes()).hexdigest()
pads,regions,tracks,vias,outline=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
g=unary_union([r['geometry'] for r in regions if r['layer']==5 and r['net']=='GND'])
refs=sorted(set(p['ref'] for p in pads if p['ref'] and p['ref'][0] in 'RC'))
rows=[]
for ref in refs:
    pp=[p for p in pads if p['ref']==ref]
    if len(pp)!=2:continue
    hull=unary_union([p['geometry'] for p in pp]).convex_hull
    area=g.intersection(hull).area
    rows.append(dict(component=ref,hull_area_mm2=hull.area,remaining_L5_copper_mm2=area,void_pass=area<1e-5))
assert digest==hashlib.sha256(pcb.read_bytes()).hexdigest(),'PCB changed during inspection'
native=[]
with olefile.OleFileIO(pcb) as doc:
    for rec in binary_records(doc.openstream('Regions6/Data').read(),11):
        b=rec['body'];start=b.index(b'V7_LAYER=');length=struct.unpack_from('<I',b,start-4)[0]&0xffffff
        fields=dict(t.split('=',1) for t in b[start:start+length].rstrip(b'\0').decode('cp1252').split('|') if '=' in t)
        if fields.get('NAME','').startswith('L5_RC_PAD_VOID_'):
            native.append(dict(name=fields['NAME'],layer=b[0],kind=fields.get('KIND'),net=struct.unpack_from('<H',b,3)[0]))
passing=sum(r['void_pass'] for r in rows)
persist=len(native)==32 and all(r['layer']==5 and r['kind']=='1' and r['net']==65535 for r in native)
before=read_snapshot(H/'before_l5_voids'/(P.name+'.PcbDoc'),json.loads((P/'schematic_validation.json').read_text()))
other_layers=sorted({r['layer'] for r in before[1] if r['layer']!=5})
preserved=all(unary_union([r['geometry'] for r in before[1] if r['layer']==ll]).equals_exact(unary_union([r['geometry'] for r in regions if r['layer']==ll]),1e-9) for ll in other_layers)
signature=lambda tt:sorted((t['net'] or '',t['layer'],t['width'],t['geometry'].wkb_hex) for t in tt)
routes_same=signature(before[2])==signature(tracks)
result=dict(passed=passing==32 and persist and preserved and routes_same,pcb_sha256=digest,component_count=len(rows),passing=passing,other_layer_regions_preserved=preserved,RF_DC_routes_preserved_by_L5_correction=routes_same,persistent_cutouts=native,rows=rows)
(H/'l5_rc_openings_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','persistent_cutouts')},indent=2))
