from pathlib import Path
import json
H=Path(__file__).parent
n=json.loads((H.parent/'remove_resistor_rf_vias_20260921/native_render_snapshot.json').read_text())
for p in n['pads']:
 if p['component'] in ('C1','R1','C5','R5') or p['component']=='Q1' and p['net'].startswith('MW'):print('PAD',p)
for t in n['tracks']:
 if t['net'] in ('MW1','S1','MW5','S5','ZIF21','ZIF02') or t['layer'] in (2,4) and min(t['y1'],t['y2'])<31.3 and max(t['y1'],t['y2'])>30.7:print('TRACK',t)
for a in n['arcs']:
 if a['net'] in ('MW1','S1','MW5','S5'):print('ARC',a)
