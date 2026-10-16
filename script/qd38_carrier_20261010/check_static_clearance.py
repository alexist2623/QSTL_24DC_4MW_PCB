"""Audit planned static copper; this does not replace native Altium DRC."""
import json
from shapely.geometry import Point
from route_circuit import pgeom
from design_geometry import DEST


def main():
    plan = json.loads((DEST / 'circuit_plan.json').read_text())
    failures = []
    minimum = {}
    for layer in (1, 2, 4, 32):
        items = [(f"{p['ref']}-{p['pin']}", p['net'], pgeom(p))
                 for p in plan['physical_pads'] if p['layer'] in (layer, 74)]
        items += [(v['label'] + '-via', v['net'],
                   Point(v['x'], v['y']).buffer(v['diameter']/2, quad_segs=32))
                  for v in plan['vias'] if v['low'] <= layer <= v['high']]
        gaps = []
        for i, (name, net, copper) in enumerate(items):
            for other, other_net, other_copper in items[:i]:
                if net is not None and net == other_net:
                    continue
                gap = copper.distance(other_copper)
                gaps.append(gap)
                if gap < .15 - 1e-7:
                    failures.append(dict(layer=layer, a=name, b=other, gap_mm=gap))
        minimum[layer] = min(gaps)
    result = dict(passed=not failures, minimum_mm=minimum, failures=failures)
    (DEST / 'static_clearance_candidate.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
