"""Download and render the manufacturer's shared 502598 drawing, read-only."""
from pathlib import Path
import urllib.request
import fitz
H=Path(__file__).resolve().parent
url='https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf'
p=H/'Molex_SD-502598-003.pdf'
if not p.exists():
 with urllib.request.urlopen(url,timeout=30) as r:p.write_bytes(r.read())
doc=fitz.open(p)
for i in (0,1):
 doc[i].get_pixmap(matrix=fitz.Matrix(2,2)).save(H/f'Molex_page_{i+1}.png')
print('Rendered connector section and recommended FPC dimensions.')
