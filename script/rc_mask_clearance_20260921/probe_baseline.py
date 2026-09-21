from pathlib import Path
import json
H=Path(__file__).parent
n=json.loads((H.parent/'shield_rc_ring_20260921/before_native.json').read_text())
for c in n['components']:
 if c['designator'].startswith(('R','C')):print(c)
for t in n['tracks']:
 if t['net'] in ['MW1','MW5','S1','S5','ZIF21','ZIF02','ZIF23','ZIF26']:print('TRACK',t)
for a in n['arcs']:
 if a['net'] in ['MW1','MW5','S1','S5']:print('ARC',a)
