"""Inspect fixed proposal schemas and freeze target native files before edits."""
from pathlib import Path
import sys, json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
P=ROOT/'QSTL_QD4_2SET_38PAD'
backup=HERE/'backup';backup.mkdir(exist_ok=True)
manifest={}
for path in P.iterdir():
    if path.suffix.lower() in ('.pcbdoc','.schdoc','.prjpcb','.pcblib','.schlib') or path.name in ('pin_mapping.csv','schematic_validation.json'):
        dest=backup/path.name
        if not dest.exists():shutil.copy2(path,dest)
        manifest[path.name]=hashlib.sha256(dest.read_bytes()).hexdigest()
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
sys.path[:0]=[str(ROOT/'script/rf_redline_review_20261011'),str(ROOT/'script/_support/zif_revision/schematic')]
import finalize_shielded_rf_20261016 as rf
data,groups,st=rf.load_routes()
dc=json.loads((P/'DC_Shielded_Plan_20261016/dc_routed_plan.json').read_text())
snap=json.loads((ROOT/'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json').read_text())
sh=json.loads((P/'Shielded_Symmetric_RF_Plan_20261016/shielded_rf_plan.json').read_text())
print('DATA',json.dumps({k:v for k,v in data.items() if k not in ('groups','smp','QD','ZIF')})[:5000])
for label,obj in [('data',data),('group',groups[0]),('static',st),('dc',dc),('shield',sh)]:
    print(label,{k:(str(type(v)),len(v) if hasattr(v,'__len__') else '') for k,v in obj.items()})
for k in ('routes','vias','top_fanout'):print(k,dc[k][0])
print('GROUP', {k:v for k,v in groups[0].items() if k not in ('qline','sline','lines','envelope','capg','resg','qd_to_c2','smp_to_c1')})
print('VIA',sh['vias'][0]); print('QD',data.get('QD'));print('ZIF',str(data.get('ZIF'))[:2200])
import build_zif_schematic as sch
rows=sch.records(P/'QSTL_QD4_2SET_38PAD.SchDoc');cg=sch.component_groups(rows)
print('J1',cg['J1'][:6]); print('LABELS',[(i,r) for i,r in enumerate(rows) if r.get('RECORD')=='25'][:5])
print('SCH_VALIDATION',json.loads((P/'schematic_validation.json').read_text()).keys())
