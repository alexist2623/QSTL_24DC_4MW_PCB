"""Read-only edge-to-edge SMD pad spacing check on the audited native snapshot."""
import hashlib
import itertools
import json
from pathlib import Path

from shapely.affinity import rotate, translate
from shapely.geometry import Point, box

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def shape(p):
    if p['shape'] == 1:
        assert abs(p['size_x'] - p['size_y']) < 1e-6
        return Point(p['x'], p['y']).buffer(p['size_x']/2, quad_segs=512)
    assert p['shape'] == 2
    return translate(rotate(box(-p['size_x']/2, -p['size_y']/2,
                                p['size_x']/2, p['size_y']/2),
                            p['rotation'], origin=(0, 0)), p['x'], p['y'])


def main():
    audit = json.loads((HERE/'saved_revision_audit.json').read_text())
    pcb = ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
    digest = hashlib.sha256(pcb.read_bytes()).hexdigest()
    assert audit['passed'] and audit['native_sha256'] == digest
    snap = json.loads((HERE/'saved_revision_snapshot.json').read_text())
    pads = [p for p in snap['pads'] if p['component'] == 'J1'
            or (p['component'] or '').startswith(('R', 'C'))]
    assert len(pads) == 117 and all(p['layer'] in (1, 32) and p['hole'] == 0 for p in pads)
    shapes = [shape(p) for p in pads]
    pairs = []
    for i, j in itertools.combinations(range(len(pads)), 2):
        a, b = pads[i], pads[j]
        if a['layer'] != b['layer']:
            continue
        pairs.append(dict(pads=[a['component']+'-'+a['number'], b['component']+'-'+b['number']],
                          nets=[a['net'], b['net']], layer=a['layer'],
                          same_component=a['component'] == b['component'],
                          same_nonempty_net=bool(a['net']) and a['net'] == b['net'],
                          edge_gap_mm=shapes[i].distance(shapes[j])))
    pairs.sort(key=lambda p: p['edge_gap_mm'])
    unequal = [p for p in pairs if not p['same_nonempty_net']]
    selected = {
        'all_SMD_pad_edges_including_same_net': pairs[0],
        'different_net_SMD': unequal[0],
        'RC_only': min((p for p in unequal if p['layer'] == 32), key=lambda p:p['edge_gap_mm']),
        'ZIF_only': min((p for p in unequal if p['layer'] == 1), key=lambda p:p['edge_gap_mm']),
        'same_resistor_two_pads': min((p for p in pairs if p['same_component'] and p['pads'][0].startswith('R')), key=lambda p:p['edge_gap_mm']),
        'same_capacitor_two_pads': min((p for p in pairs if p['same_component'] and p['pads'][0].startswith('C')), key=lambda p:p['edge_gap_mm']),
    }
    report = dict(passed=all(p['edge_gap_mm'] >= .15 - 1e-5 for p in unequal),
                  native_sha256=digest, required_different_net_gap_mm=.15,
                  pad_count=len(pads), minimums=selected, closest_pairs=unequal[:20],
                  scope='Actual saved R/C and J1 SMD pad copper edges. QD wire-bond pads and through-hole SMP pads are not SMD pads. No CAD modifications.')
    (HERE/'saved_smd_pad_spacing.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('passed','native_sha256','pad_count','minimums')}, indent=2))
    assert report['passed']


if __name__ == '__main__':
    main()
