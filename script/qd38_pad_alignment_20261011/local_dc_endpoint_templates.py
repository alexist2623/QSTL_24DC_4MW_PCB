"""Offline octilinear templates for small DC endpoint repairs.

This module does not edit a candidate or a native file. It exposes short
H/V/45-degree paths from a moved QD via to an unchanged trunk anchor. Callers
must test complete copper against all layer-specific obstacles and jointly
choose non-conflicting paths before accepting a repair.
"""
from __future__ import annotations

import math
from typing import Iterable

Point = tuple[float, float]
DIRECTIONS = tuple((math.cos(i*math.pi/4), math.sin(i*math.pi/4)) for i in range(8))


def determinant(a: Point, b: Point) -> float:
    return a[0]*b[1]-a[1]*b[0]


def unit(a: Point, b: Point) -> Point:
    dx, dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        raise ValueError('Coincident direction points')
    return dx/length, dy/length


def turn(a: Point, b: Point) -> float:
    return math.degrees(math.acos(max(-1., min(1., a[0]*b[0]+a[1]*b[1]))))


def clean(points: Iterable[Point]) -> list[Point]:
    result: list[Point] = []
    for point in points:
        p = (float(point[0]), float(point[1]))
        if result and math.dist(result[-1], p) < 1e-9:
            continue
        while len(result) >= 2:
            u, v = unit(result[-2], result[-1]), unit(result[-1], p)
            if abs(determinant(u, v)) < 1e-9 and u[0]*v[0]+u[1]*v[1] > 0:
                result.pop()
            else:
                break
        result.append(p)
    return result


def legal_shape(points: list[Point], outgoing: Point | None = None) -> bool:
    vectors = [unit(a, b) for a, b in zip(points, points[1:])]
    for v in vectors:
        if min(abs(v[0]), abs(v[1]), abs(abs(v[0])-abs(v[1]))) > 1e-8:
            return False
    if outgoing is not None:
        vectors.append(outgoing)
    return all(turn(a, b) <= 45.000001 for a, b in zip(vectors, vectors[1:]))


def cut_prefix(points: Iterable[Point], length_mm: float) -> tuple[list[Point], list[Point]]:
    """Split a route at an exact unchanged anchor, retaining the suffix."""
    original = [tuple(p) for p in points]
    if length_mm <= 0:
        raise ValueError('A positive local prefix length is required')
    prefix = [original[0]]
    remaining = length_mm
    for i, (a, b) in enumerate(zip(original, original[1:])):
        length = math.dist(a, b)
        if remaining < length-1e-8:
            t = remaining/length
            anchor = (a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1]))
            return clean(prefix+[anchor]), [anchor]+original[i+1:]
        prefix.append(b)
        remaining -= length
        if abs(remaining) < 1e-8 and i+2 < len(original):
            return clean(prefix), original[i+1:]
    raise ValueError('Local prefix would consume the complete DC route')


def two_directions(displacement: Point, u: Point, v: Point) -> tuple[float, float] | None:
    det = determinant(u, v)
    if abs(det) < 1e-9:
        return None
    a, b = determinant(displacement, v)/det, determinant(u, displacement)/det
    return (a, b) if min(a, b) >= -1e-9 else None


def endpoint_templates(start: Point, anchor: Point, outgoing: Point | None,
                       max_local_length_mm: float = 5.0,
                       middle_steps_mm: Iterable[float] | None = None) -> list[list[Point]]:
    """Enumerate only true <=45-degree turns; no obstacle claim is made.

    The three-segment family varies one segment length over a local sampling
    set. It is intentionally not a global router or an impossibility proof.
    The caller can add obstacle-derived breakpoints to middle_steps_mm.
    """
    start, anchor = tuple(start), tuple(anchor)
    displacement = (anchor[0]-start[0], anchor[1]-start[1])
    options: dict[tuple, list[Point]] = {}

    def add(points):
        pp = clean(points)
        if len(pp) < 2 or not legal_shape(pp, outgoing):
            return
        length = sum(math.dist(a, b) for a, b in zip(pp, pp[1:]))
        if length > max_local_length_mm+1e-9:
            return
        key = tuple((round(x, 9), round(y, 9)) for x, y in pp)
        options[key] = pp

    add([start, anchor])
    if middle_steps_mm is None:
        middle_steps_mm = [i*.025 for i in range(1, 101)]
    for i, u in enumerate(DIRECTIONS):
        for j in ((i-1) % 8, (i+1) % 8):
            v = DIRECTIONS[j]
            lengths = two_directions(displacement, u, v)
            if lengths:
                a, _ = lengths
                add([start, (start[0]+a*u[0], start[1]+a*u[1]), anchor])
            for k in ((j-1) % 8, (j+1) % 8):
                w = DIRECTIONS[k]
                for middle in middle_steps_mm:
                    residual = (displacement[0]-middle*v[0], displacement[1]-middle*v[1])
                    lengths = two_directions(residual, u, w)
                    if lengths is None:
                        continue
                    a, _ = lengths
                    p = (start[0]+a*u[0], start[1]+a*u[1])
                    q = (p[0]+middle*v[0], p[1]+middle*v[1])
                    add([start, p, q, anchor])
    return sorted(options.values(), key=lambda pp: (len(pp), sum(math.dist(a, b) for a, b in zip(pp, pp[1:]))))


def smoke_check() -> dict:
    checks = []
    for start, anchor, outgoing in [
        ((.12, .15), (0., -2.), (0., -1.)),
        ((.25, .15), (1., -1.), (1., 0.)),
        ((0., 0.), (1., 1.), (0., 1.)),
        ((0., 0.), (-1., -1.), (-1., 0.)),
    ]:
        choices = endpoint_templates(start, anchor, outgoing)
        assert choices and all(legal_shape(p, outgoing) for p in choices)
        assert all(math.dist(p[0], start) < 1e-12 and math.dist(p[-1], anchor) < 1e-12 for p in choices)
        checks.append(dict(start=start, anchor=anchor, choices=len(choices), best=choices[0]))
    prefix, suffix = cut_prefix([(0., 0.), (1., 1.), (1., 5.)], 2.)
    assert math.dist(prefix[-1], suffix[0]) < 1e-12
    assert abs(sum(math.dist(a, b) for a, b in zip(prefix, prefix[1:]))-2.) < 1e-12
    assert legal_shape(clean(prefix+suffix[1:]))
    return dict(passed=True, scope='Template geometry only; no obstacle or design mutation', checks=checks)


if __name__ == '__main__':
    import json
    print(json.dumps(smoke_check(), indent=2))
