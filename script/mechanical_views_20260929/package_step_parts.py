"""Validate and package the latest native Inventor STEP exports for the three parts."""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import math
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parents[2]
model = root / 'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
out = model / 'STEP_Parts_20260929'
out.mkdir(exist_ok=True)
sys.path.insert(0, str(root / 'script/mechanical_assembly_20260921'))
from inspect_geometry import read, inspect
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

audit = json.loads((model / 'Manufacturing_DWG/delivery_audit.json').read_text(encoding='utf-8-sig'))
expected = {row['file']: row['sha256'].lower() for row in audit['files']}
parts = [
    ('CP-01', 'Centre_Plate', [39.0, 80.0, 10.0]),
    ('LS-01', 'Left_Rod_Support', [12.0, 80.0, 8.5]),
    ('RS-01', 'Right_Rod_Support', [12.0, 80.0, 8.5]),
]
records = []
for code, name, dimensions in parts:
    native = model / f'{name}.ipt'
    source = model / f'{name}.step'
    native_hash = sha256(native.read_bytes()).hexdigest()
    source_hash = sha256(source.read_bytes()).hexdigest()
    assert native_hash == expected[native.name], f'{native.name} differs from the Rev E source.'
    assert source_hash == expected[source.name], f'{source.name} differs from the audited native export.'
    text = source.read_text(encoding='ascii', errors='replace')
    assert 'SI_UNIT(.MILLI.,.METRE.)' in text.replace(' ', '').replace('\n', ''), 'Expected millimetres.'
    shape = read(source)
    data = inspect(shape)
    assert data['valid'] and data['volume'] > 0, name
    solids = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while solids.More():
        count += 1
        solids.Next()
    assert count == 1, f'{name}: expected one manufactured solid.'
    actual_dimensions = [data['bounds'][i + 3] - data['bounds'][i] for i in range(3)]
    assert max(abs(a-b) for a, b in zip(actual_dimensions, dimensions)) < 1e-6, (name, actual_dimensions)
    if code != 'CP-01':
        bevels = [p for p in data['planes']
                  if abs(abs(p['normal'][0])-math.sqrt(0.5)) < 1e-7
                  and abs(abs(p['normal'][2])-math.sqrt(0.5)) < 1e-7]
        assert len(bevels) == 1
        assert abs(bevels[0]['bounds'][5]-bevels[0]['bounds'][2]-1.6) < 1e-6
        mounting_holes = [c for c in data['cylinders']
                          if abs(c['radius']-1.7) < 1e-7 and abs(abs(c['axis'][2])-1) < 1e-7]
        assert len(mounting_holes) == 4
        assert all(abs(c['bounds'][5]-c['bounds'][2]-1.6) < 1e-6 for c in mounting_holes)
    destination = out / f'{code}_{name}.step'
    shutil.copyfile(source, destination)
    assert sha256(destination.read_bytes()).hexdigest() == source_hash
    records.append({
        'part_number': code, 'file': destination.name,
        'source_ipt': str(native.relative_to(root)).replace('\\', '/'),
        'source_ipt_sha256': native_hash, 'step_sha256': source_hash,
        'matches_rev_e_native_export': True, 'solid_count': count,
        'valid_brep': data['valid'], 'units': 'mm',
        'bounds_mm': data['bounds'], 'dimensions_mm': actual_dimensions,
        'volume_mm3': data['volume'],
    })

report = {
    'packaged_utc': datetime.now(timezone.utc).isoformat(),
    'method': 'Unmodified native Inventor STEP exports, matched to the Rev E delivery audit.',
    'parts': records,
}
(out / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
(out / 'README.md').write_text('''# Split mount STEP parts

Latest saved geometry, packaged 2026-09-29. Units: millimetres.

| Part | STEP file | Description |
| --- | --- | --- |
| CP-01 | CP-01_Centre_Plate.step | Central plate with integral device-mounting boss and relief grooves |
| LS-01 | LS-01_Left_Rod_Support.step | Left support; 1.6 mm rod-contact flange and C1.6 x 45-degree bevel |
| RS-01 | RS-01_Right_Rod_Support.step | Right support; 1.6 mm rod-contact flange and C1.6 x 45-degree bevel |

These are the unmodified Inventor exports corresponding to the current native IPT files and Rev E drawings. Each STEP was reopened independently and verified as one valid solid. The part origins and orientations are retained from the individual source parts.

The supports retain four plain diameter 3.4 mm rod-mounting clearance holes each. Threaded holes retain their modeled pilot bores; STEP does not carry the Inventor cosmetic thread features. Use the matching Rev E DWGs in `../Manufacturing_DWG/` for M3 x 0.5 thread callouts and depths.

`validation.json` records source hashes and geometry checks. No source CAD or PCB geometry was changed while preparing this package.
''', encoding='utf-8')
archive = out / 'QSTL_Split_Mount_STEP_Parts_20260929.zip'
members = [out / row['file'] for row in records] + [out / 'README.md', out / 'validation.json']
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
    for path in members:
        z.write(path, path.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for row in records:
        assert sha256(z.read(row['file'])).hexdigest() == row['step_sha256']
print(json.dumps({'archive': str(archive), 'parts': records}, indent=2))
