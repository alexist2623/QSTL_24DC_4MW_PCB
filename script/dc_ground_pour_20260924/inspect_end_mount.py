"""Read the ZIF-end mounting space without modifying the design."""
from pathlib import Path
import sys,json
H=Path(__file__).resolve().parent;R=H.parents[1];W=H.parent/'_support'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import properties,pads_stream,UNIT
from build_routed_copy import snapshot
s=snapshot(R/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc')
cs=properties(s['Components6/Data']);ps=pads_stream(s['Pads6/Data']);ns=properties(s['Nets6/Data'])
ji=next(i for i,c in enumerate(cs) if c['SOURCEDESIGNATOR']=='J1')
print('J1',json.dumps(cs[ji],indent=2))
print('J1_PADS',json.dumps([{'n':p['number'],'layer':p['layer'],'xy_sizes_mm':[v*UNIT for v in p['coords']],'rotation':p['rotation']} for p in ps if p['component']==ji],indent=2))
print('MOUNTS',json.dumps([{'n':p['number'],'layer':p['layer'],'xy_sizes_mm':[v*UNIT for v in p['coords']]} for p in ps if p['component']==65535],indent=2))
print('BODY_STREAMS',[k for k in s if any(a in k.lower() for a in ('body','bodies','model'))])
