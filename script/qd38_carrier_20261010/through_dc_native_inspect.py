from pathlib import Path
import json,importlib.util,sys,struct
h=Path(__file__).resolve().parent;root=h.parents[1];dest=root/'QSTL_QD4_2SET_38PAD'
spec=importlib.util.spec_from_file_location('nr',root/'script/_support/zif_revision_v2/render_native_layout.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);r.SOURCE=dest/'QSTL_QD4_2SET_38PAD.PcbDoc'

with r.olefile.OleFileIO(r.SOURCE) as o:b={'/'.join(k):o.openstream(k).read() for k in o.listdir()}
cs=r.props(b['Components6/Data']);print('component0',cs[0]);print('component1',cs[1]);p=json.loads((dest/'full_copper_candidate.json').read_text());print('plan keys',p.keys());print('plan comp',p['components'][0]);print('plan pads',p['physical_pads'][:2]);print('planvia',p['vias'][0]);print('sch keys',json.loads((dest/'schematic_validation.json').read_text()).keys())
for k in ['Regions6/Header','ShapeBasedRegions6/Header','Texts6/Header','Arcs6/Header','Connections6/Header']:
 print(k,b.get(k))
for v in list(r.binary(b['Vias6/Data'],3))[:1]:print('via bytes',len(v),list(v[:70]))
for v in list(r.binary(b['Regions6/Data'],11))[:1]:print('region bytes',len(v),v[:300])
