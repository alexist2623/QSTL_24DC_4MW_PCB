from pathlib import Path
import re,html
H=Path(__file__).resolve().parent;P=H.parents[1]/'QSTL_24DC_4MW_PCB'
s=(P/'docs/Shield_spacing_DRC.html').read_text(encoding='cp949',errors='replace')
rows=re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>',s,re.S)
print('SUMMARY',rows)
for line in s.splitlines():
    if 'Between' in line:print(html.unescape(re.sub('<[^>]+>','',line)))
