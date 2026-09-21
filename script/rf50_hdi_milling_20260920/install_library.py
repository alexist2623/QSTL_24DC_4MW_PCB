"""Install the prepared footprint after checking the saved board pad positions."""
from pathlib import Path
import json,sys,shutil
H=Path(__file__).resolve().parent;W=H.parent/'_support';P=H.parents[1]/'QSTL_24DC_4MW_PCB';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic')]
from native_metadata_helpers import sha,properties,pads_stream,UNIT
from build_routed_copy import snapshot
plan=json.loads((H/'plan.json').read_text());lp=json.loads((H/'library_plan.json').read_text());source=P/(B+'.PcbLib')
assert sha(source) in (lp['source_sha256'],lp['prepared_sha256']),'Library changed independently'
s=snapshot(P/(B+'.PcbDoc'));cs=properties(s['Components6/Data']);ps=pads_stream(s['Pads6/Data'])
qd={p['number']:p for p in ps if p['component']!=65535 and cs[p['component']]['SOURCEDESIGNATOR']=='Q1'}
for m in plan['pad_moves']:
    p=qd[m['number']];assert all(abs(a*UNIT-b)<6*UNIT for a,b in zip(p['coords'][:2],m['new']))
shutil.copy2(H/'QD_updated.PcbLib',source)
print('Installed matching QD4 into original footprint library',sha(source))
