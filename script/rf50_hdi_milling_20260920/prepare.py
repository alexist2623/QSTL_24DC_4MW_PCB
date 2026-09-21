"""Capture the input design and record the latest fabrication requirements."""
from pathlib import Path
import sys, json, shutil, importlib.util
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
sys.path[:0]=[str(W/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board','rf_revision','route_python')]
from native_metadata_helpers import sha,properties
from build_routed_copy import snapshot
from verify_final_native_v2 import read_rules
if not (H/'before.PcbDoc').exists():
    assert sha(P/(B+'.PcbDoc'))=='bd8c71fd36253a7f13eab69a7828f3587760a34894e2eb19c72f3818caaff793'
    shutil.copy2(P/(B+'.PcbDoc'),H/'before.PcbDoc')
    for name in ('validation.json','mask_ground_validation.json','connection_validation.json'):
        shutil.copy2(P/'docs'/name,H/('before_'+name))
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader);reader.SOURCE=H/'before.PcbDoc';n=reader.read_native()
(H/'before_native.json').write_text(json.dumps(n,indent=2))
s=snapshot(H/'before.PcbDoc');b=properties(s['Board6/Data'])[0]
(H/'before_stack.json').write_text(json.dumps({k:v for k,v in b.items() if 'STACK' in k or 'LAYER' in k},indent=2))
(H/'before_rules.json').write_text(json.dumps(read_rules(s['Rules6/Data']),indent=2))
print(json.dumps(dict(RF_tracks=[t for t in n['tracks'] if t['layer']==32],SMP_pads=[p for p in n['pads'] if p['component']=='SMP1'],layers=n.get('layers')),indent=2))
