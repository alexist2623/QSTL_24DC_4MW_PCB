"""Prepare an eight-resistor mesh-transform-only correction."""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';OLD=ROOT/'script/qd_via_land_20261017'
pcb=P/(P.name+'.PcbDoc');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(pcb)=='97581f7c13d63e503f25b2d211d5f3593e22ee7ad6817f86f47d3dbe955f0d7f'
bk=H/'baseline';bk.mkdir(exist_ok=True)
for src in (pcb,P/(P.name+'.SchDoc'),P/'pin_mapping.csv'):
    dst=bk/src.name
    if dst.exists():assert sha(dst)==sha(src)
    else:shutil.copy2(src,dst)
inspection=json.loads((H/'inspection.json').read_text());assert inspection['source_sha256']==sha(pcb)
rows=[r for r in inspection['resistors'] if abs(float(r['component_rotation'])%90)>1e-6];assert len(rows)==8
plan=json.loads((OLD/'candidate.json').read_text())
for r in rows:plan['model_rotation_overrides'][r['ref']]=(-float(r['component_rotation']))%360
(H/'candidate.json').write_text(json.dumps(plan,indent=2))
out=P/'Resistor_Models_20261017';out.mkdir(exist_ok=True)
shutil.copy2(OLD/'dispatch.py',H/'dispatch.py')
pas=(OLD/'CorrectCapModels.pas').read_text().replace('CorrectCapModels','CorrectResistorModels').replace(OLD.name,H.name)
for r in rows:pas=pas.replace("C.Name.Text='C"+r['ref'][1:]+"'","C.Name.Text='"+r['ref']+"'")
pas=pas.replace('MMsToCoord(1.8)','MMsToCoord(0.45)')
assert "C.Name.Text='C" not in pas
def write(stem,text):
    (H/(stem+'.pas')).write_text(text,encoding='ascii')
    (H/(stem+'.PrjScr')).write_text(f'[Design]\nVersion=1.0\n[Document1]\nDocumentPath={stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={stem}.pas>{stem}\n',encoding='ascii')
write('CorrectResistorModels',pas)
validation=(OLD/'ValidateNative16RF.pas').read_text().split('Procedure CompileProject')[0].replace(OLD.name,H.name)
validation+='\nProcedure ValidateResistorModels;\nBegin SaveAndCheckNative;End;\n'
write('ValidateResistorModels',validation)
(H/'preparation.json').write_text(json.dumps(dict(source_sha256=sha(pcb),changed_refs=[r['ref'] for r in rows],model_changes=[dict(ref=r['ref'],before=r['model_rotation'][2],after=plan['model_rotation_overrides'][r['ref']]) for r in rows]),indent=2))
print(json.dumps(dict(prepared=True,refs=[r['ref'] for r in rows]),indent=2))
