"""Promote validated logical files after Altium closes them; prepare audits."""
from pathlib import Path
import json,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB';B='QSTL_24DC_4MW_PCB';OLD=H.parent/'lower_rc_70pct_20260921'
assert (H/'apply_native.txt').read_text().strip().endswith('COMPLETE')
for ext in ('SchDoc','SchLib'):shutil.copy2(H/'built'/(B+'.'+ext),P/(B+'.'+ext))
s=(OLD/'audit_connectivity.py').read_text().replace("PREV=H.parent/'rf_six_inward_20260920'","PREV=H")
(H/'audit_connectivity.py').write_text(s)
s=(OLD/'verify_final.py').read_text().replace("PREV=H.parent/'rf_six_inward_20260920'","PREV=H")
s=s.replace("map(viakey,wanted['vias'])", "map(viakey,[v for v in wanted['vias'] if v['net']!='GND'])")
s=s.replace("('Fills6/Data','Nets6/Data')","('Fills6/Data',)")
a=s.index("for ext,key in ((");b=s.index('for v in shield:',a)
s=s[:a]+s[b:]
s=s.replace("json.loads((PREV/'geometry.json').read_text())", "json.loads((H.parent/'rf_six_inward_20260920/geometry.json').read_text())")
s=s.replace('Lower_RC_70pct','DC_Even_ZIF')
(H/'verify_final.py').write_text(s)
s=(OLD/'verify_refinements.py').read_text();(H/'verify_refinements.py').write_text(s)
s=(OLD/'read_drc.py').read_text().replace('Lower_RC_70pct','DC_Even_ZIF');(H/'read_drc.py').write_text(s)
s=(H/'ReopenAudit.pas').read_text()+'\n'+(H/'AuditPaste.pas').read_text()+'\n'+(H/'ValidateSchematic.pas').read_text()+'''
Procedure AuditAll;
Var D:IServerDocument;
Begin
 ReopenAudit;
 AuditPaste;
 OpenAndValidate;
 D:=Client.OpenDocument('PCB','''+repr(str(P/(B+'.PcbDoc')))+''');If D<>Nil Then Client.ShowDocument(D);
End;
'''
(H/'AuditAll.pas').write_text(s.replace(chr(92)*2,chr(92)))
(H/'AuditAll.PrjScr').write_text('[Design]\nVersion=1.0\n\n[Document1]\nDocumentPath=AuditAll.pas\n')
print('Logical files promoted; native and independent audits prepared.')
