"""Prepare native, reversible ZIF-end mounting-hole edits."""
from pathlib import Path
import hashlib, shutil

H=Path(__file__).resolve().parent
R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
source=P/'QSTL_24DC_4MW_PCB.PcbDoc'
expected='833555d572fb9945703213acef1ecd809d7eb3ce4a73d5e467c577d3ef70bc90'
assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
backup=H/'before_mounts.PcbDoc'
if not backup.exists():shutil.copy2(source,backup)
assert source.read_bytes()==backup.read_bytes()
audit=(H.parent/'dwg_gerber_refresh_20260924/AuditAll.pas').read_text(encoding='utf-8-sig')
audit=audit.replace('script\\dwg_gerber_refresh_20260924','script\\pcb_end_mounts_20260925')
audit=audit.replace('fabrication\\JLCPCB_HDI_20260924','fabrication\\JLCPCB_HDI_20260925')
(P/'fabrication/JLCPCB_HDI_20260925').mkdir(parents=True,exist_ok=True)
(H/'AuditAll.pas').write_text(audit,encoding='ascii')
(H/'EndMounts.PrjScr').write_text('[Design]\nVersion=1.0\nHierarchyMode=0\n\n[Document1]\nDocumentPath=EndMounts.pas\nAnnotationEnabled=1\n\n[Document2]\nDocumentPath=AuditAll.pas\nAnnotationEnabled=1\n',encoding='ascii')
print('Source backed up; native script project prepared.')
