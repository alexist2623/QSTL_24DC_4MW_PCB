"""Audit the actual saved candidate, without substituting hypothetical via spans.

This guard covers all six copper layers, same-net connectivity, shield spans,
and cross-net clearances including prepared ground copper. It is independent
of the native generator, does not edit any plan, and is not Altium DRC.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from shapely.geometry import Point, LineString, shape
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

from route_circuit import pgeom


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / 'QSTL_QD4_2SET_38PAD' / 'full_copper_candidate.json'
LAYERS = (1, 2, 3, 4, 5, 32)
CLEARANCE = .15


def pieces(geometry):
    return list(geometry.geoms) if hasattr(geometry, 'geoms') else [geometry]


def span(via):
    return [layer for layer in LAYERS if via['low'] <= layer <= via['high']]


def main():
    before = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    plan = json.loads(SOURCE.read_text())
    objects = []

    def add(net, layers, geometry, label, kind):
        objects.append(dict(net=net, layers=layers, geometry=geometry, label=label, kind=kind))

    for pad in plan['physical_pads']:
        layers = list(LAYERS) if pad['layer'] == 74 else [pad['layer']]
        add(pad['net'], layers, pgeom(pad), f"{pad['ref']}-{pad['pin']}", 'pad')
    for via in plan['vias']:
        add(via['net'], span(via), Point(via['x'], via['y']).buffer(via['diameter']/2, quad_segs=64),
            via['label'] + '-via', 'signal-via')
    for i, via in enumerate(plan['shield_vias']):
        add(via['net'], span(via), Point(via['x'], via['y']).buffer(via['diameter']/2, quad_segs=64),
            f"shield-{i}-{via['label']}", 'shield-via')
    tracks = defaultdict(list)
    for track in plan['tracks']:
        tracks[track['layer'], track['net']].append(
            LineString([track['a'], track['b']]).buffer(track['width']/2, quad_segs=32))
    for (layer, net), shapes in tracks.items():
        for index, geom in enumerate(pieces(unary_union(shapes))):
            add(net, [layer], geom, f'{net}-L{layer}-track-{index}', 'track-net-piece')
    for layer, value in plan['ground_regions'].items():
        for index, geom in enumerate(pieces(shape(value))):
            add('GND', [int(layer)], geom, f'GND-L{layer}-region-{index}', 'ground-region')

    parent = list(range(len(objects)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[root(i)] = root(j)

    violations = []
    minima = {}
    for layer in LAYERS:
        ids = [i for i, o in enumerate(objects) if layer in o['layers']]
        geometries = [objects[i]['geometry'] for i in ids]
        tree = STRtree(geometries)
        minimum = float('inf')
        for local_i, global_i in enumerate(ids):
            a = objects[global_i]
            for raw_j in tree.query(a['geometry'].buffer(CLEARANCE + .001)):
                local_j = int(raw_j)
                if local_j >= local_i:
                    continue
                global_j = ids[local_j]
                b = objects[global_j]
                distance = a['geometry'].distance(b['geometry'])
                if a['net'] is not None and a['net'] == b['net']:
                    if distance <= 1e-8:
                        union(global_i, global_j)
                    continue
                minimum = min(minimum, distance)
                if distance >= CLEARANCE - 1e-7:
                    continue
                p, q = nearest_points(a['geometry'], b['geometry'])
                overlap = a['geometry'].intersection(b['geometry']).area
                violations.append(dict(layer=layer, a=a['label'], b=b['label'],
                                       kinds=[a['kind'], b['kind']], nets=[a['net'], b['net']],
                                       gap_mm=distance, overlap_area_mm2=overlap,
                                       nearest_location_mm=[(p.x+q.x)/2, (p.y+q.y)/2]))
        # This is only a local-query minimum. No result means all gaps exceed
        # the query envelope, not that global clearance was measured exactly.
        minima[str(layer)] = minimum if minimum != float('inf') else None

    connectivity = {}
    for net, expected_pads in plan['nets'].items():
        ids = [i for i, obj in enumerate(objects) if obj['net'] == net]
        components = defaultdict(list)
        for i in ids:
            components[root(i)].append(objects[i]['label'])
        labels = {objects[i]['label'] for i in ids}
        missing = [label for label in expected_pads if label not in labels]
        connectivity[net] = dict(connected=len(components) == 1 and not missing,
                                 copper_components=len(components), missing_pads=missing)
        if len(components) != 1:
            connectivity[net]['components'] = list(components.values())

    signal_spans_valid = all(v['low'] == 1 and v['high'] == 32 for v in plan['vias'])
    shield_spans_valid = all(v['low'] == 5 and v['high'] == 32 for v in plan['shield_vias'])
    source_unchanged = before == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    all_connected = all(result['connected'] for result in connectivity.values())
    result = dict(
        status='ACTUAL_CANDIDATE_ALL_SIX_COPPER_LAYERS_OFFLINE_GUARD',
        candidate_sha256=before, candidate_path=str(SOURCE),
        passed=signal_spans_valid and shield_spans_valid and source_unchanged and all_connected and not violations,
        signal_vias=len(plan['vias']), signal_via_spans_are_through=signal_spans_valid,
        actual_signal_spans=dict(Counter(f"{v['low']}-{v['high']}" for v in plan['vias'])),
        shield_vias=len(plan['shield_vias']), shield_spans_are_l5_bottom=shield_spans_valid,
        layers=list(LAYERS), clearance_limit_mm=CLEARANCE,
        clearance_violations=violations, clearance_violation_count=len(violations),
        violations_per_layer=dict(Counter(v['layer'] for v in violations)),
        local_query_minimum_mm=minima,
        all_nets_connected_including_gnd=all_connected, connectivity=connectivity,
        source_unchanged=source_unchanged,
        scope='Actual plan copper only. No hypothetical span substitution. Includes pads, signal vias, shields, traces, prepared GND and physical same-net connectivity. Native DRC, masks, paste, manufacturing stack and drilling checks remain separate.',
    )
    (HERE / 'through_via_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ('clearance_violations', 'connectivity')}, indent=2))
    print('DISCONNECTED', [(k, v['copper_components']) for k, v in connectivity.items() if not v['connected']])


if __name__ == '__main__':
    main()
