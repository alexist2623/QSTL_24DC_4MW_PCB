"""Promote the verified synchronized schematic/library into the existing project."""
from pathlib import Path
import json,hashlib,shutil,configparser,csv
H=Path(__file__).resolve().parent;ROOT=H.parents[1];P=ROOT/'QSTL_QD4_2SET_38PAD';N='QSTL_QD4_2SET_38PAD'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((H/'backup/manifest.json').read_text())
for name in (N+'.SchDoc','QD4_2SET_38.PcbLib'):
    assert sha(P/name)==frozen[name],name
for name in (N+'.SchDoc','QD4_2SET_38.PcbLib','Capacitors_1206.PcbLib','schematic_validation.json'):shutil.copy2(H/name,P/name)
cfg=configparser.ConfigParser(interpolation=None,strict=False);cfg.optionxform=str;cfg.read(P/(N+'.PrjPcb'))
if not any(cfg.get(s,'DocumentPath',fallback='')=='Capacitors_1206.PcbLib' for s in cfg.sections()):
    n=max(int(s[8:]) for s in cfg.sections() if s.startswith('Document') and s[8:].isdigit())+1
    cfg['Document'+str(n)]={'DocumentPath':'Capacitors_1206.PcbLib'}
with (P/(N+'.PrjPcb')).open('w') as f:cfg.write(f,space_around_delimiters=False)
# Preserve historical mapping columns in the proposal, update canonical fields.
rows=list(csv.DictReader((P/'DC_Shielded_Plan_20261016/proposed_pin_mapping.csv').open()))
fields=['qd_pad','chip_net','zif_pin','dc_net','dc_layer','rf','rf_net','smp','resistor','capacitor']
for r in rows:r['zif_pin']=r['proposed_zif_pin'];r['dc_layer']=r['proposed_dc_layer']
with (P/'pin_mapping.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
(H/'promoted_schematic.json').write_text(json.dumps({name:sha(P/name) for name in (N+'.SchDoc',N+'.PrjPcb','QD4_2SET_38.PcbLib','Capacitors_1206.PcbLib','pin_mapping.csv')},indent=2))
print('Promoted synchronized schematic, footprint libraries and mapping into existing project.')
