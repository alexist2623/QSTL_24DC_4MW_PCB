"""Update generated reports and validation expectations for the 80 mm plate."""
from pathlib import Path

HERE = Path(__file__).resolve().parent

def replace_all(filename, replacements):
    path = HERE / filename
    source = path.read_text(encoding="utf-8-sig")
    for old, new in replacements:
        assert old in source, (filename, old)
        source = source.replace(old, new)
    path.write_text(source, encoding="utf-8-sig" if filename.endswith('.ps1') else "utf-8")

replace_all('build_hanging_adapter.ps1', [
    ('adapter_position_mm=@(0,95,6)', 'adapter_position_mm=@(0,135,6)'),
    ('solid_plate_mm=@(51,150,4)', 'solid_plate_mm=@(51,80,4)'),
    ('contact_length_per_rod_mm=150', 'contact_length_per_rod_mm=80'),
    ('gross_contact_area_mm2=1800', 'gross_contact_area_mm2=960'),
    ('rod_fastener_rows_y_mm=@(100,120,140,160,180,200,220,240)', 'rod_fastener_rows_y_mm=@(140,160,180,200)'),
    ('count=16;count_per_side=8', 'count=10;count_per_side=5'),
    ('@(0..7 | ForEach-Object {112.82802366515844+16*$_})', '@(0..4 | ForEach-Object {144.82802366515844+16*$_})'),
    ('Saved hanging adapter, 18 illustrative screws', 'Saved short hanging adapter, 10 illustrative screws'),
])
replace_all('finalize_hanging_adapter.ps1', [
    ('$expectedOccurrences=21', '$expectedOccurrences=13'),
    ('(Matrix 0 @(0,95,6))', '(Matrix 0 @(0,135,6))'),
    ("if ($threads.Count -ne 16) {throw 'Expected sixteen saved native thread features.'}", "if ($threads.Count -ne 10) {throw 'Expected ten saved native thread features.'}"),
    ("if ($sideRows.Count -ne 8) {throw 'Expected eight threads on each opposite face.'}", "if ($sideRows.Count -ne 5) {throw 'Expected five threads on each opposite face.'}"),
    ('$i -lt 8', '$i -lt 5'),
    ('17.82802366515844+16*$i', '9.82802366515844+16*$i'),
    ('native_thread_count=16;count_per_side=8', 'native_thread_count=10;count_per_side=5'),
])
replace_all('verify_hanging_adapter.py', [
    ('[0,0,0,51,150,10]', '[0,0,0,51,80,10]'),
    ('len(device_holes)==16', 'len(device_holes)==10'),
    ('len(row)==8', 'len(row)==5'),
    ('112.82802366515844+16*i', '144.82802366515844+16*i'),
    ("gp_Pnt(plan['boss_x_min_mm']+6,99,10),1.5,142,6", "gp_Pnt(plan['boss_x_min_mm']+6,139,10),1.5,72,6"),
    ('1.5*142*6', '1.5*72*6'),
    ('len(rod_errors)==16', 'len(rod_errors)==8'),
    ('2*(6*150-8*math.pi*1.7**2-7*math.pi*1.5**2)', '2*(6*80-4*math.pi*1.7**2-4*math.pi*1.5**2)'),
    ('39,150,4', '39,80,4'),
    ('39*150*4', '39*80*4'),
    ('rod_contact_gross_area_mm2=1800', 'rod_contact_gross_area_mm2=960'),
    ('fasteners_illustrative=18', 'fasteners_illustrative=10'),
    ('device_hole_count=16,device_hole_count_per_side=8', 'device_hole_count=10,device_hole_count_per_side=5'),
])
