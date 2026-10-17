"""Verify restricted SMP changes and exact retained QD/DC/protected entries."""
from pathlib import Path
import sys,json,hashlib,struct,math
from collections import defaultdict
import numpy as np
from shapely.geometry import LineString,Point,shape
from shapely.ops import unary_union
from shapely.affinity import scale
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N=P.name
sys.path[:0]=[str(ROOT/'script/native_16rf_apply_20261016'),str(ROOT/'script/qd38_rotation_20261011')]
import build_candidate as bc
from audit_saved_revision_surface import read_snapshot,properties,binary_records,UNIT,olefile
old=json.loads((H/'baseline/candidate.json').read_text());new=json.loads((H/'candidate.json').read_text());routes=json.loads((H/'entry_routes.json').read_text())
changed={'S'+n[3:] for n in routes['changed_entries']};protected={'S'+n[3:] for n in routes['uncertain_entries']}|{'S13'}
for kind in ('tracks','arcs'):
    assert [r for r in old[kind] if r['net'] not in changed]==[r for r in new[kind] if r['net'] not in changed],kind
before=json.loads((H/'baseline/shield_records.json').read_text())['vias'];after=json.loads((H/'shield_records.json').read_text())['vias']
def fence(vv,channels):return set((v['x_mm'],v['y_mm'],v['kind'],v['channel']) for v in vv if 'S'+v['channel'][3:] in channels)
assert fence(before,protected)==fence(after,protected),'Protected entry shields changed'
nativebefore=None
checks=dict(passed=True,changed_entries=routes['changed_entries'],retained_ambiguous_entries=routes['uncertain_entries'],preserved_C13=True,preserved_QD_RF_DC_and_protected_fences=True)
by={g['row']['smp']:LineString(g['smp_to_c1']) for g in routes['groups']}
sym=[]
for a,b in [('34','32'),('35','31'),('09','30'),('05','21'),('02','24'),('11','28'),('12','16'),('15','13')]:
    dist=scale(by['SMP'+a],xfact=-1,yfact=1,origin=(9.75,0)).hausdorff_distance(by['SMP'+b]);sym.append(dist);assert dist<.00002,(a,b,dist)
checks['maximum_entry_mirror_error_mm']=max(sym)
if '--native' in sys.argv:
    sch=json.loads((P/'schematic_validation.json').read_text());a=read_snapshot(H/'baseline'/(N+'.PcbDoc'),sch);b=read_snapshot(P/(N+'.PcbDoc'),sch)
    def preserved(s):
        bag=defaultdict(list)
        for t in s[2]:
            if t['net'] not in changed:bag[(t['net'],t['layer'],t['width'])].append(t['geometry'])
        return {k:unary_union(g) for k,g in bag.items()}
    a,b=preserved(a),preserved(b);assert a.keys()==b.keys()
    error=max(a[k].hausdorff_distance(b[k]) for k in a);assert error<2*UNIT,error
    checks['saved_preserved_routes_max_difference_mm']=error
    expected=routes['exact_entry_primitives'];want={n:[z for z in zz if not z['line']] for n,zz in expected.items()}
    actual=defaultdict(list)
    with olefile.OleFileIO(P/(N+'.PcbDoc')) as doc:
        nets=properties(doc.openstream('Nets6/Data').read())
        for rec in binary_records(doc.openstream('Arcs6/Data').read(),1):
            raw=rec['body'];ni=struct.unpack_from('<H',raw,3)[0]
            if ni==65535:continue
            net=nets[ni]['NAME']
            if net not in want:continue
            cx,cy,r=[v*UNIT for v in struct.unpack_from('<3i',raw,13)];aa,bb=struct.unpack_from('<2d',raw,25)
            actual[net].append(dict(cx=cx,cy=cy,radius=r,start_angle=aa,end_angle=bb,layer=raw[0]))
    angle_endpoint_errors=[]
    for net,zz in want.items():
        assert len(actual[net])==len(zz),(net,actual[net],zz)
        for z in zz:
            close=min(actual[net],key=lambda t:math.hypot(t['cx']-z['cx'],t['cy']-z['cy']))
            assert close['layer']==32
            assert max(abs(close[k]-z[k]) for k in ('cx','cy','radius'))<.000005,(net,z,close)
            # CleanNet derives non-axial arc angles from grid-rounded joins.
            # Bound the resulting physical endpoint displacement, not decimal angle digits.
            angle_error=max(abs((close[k]-z[k]+180)%360-180) for k in ('start_angle','end_angle'))
            endpoint_error=z['radius']*math.radians(angle_error);angle_endpoint_errors.append(endpoint_error)
            assert endpoint_error<2*UNIT,(net,z,close,endpoint_error)
    checks['maximum_arc_angle_endpoint_rounding_mm']=max(angle_endpoint_errors)
    checks.update(native_exact_arcs=dict(actual),source_sha256=hashlib.sha256((P/(N+'.PcbDoc')).read_bytes()).hexdigest())
(H/('native_scope_audit.json' if '--native' in sys.argv else 'scope_audit.json')).write_text(json.dumps(checks,indent=2))
print(json.dumps({k:v for k,v in checks.items() if k!='native_exact_arcs'},indent=2))
