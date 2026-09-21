from pathlib import Path
import json,importlib.util,sys,collections
h=Path('script/lower_rc_70pct_20260921').resolve();w=h.parent/'_support'
sys.path[:0]=[str(w/x) for x in ('qd_center_revision','final_routing/schematic','zif_revision_v2/board')]
from verify_final_native_v2 import trackkey,arckey
spec=importlib.util.spec_from_file_location('reader',w/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=h.parents[1]/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc';n=m.read_native();p=json.loads((h/'planned_native.json').read_text())
print('COUNTS',len(n['vias']),len(n['tracks']),len(p['tracks']))
for field,key in [('tracks',trackkey),('arcs',arckey)]:
 a=collections.Counter(map(key,n[field]));b=collections.Counter(map(key,p[field]));print(field,'EXTRA',list((a-b).elements()),'MISSING',list((b-a).elements()))
