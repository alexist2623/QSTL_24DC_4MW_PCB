"""Preserve the current copied carrier before its authorized rotation revision."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[1]/'QSTL_QD4_2SET_38PAD'
OUT=HERE/'before_rotation'
OUT.mkdir(exist_ok=True)
names=[p.name for p in PROJECT.iterdir() if p.suffix.lower() in ('.pcbdoc','.schdoc','.pcblib','.schlib','.prjpcb')]
names += ['design_plan.json','circuit_plan.json','full_copper_candidate.json','negotiated_plan.json','pin_mapping.csv','schematic_validation.json','copy_provenance.json','work_state_audit.json','README.md']
manifest={}
for name in names:
    src=PROJECT/name
    if not src.is_file():
        continue
    dst=OUT/name
    h=hashlib.sha256(src.read_bytes()).hexdigest()
    if dst.exists():
        assert hashlib.sha256(dst.read_bytes()).hexdigest()==h, name
    else:
        shutil.copy2(src,dst)
    manifest[name]=h
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'files_preserved':len(manifest),'pcb_sha256':manifest['QSTL_QD4_2SET_38PAD.PcbDoc'],'backup':str(OUT)}))
