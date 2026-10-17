"""Inspect QD terminal vias and the native via rules before resizing."""
from pathlib import Path
import sys,json,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD'
sys.path.insert(0,str(ROOT/'script/qd38_rotation_20261011'))
from audit_saved_revision_surface import read_snapshot
from prepare_native_revision_rules import read_rules
pcb=P/(P.name+'.PcbDoc');s=read_snapshot(pcb,json.loads((P/'schematic_validation.json').read_text()))
plan=json.loads((ROOT/'script/rc_mask_margin_20261017/candidate.json').read_text())
rules={k:v for k,v in read_rules(pcb).items() if 'Via' in v.get('RULEKIND','') or 'Annular' in v.get('RULEKIND','')}
result=dict(source_sha256=hashlib.sha256(pcb.read_bytes()).hexdigest(),QD_vias=[v for v in plan['vias'] if v['label'].startswith('Q1-')],via_rules=rules)
(H/'inspection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(dict(source_sha256=result['source_sha256'],QD_vias=len(result['QD_vias']),via_rules=rules),indent=2))
