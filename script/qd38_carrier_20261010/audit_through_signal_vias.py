"""Read-only scenario audit: extend every signal via through all six layers.

The source PCB, candidate plans, and manufacturing files are never written.
Results are stored beside this helper. This is an offline geometric audit,
not a native Altium DRC or an authorization to change the via process.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, LineString, shape
from shapely.ops import nearest_points, unary_union

from route_circuit import pgeom


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'QSTL_QD4_2SET_38PAD' / 'full_copper_candidate.json'
LAYERS = (1, 2, 3, 4, 5, 32)
CLEARANCE = .15


def span(via):
    return {layer for layer in LAYERS if via['low'] <= layer <= via['high']}


def location(a, b):
    p, q = nearest_points(a, b)
    return [round((p.x + q.x) / 2, 7), round((p.y + q.y) / 2, 7)]


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    plan = json.loads(SOURCE.read_text())
    vias = plan['vias']
    copper = [Point(v['x'], v['y']).buffer(v['diameter'] / 2, quad_segs=64) for v in vias]
    pads = [(p, pgeom(p)) for p in plan['physical_pads']]
    tracks = defaultdict(list)
    for t in plan['tracks']:
        tracks[t['layer'], t['net']].append(
            LineString([t['a'], t['b']]).buffer(t['width'] / 2, quad_segs=32))
    traces = {key: unary_union(parts) for key, parts in tracks.items()}
    shields = [(s, Point(s['x'], s['y']).buffer(s['diameter'] / 2, quad_segs=64))
               for s in plan['shield_vias']]
    ground = {int(k): shape(v) for k, v in plan['ground_regions'].items()}
    results = []
    min_by_category = defaultdict(lambda: float('inf'))

    def compare(i, layer, b, category, other, other_net, baseline_exposed):
        v, a = vias[i], copper[i]
        if other_net == v['net']:
            return
        gap = a.distance(b)
        min_by_category[f'L{layer}:{category}'] = min(min_by_category[f'L{layer}:{category}'], gap)
        if gap >= CLEARANCE - 1e-7:
            return
        results.append(dict(layer=layer, category=category, via=v['label'], net=v['net'],
                            via_center=[v['x'], v['y']], original_span=[v['low'], v['high']],
                            other=other, other_net=other_net, clearance_mm=gap,
                            copper_overlap=a.intersection(b).area > 1e-12,
                            overlap_area_mm2=a.intersection(b).area,
                            nearest_location_mm=location(a, b),
                            newly_exposed=not baseline_exposed))

    for i, via in enumerate(vias):
        for layer in LAYERS:
            present = layer in span(via)
            for pad, geom in pads:
                if pad['layer'] in (layer, 74):
                    compare(i, layer, geom, 'via-pad', f"{pad['ref']}-{pad['pin']}", pad['net'], present)
            for j in range(i):
                compare(i, layer, copper[j], 'via-signal-via', vias[j]['label'], vias[j]['net'],
                        present and layer in span(vias[j]))
            for shield, geom in shields:
                if layer in span(shield):
                    compare(i, layer, geom, 'via-shield-via', shield['label'] + f"@{shield['x']:.5f},{shield['y']:.5f}", 'GND', present)
            for (track_layer, net), geom in traces.items():
                if track_layer == layer:
                    compare(i, layer, geom, 'via-track-net', net, net, present)
            if layer in ground:
                compare(i, layer, ground[layer], 'via-ground-region', f'ground-L{layer}', 'GND', present)

    summary = {}
    for layer in LAYERS:
        rows = [r for r in results if r['layer'] == layer]
        summary[f'L{layer}'] = dict(
            violations_by_category=dict(Counter(r['category'] for r in rows)),
            new_violations_by_category=dict(Counter(r['category'] for r in rows if r['newly_exposed'])),
            copper_overlaps_by_category=dict(Counter(r['category'] for r in rows if r['copper_overlap'])),
            affected_signal_vias=len({r['via'] for r in rows}),
        )
    nonground = [r for r in results if r['category'] != 'via-ground-region']
    new_nonground = [r for r in nonground if r['newly_exposed']]
    report = dict(
        status='READ_ONLY_THROUGH_SIGNAL_VIA_SCENARIO_NOT_NATIVE_DRC', source=str(SOURCE),
        source_sha256=before, signal_vias=len(vias), shield_vias_unchanged=len(shields),
        requested_scenario_span=[1, 32], minimum_clearance_mm=CLEARANCE,
        original_signal_spans=dict(Counter(f"{v['low']}-{v['high']}" for v in vias)),
        original_signal_via_sizes=dict(Counter(f"{v['diameter']}/{v['hole']}" for v in vias)),
        unique_violation_count=len(results), non_ground_violation_count=len(nonground),
        new_non_ground_violation_count=len(new_nonground),
        non_ground_affected_vias=sorted({r['via'] for r in nonground}),
        per_layer=summary, minimum_by_layer_category_mm=dict(min_by_category), violations=results,
        counting='Via-track is one event per via/layer/foreign net, rather than per track segment. Via-via pairs are counted once per layer.',
        limitation='Ground copper is the unchanged partial-span candidate. Those ground conflicts require regenerated antipads/pours; this audit does not regenerate them.',
    )
    after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert before == after, 'Read-only source changed during audit'
    report['source_unchanged'] = True
    (HERE / 'through_signal_via_audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ('violations', 'minimum_by_layer_category_mm')}, indent=2))
    print('NON_GROUND_DETAILS')
    for row in nonground:
        print(json.dumps(row))


if __name__ == '__main__':
    main()
