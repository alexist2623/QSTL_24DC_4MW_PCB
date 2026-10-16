"""Extract actual native DRC rows without altering or suppressing rules."""
from pathlib import Path
import json,re,html
H=Path(__file__).resolve().parent
s=(H/'Native_DRC.html').read_text()
rows=[[html.unescape(re.sub('<[^>]+>',' ',c)).strip() for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>',tr,re.S)] for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',s,re.S)]
(H/'drc_rows.json').write_text(json.dumps(rows,indent=2))
for r in rows:
    if r and any('Constraint' in v or 'Violation' in v or 'Un-Routed' in v or 'Short-Circuit' in v for v in r):print(' | '.join(r))
