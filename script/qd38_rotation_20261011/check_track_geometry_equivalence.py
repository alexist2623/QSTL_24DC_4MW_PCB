"""Regression and negative mutation checks against the actual saved snapshot.

Only in-memory track dictionaries are mutated. Native and candidate files are
read-only. The report records the original false-positive symptoms.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from scipy.optimize import linear_sum_assignment
from track_geometry_equivalence import track_values, undirected_distance_matrix, union_metrics, metrics_pass

H = Path(__file__).resolve().parent
paths = [H/'saved_revision_snapshot.json', H/'full_copper_candidate.json']
before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
saved, plan = [json.loads(p.read_text()) for p in paths]
expected = [dict(net=t['net'], layer=t['layer'], x1=t['a'][0], y1=t['a'][1],
                 x2=t['b'][0], y2=t['b'][1], width=t['width']) for t in plan['tracks']]
actual = saved['tracks']
mw_actual = [t for t in actual if t['net']=='MW32']
mw_expected = [t for t in expected if t['net']=='MW32']
mw_metric = union_metrics(mw_actual, mw_expected)
assert metrics_pass(mw_metric)
assert mw_metric['raw_centerline_union_length_difference_mm'] > .0035
assert mw_metric['centerline_union_length_difference_mm'] < 1e-10

dc_actual = [t for t in actual if t['net']=='DC32' and t['layer']==2]
dc_expected = [t for t in expected if t['net']=='DC32' and t['layer']==2]
dist = undirected_distance_matrix([track_values(t) for t in dc_actual],
                                  [track_values(t) for t in dc_expected])
ri, ci = linear_sum_assignment(dist)
assert max(dist[ri, ci]) < 1e-5
reversed_expected = [dict(t, x1=t['x2'], y1=t['y2'], x2=t['x1'], y2=t['y1']) for t in dc_expected]
reverse_dist = undirected_distance_matrix([track_values(t) for t in dc_actual],
                                          [track_values(t) for t in reversed_expected])
assert (dist == reverse_dist).all()

negative_results = {}
shifted = deepcopy(mw_actual)
for track in shifted:
    track['x1'] += .002
    track['x2'] += .002
negative_results['real_2um_translation_rejected'] = not metrics_pass(union_metrics(shifted, mw_expected))
missing = deepcopy(mw_actual)
missing.pop(max(range(len(missing)), key=lambda i: (missing[i]['x2']-missing[i]['x1'])**2 + (missing[i]['y2']-missing[i]['y1'])**2))
negative_results['missing_unique_long_segment_rejected'] = not metrics_pass(union_metrics(missing, mw_expected))
narrowed = deepcopy(mw_actual)
for track in narrowed:
    track['width'] -= .01
negative_results['real_10um_width_reduction_rejected'] = not metrics_pass(union_metrics(narrowed, mw_expected))
assert all(negative_results.values())
assert before == {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
report = dict(passed=True, input_sha256=before,
              actual_native_sha256=saved['source_sha256'],
              DC32_direction_independent_maximum_error_mm=float(max(dist[ri, ci])),
              all_endpoint_reversals_identical=True, MW32_metrics=mw_metric,
              negative_mutation_checks=negative_results, input_files_unchanged=True)
(H/'track_equivalence_regression_report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
