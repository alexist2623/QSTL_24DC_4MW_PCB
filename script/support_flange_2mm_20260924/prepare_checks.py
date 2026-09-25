"""Adapt the established native drawing and geometry checks for flange revision C."""
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];old=H.parent/'cnc_drawings_20260922'
s=(H.parent/'probe_rod_inspection/verify_dropped_adapter.py').read_text()
s=s.replace("assert np.allclose(after, before, atol=1e-10)","\n        if r['name'].startswith('Rod_Clamp_M3_'):\n            before = before.copy(); before[2,3] += 2.0\n        assert np.allclose(after, before, atol=1e-10)")
(H/'verify_assembly.py').write_text(s)
s=(old/'build_native_dwg.ps1').read_text(encoding='utf-8-sig')
s=s.replace('script\\cnc_drawings_20260922','script\\support_flange_2mm_20260924').replace('RevB','RevC').replace('REV B','REV C').replace('2026-09-22','2026-09-24')
s=s.replace("$null=Dim $end @($fx,0,8.5) @($fx,0,12.5) V 60 247 4", "$bx=if($isLeft){2.0}else{49.0}\n  $null=Dim $end @($bx,0,10.5) @($fx,0,12.5) V 55 249 2\n  Lead $end @($bx,0,10.5) 28 274 'C2 X 45 DEG - OUTER EDGE'")
s=s.replace('THROUGH 4.00 FLANGE','THROUGH 2.00 FLANGE')
(H/'build_dwg.ps1').write_text(s,encoding='utf-8-sig')
s=(old/'verify_native_dwg.ps1').read_text(encoding='utf-8-sig').replace('RevB','RevC')
(H/'verify_dwg.ps1').write_text(s,encoding='utf-8-sig')
print('Prepared revision C native drawing builder and saved-CAD checks.')
