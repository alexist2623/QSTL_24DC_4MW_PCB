"""Limit the follow-up to S13 and its nearby shielding/surfaces; inspect exact native arc."""
from pathlib import Path
import json, sys, hashlib, struct
from collections import defaultdict
from shapely.geometry import Point, box
from shapely.ops import unary_union
H=Path(__file__).resolve().parent; ROOT=H.parents[1]; P=ROOT/'QSTL_QD4_2SET_38PAD'; N=P.name
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot, properties, binary_records, UNIT, olefile
old=json.loads((H/'before_c13_rounding/candidate.json').read_text()); new=json.loads((H/'candidate.json').read_text())
local=box(10.4,21.9,17.8,26.5)
for key in ('tracks','arcs'):
    assert [t for t in old[key] if t['net']!='S13']==[t for t in new[key] if t['net']!='S13'],key
sig=lambda p:set((v['x'],v['y'],v['diameter'],v['hole'],v['low'],v['high']) for v in p['shield_vias'])
a,b=sig(old),sig(new); delta=a^b
assert all(local.covers(Point(v[:2])) for v in delta),delta
oldrecords=json.loads((H/'before_c13_rounding/shield_records.json').read_text())['vias']
newrecords=json.loads((H/'shield_records.json').read_text())['vias']
rec=lambda rows:set((v['x_mm'],v['y_mm'],v['kind'],v['channel']) for v in rows if v['channel']!='SMP13')
assert rec(oldrecords)==rec(newrecords),'Other channels shield geometry changed'
result=dict(passed=True,other_RF_routes_and_entry_shields_exactly_unchanged=True,local_removed_shields=len(a-b),local_added_shields=len(b-a),changed_shield_bounds_mm=unary_union([Point(v[:2]) for v in delta]).bounds)
if '--native' in sys.argv:
    sch=json.loads((P/'schematic_validation.json').read_text())
    before=read_snapshot(H/'before_c13_rounding'/(N+'.PcbDoc'),sch); after=read_snapshot(P/(N+'.PcbDoc'),sch)
    def routes(s):
        groups=defaultdict(list)
        for t in s[2]:
            if t['net']!='S13':groups[(t['net'],t['layer'],t['width'])].append(t['geometry'])
        return {k:unary_union(v) for k,v in groups.items()}
    a,b=routes(before),routes(after);assert a.keys()==b.keys()
    differences={str(k):a[k].hausdorff_distance(b[k]) for k in a}
    diff=max(differences.values());assert diff<2*UNIT,diff  # Native coordinate rounding during arc cleanup.
    result['other_saved_routes_max_difference_mm']=diff
    result['unchanged_route_native_grid_tolerance_mm']=2*UNIT
    result['rounded_route_differences_mm']={k:v for k,v in differences.items() if v>1e-7}
    with olefile.OleFileIO(P/(N+'.PcbDoc')) as doc:
        nets=properties(doc.openstream('Nets6/Data').read()); arcs=[]
        for r in binary_records(doc.openstream('Arcs6/Data').read(),1):
            raw=r['body']; ni=struct.unpack_from('<H',raw,3)[0]
            if ni!=65535 and nets[ni]['NAME']=='S13':
                cx,cy,radius=[v*UNIT for v in struct.unpack_from('<3i',raw,13)]
                a0,a1=struct.unpack_from('<2d',raw,25)
                arcs.append(dict(cx=cx,cy=cy,radius=radius,start=a0,end=a1,layer=raw[0]))
    assert len(arcs)==1,arcs
    z=arcs[0];assert z['layer']==32 and max(abs(z[k]-v) for k,v in dict(cx=13.35,cy=24.45,radius=1.6,start=180,end=270).items())<1e-5,z
    s13=[t for t in after[2] if t['net']=='S13'];assert len(s13)==3
    straight=[t['geometry'] for t in s13 if not t.get('is_arc')];assert len(straight)==2
    result.update(native_arc=z,normal_launch_mm=.75,radial_entry_mm=3.4,source_sha256=hashlib.sha256((P/(N+'.PcbDoc')).read_bytes()).hexdigest())
(H/('c13_native_audit.json' if '--native' in sys.argv else 'c13_scope_audit.json')).write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
