"""Validate and package native plate-only drawings with their CAD references."""
from pathlib import Path
import hashlib
import json
import zipfile
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
OUT = MODEL / 'Manufacturing_DWG'
reader = PdfReader(OUT / 'QSTL_Split_Mount_RevE.pdf')
assert len(reader.pages) == 5
for page in reader.pages:
    txt = page.extract_text()
    for removed in ['Proposed RFQ', 'Supplier to state', 'NOTES:', 'BILL OF MATERIALS',
                    'ASSEMBLY SEQUENCE', 'SLEEVE', 'INSTALLATION / INSPECTION']:
        assert removed not in txt, removed
    assert 'NONE' in txt
    # Inventor rounds PDF MediaBox extents to whole points (up to 0.1764 mm).
    assert abs(float(page.mediabox.width) * 25.4 / 72 - 420) < .18
    assert abs(float(page.mediabox.height) * 25.4 / 72 - 297) < .18
assert '13.9334' in reader.pages[0].extract_text()
assert '9.8280' in reader.pages[0].extract_text()
assert 'EXPLODED ASSEMBLY' in reader.pages[4].extract_text()
assert 'SECTION C-C' in reader.pages[4].extract_text()
for page in reader.pages[2:4]:
    assert 'C1.6 X 45 DEG - OUTER EDGE' in page.extract_text()
    assert 'THROUGH 1.60 FLANGE' in page.extract_text()

native_audit = json.loads((OUT / 'native_dimension_audit.json').read_text(encoding='utf-8-sig'))
assert len(native_audit) == 46
for row in native_audit:
    assert abs(row['expected_mm'] - row['native_model_value_mm']) < 1e-7
    assert abs(float(row['displayed_text'].split()[0]) - row['expected_mm']) <= .5 * 10 ** -row['precision'] + 1e-7
for file, digest in json.loads((OUT / 'source_cad_hashes.json').read_text(encoding='utf-8-sig')).items():
    assert hashlib.sha256((MODEL / file).read_bytes()).hexdigest().upper() == digest

reopened = json.loads((OUT / 'dwg_reopen_audit.json').read_text(encoding='utf-8-sig'))
assert reopened['native_dimension_count'] == 46
assert len(reopened['standalone_files']) == 5
for sheet in reopened['native_sheets']:
    assert sheet['width_mm'] == 420 and sheet['height_mm'] == 297
    assert sheet['border'] and sheet['titleblock']
assert any(x.endswith('Split_Mount_Assembly.ipn') for x in reopened['native_sheets'][4]['references'])

readme = (Path(__file__).resolve().parent / 'DWG_README.md').read_text(encoding='utf-8')
(OUT / 'README.md').write_text(readme,encoding='utf-8')
files = [OUT / f'QSTL_Split_Mount_RevE_QSTL-{code}.dwg' for code in ['CP01','CP02','LS01','RS01','AS01']]
files += [OUT / name for name in ['QSTL_Split_Mount_RevE_Inventor.dwg', 'QSTL_Split_Mount_RevE.idw',
          'QSTL_Split_Mount_RevE.pdf', 'Split_Mount_Assembly.ipn', 'Split_Mount_Plate_Only.iam',
          'Split_Mount_Presentation_Source.iam', 'Eight_M3_Fasteners.iam']]
files += [MODEL / (part + '.ipt') for part in ['Centre_Plate','Left_Rod_Support','Right_Rod_Support']]
files += [MODEL / 'Standard_Fasteners/DIN_7991_M3x10.ipt', MODEL / 'content_center_fasteners.json']
files += [MODEL / (part + '.step') for part in ['Centre_Plate','Left_Rod_Support','Right_Rod_Support']]
files += [MODEL / 'device_relief_grooves.json']
files += [MODEL / 'support_flange_1p6mm_validation.json', MODEL / 'support_native_reopen.json', OUT / 'Split_Mount_Plate_Only.step']
archive = MODEL / 'QSTL_Plate_DWG_Package_RevE.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for file in files:
        assert file.stat().st_size > 0
        z.write(file, str(file.relative_to(MODEL)))
    z.write(OUT / 'README.md','README.md')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
audit = {'sheets':5,'paper':'ISO A3 landscape','native_dimensions':46,'source_cad_unchanged_during_drawing_generation':True,
         'native_presentation':'Split_Mount_Assembly.ipn','removed_blocks':['BILL OF MATERIALS','ASSEMBLY SEQUENCE'],
         'files':[{'file':str(p.relative_to(MODEL)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(OUT / 'delivery_audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps({'zip':str(archive),'pdf_sheets':5,'verified_dimensions':46,'native_dwg_files':6,'source_cad_unchanged_during_drawing_generation':True},indent=2))

