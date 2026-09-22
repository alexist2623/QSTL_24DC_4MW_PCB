"""Make validation consume actual saved placements rather than superseded formulas."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
(HERE/'verify_hanging_adapter.py').write_text('''"""Validate the current inward-facing mounting arrangement."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name('verify_inward_mounting.py')),run_name='__main__')
''')
p=HERE/'verify_probe_tube.py';s=p.read_text();start=s.index("frame=read(MECH/'Probe_H_Frame'");end=s.index('intersections=[]',start)
s=s[:start]+'''records=json.loads((HOLDER/'inward_placements.json').read_text(encoding='utf-8-sig'))
def actual_shape(record):
    source=read(Path(record['path']).with_suffix('.step'))
    m=record['matrix_cm'];t=gp_Trsf()
    t.SetValues(*[m[i][j]*(10 if j==3 else 1) for i in range(3) for j in range(4)])
    return BRepBuilderAPI_Transform(source,t,True).Shape()
parts=[(r['name'],actual_shape(r)) for r in records if r['name']!='Probe_Tube_ID51_OD54']
''' +s[end:]
p.write_text(s)
print('Updated verifier entry points to use reopened final assembly placements.')
