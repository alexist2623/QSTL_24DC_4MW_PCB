"""Isolate the proven paste audit job generator in this revision directory."""
from pathlib import Path
import sys
H=Path(__file__).resolve().parent
OLD=H.parent/'qd38_rotation_20261011'
code=(OLD/'prepare_revision_paste_cam.py').read_text()
code=code.replace('ExportQD90PasteAuditLinked','ExportQD38PasteAlignment')
sys.argv=[str(Path(__file__)), '--candidate',str(H/'alignment_full_candidate.json'),'--audit',str(H/'alignment_full_audit.json')]
exec(compile(code,str(H/'prepare_revision_paste_cam.py'),'exec'),{'__name__':'__main__','__file__':str(H/'prepare_revision_paste_cam.py')})
