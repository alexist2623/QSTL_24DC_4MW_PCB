from pathlib import Path
import re,html
P=Path(r'C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB\QSTL_24DC_4MW_PCB')
s=(P/'docs/RF6_DRC.html').read_text(encoding='cp949',errors='replace')
for m in re.findall(r'<acronym[^>]*>(.*?)</acronym>',s,re.S):
 if any(k in m for k in ['Mask Sliver','Silk To','Net Antennae']):print(html.unescape(re.sub('<[^>]+>','',m)))
