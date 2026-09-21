"""Record the user's corrected cavity size and inspect the pad fanout."""
from pathlib import Path
import json, math
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'QSTL_24DC_4MW_PCB'
f=R/'AGENTS.md';s=f.read_text(encoding='utf-8')
s=s.replace('Keep the 4.3 x 4.3 mm square defined by QD inner pad ends free of GND copper on every layer except Top. Preserve Top GND inside this boundary. The latest request adds a 3.9 x 3.9 mm non-through pocket, depth 1.2 mm from the QD/Bottom face, inset 0.2 mm from each inner pad-end boundary.', 'Keep the central QD cavity 4.3 x 4.3 mm, centred at (9.75,42.5) mm. Move the QD pads outward by 0.2 mm, preserving pad dimensions, to make a 4.7 x 4.7 mm inner pad-end square and 0.2 mm cavity-to-pad clearance. Keep the 4.7 mm inner square free of GND copper on every layer except Top. Preserve Top GND inside this boundary. The non-through pocket is 1.2 mm deep from the QD/Bottom face.')
f.write_text(s,encoding='utf-8')
f=P/'docs/DESIGN_REQUIREMENTS.md';s=f.read_text(encoding='utf-8')
s=s.replace('The square defined by inward-facing pad ends is 4.3 x 4.3 mm. QD pads are 1.0 x 0.5 mm at 0.7 mm pitch.', 'The central QD cavity remains 4.3 x 4.3 mm. The latest user correction requires moving the QD pads outward by 0.2 mm, making the square defined by inward-facing pad ends 4.7 x 4.7 mm. Preserve the 1.0 x 0.5 mm pad sizes and 0.7 mm pitch along each row; cavity-to-pad clearance is 0.2 mm.')
s=s.replace('The boundary is x=7.6-11.9 mm and y=40.35-44.65 mm, centred at (9.75,42.5) mm.', 'The updated inner pad-end boundary is x=7.4-12.1 mm and y=40.15-44.85 mm, centred at (9.75,42.5) mm.')
s=s.replace('with a 3.9 x 3.9 mm outer envelope and 1.2 mm depth.', 'with a 4.3 x 4.3 mm outer envelope and 1.2 mm depth.')
s=s.replace('Do not create a through-board cutout or move the QD pads.', 'Do not create a through-board cutout. Move the QD pads outward as specified above and reconnect their existing via-in-pad fanouts.')
s=s.replace('The pocket envelope is x=7.8-11.7 mm, y=40.55-44.45 mm, inset 0.2 mm from each 4.3 mm pad-end boundary. The user initially chose 4.1 mm but then explicitly changed the inset to 0.2 mm.', 'The pocket envelope is x=7.6-11.9 mm, y=40.35-44.65 mm, inset 0.2 mm from each 4.7 mm pad-end boundary. The latest user correction preserves the 4.3 mm QD cavity and moves the pads, superseding the earlier proposal to shrink the cavity to 3.9 mm.')
f.write_text(s,encoding='utf-8')
n=json.loads((H/'before_native.json').read_text())
for p in n['pads']:
    if p['component']!='Q1':continue
    print('PAD',p['number'],p['net'],p['x'],p['y'],p['rotation'])
    for t in n['tracks']:
        if min(math.dist((p['x'],p['y']),(t['x1'],t['y1'])),math.dist((p['x'],p['y']),(t['x2'],t['y2'])))<.001:print('  TRACK',t)
    for a in n['arcs']:
        pts=[(a['cx']+a['radius']*math.cos(math.radians(v)),a['cy']+a['radius']*math.sin(math.radians(v))) for v in (a['start_angle'],a['end_angle'])]
        if min(math.dist((p['x'],p['y']),q) for q in pts)<.001:print('  ARC',a)
