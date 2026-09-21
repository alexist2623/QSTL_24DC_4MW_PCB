"""Adapt the local read-only rendering helpers to the verified six-channel board."""
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parent/'_support';T=W/'dc_direct_20260920'
code=(T/'render_layers.py').read_text()
for old,new in [('RF 4개','RF 6개'),('range(1,5)','range(1,7)'),('부품·패드 위치 유지','SMP·QD·기구 홀 유지'),
                ('중앙 12개 + ZIF23 층 전환','중앙 12개 / 층 전환 없음'),('중앙 12개 / 선폭 0.125 mm','중앙 12개 / 층 전환 없음')]:code=code.replace(old,new)
(H/'render_layers.py').write_text(code)
code=(T/'render_dc_only.py').read_text().replace('W=H.parent','W=H.parent/\'_support\'').replace('len(vias)==49','len(vias)==48')
code=code.replace("['R1','R2','R3','R4']","['R1','R2','R3','R4','R5','R6']")
start=code.index("   label(5.85,48.75,");end=code.index("  else:",start)
code=code[:start]+'''   for name,x,y in [('R4',6.7,47.2),('R3',13.0,47.2),('R2',17.0,42.9),('R6',2.7,42.3),('R1',15.8,31.3),('R5',4.7,31.3)]:
    p=next(p for p in n['pads'] if p['component']==name and p['number']=='2')
    label(x,y,name+' · '+p['net'],color(p['net']),16)
'''+code[end:]
code=code.replace('중앙으로 모은 DC 배선','층 전환 비아 없이 중앙으로 모은 DC')
(H/'render_dc_only.py').write_text(code)
code=(T/'render_schematic.py').read_text().replace('W=H.parent','W=H.parent/\'_support\'')
code=code.replace('22 components / 141 symbol pins / 33 named nets / 41 intentional NC','22 components / 141 symbol pins / 37 named nets / 31 intentional NC')
(H/'render_schematic.py').write_text(code)
code=(T/'render_overviews.py').read_text().replace('W=H.parent;','W=H.parent/\'_support\';')
code=code.replace("M=types.ModuleType('native_view');",'''code=code.replace('RF4 / DC20','RF6 / DC18').replace("['MW1','MW2','MW3','MW4']","['MW1','MW2','MW3','MW4','MW5','MW6']")
code=code.replace("   text_at(xy(9.75,5)","   text_at(xy(9.75,20.7),'RF5 -> 12   RF6 -> 18',fill='#ff9ada',f=small)\\n   text_at(xy(9.75,5)")
M=types.ModuleType('native_view');''')
code=code.replace('24 centred QD vias + 16 centred R/C vias.','24 centred QD vias + 24 centred R/C vias.')
code=code.replace(";d.polygon([xy(*v) for v in M.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=color)",
'''\n if p['shape']==1 and abs(p['size_x']-p['size_y'])<.00001:
  x,y=xy(p['x'],p['y']);r=p['size_x']*scale/2;d.ellipse((x-r,y-r,x+r,y+r),fill=color)
 else:d.polygon([xy(*v) for v in M.corners(p['x'],p['y'],p['size_x'],p['size_y'],p['rotation'])],fill=color)''')
code=code.replace("'R2':(16.,44.75),'R3':(13.65,48.8),'R4':(5.85,48.8),'R6':(3.5,44.75),'C2':(17.55,41.25),'C3':(15.2,45.45),'C4':(4.3,45.45),'C6':(1.95,41.25)",
                  "'R2':(17.3,42.5),'R3':(12.6,47.2),'R4':(6.8,47.2),'R6':(2.3,41.7),'C2':(17,39.5),'C3':(12.1,48.5),'C4':(7.35,48.5),'C6':(2.5,39.2)")
(H/'render_overviews.py').write_text(code)
print('Four read-only renderers prepared in',H)
