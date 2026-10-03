from pathlib import Path
import urllib.request
import fitz

ROOT = Path(__file__).resolve().parent
REF = ROOT / 'reference'
REF.mkdir(exist_ok=True)
SOURCES = {
    '150150001_PSD000_RevB': 'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/150/15015/150150445_sd.pdf',
    'PS_15015_001_RevC': 'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/productspecificationpdf/000/000000/PS-15015-001-001.pdf',
    'SD_502598_003': 'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/502/502598/5025983993_sd.pdf',
}
for name, url in SOURCES.items():
    pdf = REF / (name + '.pdf')
    if not pdf.exists():
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        pdf.write_bytes(urllib.request.urlopen(req, timeout=45).read())
    doc = fitz.open(pdf)
    (REF / (name + '.txt')).write_text('\n'.join(p.get_text() for p in doc), encoding='utf-8')
    for i, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(3, 3)).save(REF / f'{name}_{i+1}.png')
    print(name, len(doc), 'pages')
