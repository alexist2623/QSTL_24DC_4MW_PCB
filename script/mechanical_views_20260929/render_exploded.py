"""Render the current Rev E native drawing's exploded view without altering it."""
from pathlib import Path
import hashlib
import json
import pymupdf

root = Path(__file__).resolve().parents[2]
model = root / 'QSTL_24DC_4MW_PCB/Mechanical_Assembly/Rod_Holder_Adapter_Drop8p5'
source = model / 'Manufacturing_DWG/QSTL_Split_Mount_RevE.pdf'
out = model / 'Views_20260929'
out.mkdir(exist_ok=True)
expected = 'cb5bf20840ff40a1790e7fb7420de3ae12d59d447f79d3e4a8db502196c38f43'
digest = hashlib.sha256(source.read_bytes()).hexdigest()
assert digest == expected, 'Recheck the latest drawing revision before rendering.'
doc = pymupdf.open(source)
page = doc[4]
# Clip in sheet millimetres, preserving part callouts and all eight screw trails.
clip_mm = (17, 33, 183, 238)
clip = pymupdf.Rect(*(v * 72 / 25.4 for v in clip_mm))
pix = page.get_pixmap(matrix=pymupdf.Matrix(3, 3), clip=clip, alpha=False)
destination = out / '02_Plate_exploded_RevE.png'
pix.save(destination)
(out / 'drawing_render_audit.json').write_text(json.dumps({
    'source': str(source), 'sha256': digest, 'revision': 'E',
    'sheet': 'QSTL-AS01', 'page': 5, 'clip_mm': clip_mm,
    'output': str(destination), 'width': pix.width, 'height': pix.height,
}, indent=2), encoding='utf-8')
print(destination)
