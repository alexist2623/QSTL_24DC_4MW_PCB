"""Bring the existing task's helpers into this repository; no design edits."""
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parent
OLD=Path(r'C:\Users\박정현\Documents\Codex\2026-09-19\new-chat\work')
SUPPORT=ROOT/'_support';H=ROOT/'rf_six_inward_20260920'
files=['qd_center_revision/native_metadata_helpers.py','qd_center_revision/cfb_copy_update.py','final_routing/schematic/build_routed_copy.py','zif_revision_v2/board/verify_final_native_v2.py','zif_revision_v2/render_native_layout.py','zif_revision_v2/schematic/build_v2_schematic.py','zif_revision_v2/schematic/validate_v2_schematic.py','zif_revision_v2/schematic/render_v2_schematic.py','zif_revision/schematic/build_zif_schematic.py','rf_revision/geometry_helpers.py','rf_revision/rf_native_helpers.pas','reference_placement/placements.json','rf_stubless_20260920/ApplyStubless.pas','rf_stubless_20260920/plan_routes.py','connection_audit_20260920/audit.py','connection_audit_20260920/ReopenAudit.pas','zif_revision_v2/native_helpers/FinalizeV2.pas']
files += ['dc_direct_20260920/'+p.name for p in (OLD/'dc_direct_20260920').iterdir() if p.suffix in ['.py','.json','.pas']]
for name in files:
 dst=SUPPORT/name;dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(OLD/name,dst)
for p in H.glob('*.py'):
 s=p.read_text(encoding='utf-8')
 s=s.replace('W=H.parent;',"W=H.parent/'_support';").replace('W=H.parent\n',"W=H.parent/'_support'\n").replace('WORK = HERE.parent',"WORK = HERE.parent / '_support'")
 p.write_text(s,encoding='utf-8')
print('Helpers and active scripts are now inside',ROOT)
