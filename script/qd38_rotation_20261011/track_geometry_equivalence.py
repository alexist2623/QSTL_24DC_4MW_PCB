"""Compare saved track copper without sensitivity to endpoint order or roundoff.

Length comparisons use the native coordinate grid to collapse numerically
coincident overlaps. Unsnapped centreline and width-specific copper comparisons
remain mandatory, so snapping cannot hide a real geometric change.
"""
import math

import numpy as np
from scipy.spatial.distance import cdist
from shapely.geometry import LineString
from shapely.ops import unary_union

UNIT = 2.54e-6
TOL = 1e-5


def track_values(track):
    points = [(track['x1'], track['y1']), (track['x2'], track['y2'])]
    # Native-grid ordering also produces a stable duplicate-record key. Keep
    # raw values in the returned vector for the actual distance comparison.
    a, b = sorted(points, key=lambda p: tuple(round(v / UNIT) for v in p))
    return [*a, *b, track['width']]


def undirected_distance_matrix(actual, expected):
    """Chebyshev endpoint/width error, allowing either segment orientation."""
    a, e = np.asarray(actual), np.asarray(expected)
    return np.minimum(cdist(a, e, metric='chebyshev'),
                      cdist(a, e[:, [2, 3, 0, 1, 4]], metric='chebyshev'))


def line_union(records, quantized=False):
    def point(x, y):
        if quantized:
            return (round(x / UNIT) * UNIT, round(y / UNIT) * UNIT)
        return (x, y)
    return unary_union([LineString([point(t['x1'], t['y1']),
                                    point(t['x2'], t['y2'])]) for t in records])


def union_metrics(actual, expected):
    ac, ec = line_union(actual), line_union(expected)
    aq, eq = line_union(actual, True), line_union(expected, True)
    def copper(records):
        return unary_union([LineString([(t['x1'], t['y1']), (t['x2'], t['y2'])])
                            .buffer(t['width'] / 2, quad_segs=64) for t in records])
    ag, eg = copper(actual), copper(expected)
    snap = max(math.hypot(x - round(x / UNIT) * UNIT,
                          y - round(y / UNIT) * UNIT)
               for t in actual + expected
               for x, y in [(t['x1'], t['y1']), (t['x2'], t['y2'])])
    return dict(
        actual_count=len(actual), expected_count=len(expected),
        centerline_hausdorff_mm=ac.hausdorff_distance(ec),
        raw_centerline_union_length_difference_mm=abs(ac.length - ec.length),
        centerline_union_length_difference_mm=abs(aq.length - eq.length),
        native_grid_centerline_hausdorff_mm=aq.hausdorff_distance(eq),
        native_grid_unit_mm=UNIT, maximum_grid_snap_distance_mm=snap,
        actual_widths=sorted({t['width'] for t in actual}),
        expected_widths=sorted({t['width'] for t in expected}),
        extra_copper_outside_tolerance_mm2=ag.difference(eg.buffer(TOL)).area,
        missing_copper_outside_tolerance_mm2=eg.difference(ag.buffer(TOL)).area,
        extra_centerline_outside_tolerance_mm=ac.difference(ec.buffer(TOL)).length,
        missing_centerline_outside_tolerance_mm=ec.difference(ac.buffer(TOL)).length)


def metrics_pass(metric):
    return (metric['centerline_hausdorff_mm'] <= TOL
            and metric['native_grid_centerline_hausdorff_mm'] <= TOL
            and metric['centerline_union_length_difference_mm'] <=
                TOL * (metric['actual_count'] + metric['expected_count'])
            and metric['maximum_grid_snap_distance_mm'] <= math.sqrt(2) * UNIT / 2 + 1e-12
            and max(metric['extra_copper_outside_tolerance_mm2'],
                    metric['missing_copper_outside_tolerance_mm2']) <= 1e-12
            and max(metric['extra_centerline_outside_tolerance_mm'],
                    metric['missing_centerline_outside_tolerance_mm']) <= 1e-10
            and max(abs(x-y) for x in metric['actual_widths']
                    for y in metric['expected_widths']) <= TOL)
