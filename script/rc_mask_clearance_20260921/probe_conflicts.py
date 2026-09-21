from pathlib import Path
import json
n=json.loads((Path(__file__).parent/'planned_native.json').read_text())
print('VIA',n['vias'][4])
for i in (56,131,249):print(i,n['tracks'][i])
