"""Prepare the authorized M1 revision in the original PCB project."""
from pathlib import Path
import shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
for name,src in [('before_m1.PcbDoc',P/'QSTL_24DC_4MW_PCB.PcbDoc'),('before_m1_validation.json',H/'validation.json')]:
    if not (H/name).exists():shutil.copy2(src,H/name)
code=(H/'ResizeM16.pas').read_text()
code=code.replace('ResizeM16','ResizeM1').replace('P.HoleSize:=MMsToCoord(1.8)','P.HoleSize:=MMsToCoord(1.2)').replace('MMsToCoord(2.2)','MMsToCoord(1.6)')
code=code.replace('P.Y:=MMsToCoord(1.2);',"If P.Name='MH7' Then P.X:=MMsToCoord(1.05) Else P.X:=MMsToCoord(18.45);P.Y:=MMsToCoord(1.2);")
code=code.replace('M1.6;HOLE=1.8;LAND=2.2;Y=1.2;','M1;HOLE=1.2;LAND=1.6;X=1.05/18.45;Y=1.2;').replace('resize_native.txt','resize_m1_native.txt')
(H/'ApplyM1.pas').write_text(code+'\n'+(H/'AuditAll.pas').read_text()+'\nProcedure ApplyM1AndAudit;Begin ResizeM1;AuditAll;End;\n',encoding='ascii')
(H/'ApplyM1.PrjScr').write_text('[Design]\nVersion=1.0\nHierarchyMode=0\n[Document1]\nDocumentPath=ApplyM1.pas\nAnnotationEnabled=1\n',encoding='ascii')
req=P/'docs/DESIGN_REQUIREMENTS.md';t=req.read_text(encoding='utf-8')
needle='- Latest ZIF size correction (2026-09-25):';a=t.index(needle);b=t.index('\n\n',a)
t=t[:b]+' Implement using Content Center KS B 1021 M1 x 4, pitch 0.25 mm, head diameter 2.0 mm and head height 0.65 mm. Use 1.2 mm plated clearance drills and 1.6 mm lands at (1.05,1.20) and (18.45,1.20) mm, pitch 17.40 mm. Moving the two end holes 0.55 mm outward gives 0.30 mm nominal cable-to-hole lateral clearance while retaining the board outline; verify the saved dimensions and actual native fit.'+t[b:]
req.write_text(t,encoding='utf-8')
print('Prepared ApplyM1.PrjScr')
