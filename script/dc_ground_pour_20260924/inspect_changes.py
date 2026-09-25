"""Explain native serialization changes introduced by polygon generation."""
from pathlib import Path
import sys,collections,struct,json
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=H.parents[1]/'QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import binary_records,properties
from build_routed_copy import snapshot
from verify_final_native_v2 import read_route,trackkey
a=snapshot(H/'before_ground_pour.PcbDoc');b=snapshot(P/'QSTL_24DC_4MW_PCB.PcbDoc')
for stream,kind in [('Tracks6/Data',4),('ShapeBasedRegions6/Data',11)]:
    aa=[r['body'] for r in binary_records(a[stream],kind)];bb=[r['body'] for r in binary_records(b[stream],kind)]
    missing=list((collections.Counter(aa)-collections.Counter(bb)).elements())
    added=list((collections.Counter(bb)-collections.Counter(aa)).elements())
    print(json.dumps(dict(stream=stream,before=len(aa),after=len(bb),missing=len(missing),added=len(added),
        new=[dict(layer=x[0],net=struct.unpack_from('<H',x,3)[0],polygon=struct.unpack_from('<H',x,5)[0],length=len(x),prefix=x[:24].hex()) for x in added[:12]]),indent=2))
    if len(aa)==len(bb):print('BYTE_OFFSETS',collections.Counter(i for x,y in zip(aa,bb) for i,(u,v) in enumerate(zip(x,y)) if u!=v))
ta,_,_=read_route(a,properties(a['Nets6/Data']));tb,_,_=read_route(b,properties(b['Nets6/Data']))
print('TRACK_GEOMETRY_IDENTICAL',collections.Counter(map(trackkey,ta))==collections.Counter(map(trackkey,tb)))
