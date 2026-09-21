"""Reuse the complete routing/schematic audit with the revised paste requirements."""
from pathlib import Path

here = Path(__file__).resolve().parent
previous = here.parent / 'rf_six_inward_20260920'
source = (previous / 'verify_native.py').read_text()
source = source.replace("H=Path(__file__).resolve().parent;W=H.parent/'_support'", "H=Path(__file__).resolve().parent;PREV=H.parent/'rf_six_inward_20260920';W=H.parent/'_support'")
for name in ('validator_source.py', 'geometry.json', 'expected.json', 'dc_routes.json', 'rf_routes.json'):
    source = source.replace(f"H/'{name}'", f"PREV/'{name}'")
source = source.replace("H/(B+'.PcbDoc')", "PREV/(B+'.PcbDoc')")
source = source.replace("H/(B+'.PcbLib')", "PREV/(B+'.PcbLib')")
source = source.replace("paste=paste_audit(regions,vs);check(paste['passed'],'Via paste aperture mismatch')", "mask_ground=json.loads((D/'mask_ground_validation.json').read_text());paste=mask_ground['paste'];check(mask_ground['passed'] and mask_ground['pcb_sha256']==sha(P/(B+'.PcbDoc')),'Mask/ground audit failed or stale')")
source = source.replace('RF6_DRC.html', 'Mask_Ground_DRC.html')
source = source.replace("mask_exception='Via-in-pad holes share Bottom pad solder-mask openings; all via-specific top/bottom tent flags and paste apertures are present.'", "mask_ground=mask_ground,mask_exception='Via-in-pad shares normal component pad openings. Dedicated via paste apertures are removed; SMP and mounting pad paste is disabled; solder-control mask is retained.'")
exec(compile(source, str(here / 'verify_design.py'), 'exec'), {'__file__': str(here / 'verify_design.py'), '__name__': '__main__'})
