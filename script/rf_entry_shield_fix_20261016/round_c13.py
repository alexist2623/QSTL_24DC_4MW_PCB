"""Back up the current revision and replace only C13's approach by a broad arc."""
from pathlib import Path
import json, shutil, hashlib, math
import numpy as np
H = Path(__file__).resolve().parent
ROOT = H.parents[1]
P = ROOT / 'QSTL_QD4_2SET_38PAD'
N = 'QSTL_QD4_2SET_38PAD'
B = H / 'before_c13_rounding'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
expected = '5f673b010fc5cff1463d329b1a8a8a92767402c34f0c853543a2871f313832de'
assert sha(P / (N + '.PcbDoc')) == expected
B.mkdir(exist_ok=True)
for source in [P / (N + '.PcbDoc'), P / (N + '.SchDoc'), P / 'pin_mapping.csv'] + [H / s for s in ('candidate.json', 'entry_routes.json', 'shield_records.json', 'preparation_audit.json', 'saved_native_audit.json', 'support_audit.json')]:
    dest = B / source.name
    if not dest.exists(): shutil.copy2(source, dest)
    assert sha(dest) == sha(source), source
data = json.loads((H / 'entry_routes.json').read_text())
g = next(g for g in data['groups'] if g['row']['smp'] == 'SMP13')
assert np.linalg.norm(np.array(g['smp_to_c1'][0]) - [11.75, 25.2]) < 1e-5
assert np.linalg.norm(np.array(g['smp_to_c1'][-1]) - [16.75, 22.85]) < 1e-5
angle = np.linspace(math.pi, 1.5 * math.pi, 801)
arc = np.c_[13.35 + 1.6 * np.cos(angle), 24.45 + 1.6 * np.sin(angle)]
g['smp_to_c1'] = np.vstack(([11.75, 25.2], arc, [16.75, 22.85])).tolist()
for row in data['entry_report']:
    if row['channel'] == 'SMP13':
        row.update(straight_radial_entry_mm=3.4, radius_mm=1.6, bend_degrees=90, normal_cap_launch_mm=.75)
data['C13_exact_primitives'] = [
    dict(line=True, a=[11.75, 25.2], b=[11.75, 24.45]),
    dict(line=False, cx=13.35, cy=24.45, radius=1.6, start_angle=180., end_angle=270.),
    dict(line=True, a=[13.35, 22.85], b=[16.75, 22.85]),
]
(H / 'entry_routes.json').write_text(json.dumps(data, indent=2))
print('C13: 0.75 mm normal launch, R1.60 quarter-circle, 3.40 mm radial SMP entry; backup', B)
