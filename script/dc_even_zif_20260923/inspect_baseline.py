"""Inspect the saved PCB and preserve the pre-edit design."""
from pathlib import Path
import sys,json,importlib.util,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';W=H.parent/'_support';B='QSTL_24DC_4MW_PCB'
for ext in ['PcbDoc','SchDoc','SchLib','PrjPcb']:
 d=H/('before.'+ext)
 if not d.exists():shutil.copy2(P/(B+'.'+ext),d)
spec=importlib.util.spec_from_file_location('reader',W/'zif_revision_v2/render_native_layout.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SOURCE=H/'before.PcbDoc';n=m.read_native()
(H/'before_native.json').write_text(json.dumps(n,indent=2))
print('HASH',n['source_sha256'])
print('ZIF',[(p['number'],p['net'],*[round(p[k],4) for k in ('x','y','size_x','size_y')]) for p in n['pads'] if p['component']=='J1'])
print('VIAS',[(v['net'],*[round(v[k],4) for k in ('x','y','diameter','hole')]) for v in n['vias'] if v['y']<12])
print('TRUNKS',[(t['net'],t['layer'],*[round(t[k],4) for k in ('x1','y1','x2','y2')]) for t in n['tracks'] if t['net'].startswith('ZIF') and min(t['y1'],t['y2'])<12<max(t['y1'],t['y2'])])
print('TOP',[(t['net'],*[round(t[k],4) for k in ('x1','y1','x2','y2')]) for t in n['tracks'] if t['layer']==1])
f=P/'docs/DESIGN_REQUIREMENTS.md';s=f.read_text(encoding='utf-8')
s=s.replace('Connect 18 DC-only QD pads and six RF bias resistors to ZIF pins 1-12 and 15-26 only. Preserve the verified carrier-to-footprint physical contact numbering.', 'Connect the 18 DC-only QD pads and six RF bias resistors to the 24 even ZIF contacts 2, 4, 6, ..., 48 only, matching Anton\'s adapter contact convention. Pin 50 is explicitly unused; all odd contacts remain NC. Preserve the actual footprint contact numbering and synchronize the schematic, QD library labels and PCB. This supersedes the previous 1-12 and 15-26 assignment.')
s=s.replace('- Current bias assignments: ZIF21 to R1.2, ZIF25 to R2.2, ZIF23 to R3.2, ZIF26 to R4.2, ZIF02 to R5.2, ZIF04 to R6.2.', '- Bias assignments must be regenerated with the even-contact routing; all six resistor DC pads remain connected and all RF pad assignments remain unchanged.')
f.write_text(s,encoding='utf-8')
