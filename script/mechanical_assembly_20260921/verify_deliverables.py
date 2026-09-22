"""Verify source preservation and the exported mechanical assembly geometry."""
from pathlib import Path
import hashlib
import json
from inspect_geometry import read, bounds, volume

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'QSTL_24DC_4MW_PCB' / 'Mechanical_Assembly'
SOURCE = Path('C:/Users/박정현/Nextcloud3/Lab/Instruments/CustomParts/Carrier_8MW_24DC/Mechanical/Narrow_V3_24DC_8MW')
EXPECTED = {
    SOURCE / 'Bottom.SLDPRT': 'BF18CB81FC57202FD1FA0EC75F10D2123FF039342B51967CE9B0C1B72F48E228',
    SOURCE / 'Top.SLDPRT': 'F025481E7F5F13A52E3160A5F4153AE0F1CB326DEAD542656E4FC07E4D9598B9',
    SOURCE / 'Top_ForFridge.SLDPRT': '9297E508D5C7C758613860F31F2E4896C0C0D03101450073CEFF5E0084B8C1ED',
    ROOT / 'QSTL_24DC_4MW_PCB' / 'QSTL_24DC_4MW_PCB.PcbDoc': '84feed018fbaf5cbfa3203201c8771711b00ffec18aa0aadaf20fdeadb99ca63',
}
preserved = {}
for path, expected in EXPECTED.items():
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    assert actual.lower() == expected.lower(), str(path)
    preserved[str(path)] = actual

fit = json.loads((OUT / 'assembly_validation.json').read_text())
assert fit['top_source'] == 'Top_ForFridge.SLDPRT'
native = json.loads((OUT / 'inventor_occurrences.json').read_text(encoding='utf-8-sig'))
for assembly in ('Carrier_with_PCB', 'Carrier_exploded'):
    rows = [r for r in native if r['assembly'] == assembly]
    assert len(rows) == 3
    assert any(Path(r['source']).name == 'Top_ForFridge.ipt' for r in rows)
    assert all(Path(r['source']).resolve().is_relative_to(OUT.resolve()) for r in rows)

exported = read(OUT / 'Carrier_with_PCB.step')
expected_shape = read(OUT / 'Carrier_with_PCB_geometry.step')
bound_error = max(abs(a-b) for a,b in zip(bounds(exported),bounds(expected_shape)))
volume_error = abs(volume(exported)-volume(expected_shape))
assert bound_error < 1e-4, bound_error
assert volume_error < 1e-2, volume_error
passives = [c for c in fit['interference_checks'] if c['component'].startswith(('R','C'))]
assert all(c['overlap_mm3'] < 1e-6 for c in passives)
report = dict(source_hashes_verified=preserved,assembly_step_bound_error_mm=bound_error,
              assembly_step_volume_error_mm3=volume_error,passive_minimum_clearance_mm=min(c['minimum_distance_mm'] for c in passives),
              original_pcb_and_cad_unchanged=True,top_source='Top_ForFridge.SLDPRT')
(OUT / 'delivery_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
