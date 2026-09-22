"""Validate and package native plate-only drawings with their CAD references."""
from pathlib import Path
import hashlib
import json
import zipfile
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / 'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
OUT = MODEL / 'Manufacturing_DWG'
reader = PdfReader(OUT / 'QSTL_Split_Mount_RevB.pdf')
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

readme = '''# Split mounting plate drawings - Rev B

The drawing layout was revised against the native Enclosure3 DWG/IPN workflow.
Scope: central plate with integral boss, left support, right support and their eight-screw assembly.

## Drawings

- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-CP01.dwg: central plate overall and hole-pattern dimensions.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-CP02.dwg: central plate thread and countersink sections.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-LS01.dwg and RS01.dwg: separate support drawings.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_QSTL-AS01.dwg: native presentation-linked exploded assembly, eight fastening axes, assembled boss-side view and fastening section C-C.
- Manufacturing_DWG/QSTL_Split_Mount_RevB_Inventor.dwg: combined five-sheet master.
- Manufacturing_DWG/QSTL_Split_Mount_RevB.pdf: print-layout companion.

All six DWGs are native Inventor drawings, with editable model-associated views and dimensions on ISO A3 landscape sheets. Native borders and title blocks are used. The manually typed BOM and assembly-sequence blocks were removed. No general NOTES block or cylinder/device/frame installation drawing is included.

The IPN contains two real presentation tweaks and one associative snapshot. Eight supplemental vector axis trails identify individual screw-to-hole alignment on AS01. The IAM/IPN and source IPT files are included; retain the directory structure when extracting the package. The source part STEP files are also included.

Material: oxygen-free copper. Surface treatment: none.

Device lip reliefs: two 72 mm long grooves beside the boss, 0.5 mm deep with R0.5 end corners. The measured device lip is 3.0398406169 mm thick; groove width is 3.3398406169 mm (lip + 0.3 mm). The groove allowance extends outward to retain the original boss contact faces, device placement and thread axes. CP01 locates the grooves; CP02 section B-B dimensions width and depth.

Internal threaded holes retain native Inventor ISO Metric profile M3x0.5, class 6H, right-hand: ten in the central boss and four in each support. The eight assembly screws are unmodified Inventor 2027 Content Center DIN 7991 M3x10 members, with native M3x0.5-6g external thread features and hexagonal drives. Their 6 mm heads include a 0.2 mm rim; the 6.6 mm x 90-degree countersinks seat the head fronts 0.1 mm below the deck. Nominal engagement is 6.1 mm, with 0.4 mm remaining bore depth. Content Center cosmetic thread cylinders overlap the pilot-bore representation only within the intended threaded engagement; head and clearance-region interference is checked separately.

Validation: all six DWGs reopened in Inventor; five A3 sheets, 46 attached model dimensions without value overrides, linked IPN assembly view, unchanged source CAD hashes during drawing generation, and rendered-page layout inspection. Independent STEP validation checks groove volume, floor height, width, corner radii, retained boss/threads, device alignment and rod contact area.
'''
(OUT / 'README.md').write_text(readme,encoding='utf-8')
files = [OUT / f'QSTL_Split_Mount_RevB_QSTL-{code}.dwg' for code in ['CP01','CP02','LS01','RS01','AS01']]
files += [OUT / name for name in ['QSTL_Split_Mount_RevB_Inventor.dwg', 'QSTL_Split_Mount_RevB.idw',
          'QSTL_Split_Mount_RevB.pdf', 'Split_Mount_Assembly.ipn', 'Split_Mount_Plate_Only.iam',
          'Split_Mount_Presentation_Source.iam', 'Eight_M3_Fasteners.iam']]
files += [MODEL / (part + '.ipt') for part in ['Centre_Plate','Left_Rod_Support','Right_Rod_Support']]
files += [MODEL / 'Standard_Fasteners/DIN_7991_M3x10.ipt', MODEL / 'content_center_fasteners.json']
files += [MODEL / (part + '.step') for part in ['Centre_Plate','Left_Rod_Support','Right_Rod_Support']]
files += [MODEL / 'device_relief_grooves.json']
archive = MODEL / 'QSTL_Plate_DWG_Package_RevB.zip'
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
