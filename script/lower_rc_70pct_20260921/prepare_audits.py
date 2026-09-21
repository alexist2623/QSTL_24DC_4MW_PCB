"""Instantiate saved-file audits for the authorized movement and via removal."""
from pathlib import Path
import json
H=Path(__file__).resolve().parent;OLD=H.parent/'remove_resistor_rf_vias_20260921';RC=H.parent/'rc_mask_clearance_20260921'
plan=json.loads((H/'plan.json').read_text());count=len(plan['shield_vias'])
for name in ('audit_connectivity.py','verify_final.py','AuditPaste.pas','ReopenAudit.pas','read_drc.py','fabrication_notes.py','publish_outputs.py','verify_fabrication.py'):
    s=(OLD/name).read_text().replace(OLD.name,H.name).replace('Resistor_RF_Via_Removal','Lower_RC_70pct').replace('resistor_rf_via_removal_reopen_check','lower_rc_70pct_reopen_check')
    s=s.replace('len(shield)==470',f'len(shield)=={count}').replace('len(holes)==470',f'len(holes)=={count}').replace('470 GND shields',f'{count} GND shields').replace('470 saved L5-L6 vias',f'{count} saved L5-L6 vias')
    if name=='verify_final.py':
        s=s.replace('plan=json.loads', 'original_arckey=arckey\ndef arckey(a):\n    k=original_arckey(a);return k[:-2]+(k[-2]%360,k[-1]%360)\nplan=json.loads',1)
        s=s.replace("if c=='Q1' or (c.startswith('R')", "if (c=='Q1' and net.startswith('ZIF')) or (c.startswith('R')")
        s=s.replace("if c.startswith('R') and p['number']=='1':", "if (c=='Q1' and net.startswith('MW')) or (c.startswith('R') and p['number']=='1'):")
        s=s.replace('(22,147,37,524)',f'(22,147,37,{48+count})').replace('len(signal)==54','len(signal)==48')
        a=s.index('from preservation_helpers import text_fingerprint');b=s.index('for ext,key in',a)
        s=s[:a]+"for stream in ('Fills6/Data','Nets6/Data'):\n    check(s[stream]==old[stream],'Unrequested object change '+stream)\n"+s[b:]
        s=s.replace("map(viakey,vs))==collections.Counter(map(viakey,wanted['vias']))", "map(viakey,signal))==collections.Counter(map(viakey,wanted['vias']))")
        s=s.replace('resistor_DC_vias_remaining=6,','resistor_DC_vias_remaining=6,QD_RF_vias_remaining=0,QD_DC_vias_remaining=18,')
    if name=='publish_outputs.py':
        s=s.replace('QD via-in-pad retained | C vias removed','18 QD DC vias retained | RF pads via-free')
        s=s.replace('C1-C6: no through vias |','QD/R/C RF pads: no vias |')
    if name=='fabrication_notes.py':
        s=s.replace('54 through vias','48 through vias').replace('24 QD','18 QD DC')
        s=s.replace('Preserve QD via-in-pad and one DC-side via', 'Remove the six QD RF-pad vias (1/6/9/12/18/24); their routes remain entirely on L6. Preserve via-in-pad on the 18 QD DC pads and one DC-side via')
    (H/name).write_text(s,encoding='utf-8')
(H/'verify_refinements.py').write_text((RC/'verify_refinements.py').read_text(),encoding='utf-8')
# Correct the historical label in the reused geometric preflight report.
f=H/'preflight_plan.py';s=f.read_text().replace('planned_capacitor_vias_removed=12','planned_QD_RF_vias_removed=6');f.write_text(s,encoding='utf-8')
print('Prepared audits for',count,'blind shields and 48 required signal through vias.')
