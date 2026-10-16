"""Read-only RF equivalence across native line/arc normalization.

No record-count or angular-unit relaxation is used.  Compare unsnapped full
curves and their copper, outside copper common to both matching contact pads.
Every native arc must retain an expected circle family and sweep coverage.
Very short tangent overlap records are reported with their spatial error.
"""
from collections import defaultdict
from pathlib import Path
import argparse
import hashlib
import json
import math

from shapely import hausdorff_distance
from shapely.geometry import LineString, Point, GeometryCollection
from shapely.ops import unary_union

from audit_saved_rf_geometry import pad_geometry
from route_rf_corridor_bounded import pgeom

TOL = 1e-5
ARC_SAGITTA = 2e-8
BUFFER_QUADS = 1024


def is_rf(net):
    return (net or "").startswith(("S", "MW"))


def endpoint(arc, angle):
    rad = math.radians(angle)
    return (arc["cx"] + arc["radius"] * math.cos(rad),
            arc["cy"] + arc["radius"] * math.sin(rad))


def arc_line(arc):
    radius = arc["radius"]
    span = (arc["end_angle"] - arc["start_angle"]) % 360
    if not radius > 0 or not span > 0:
        raise ValueError("Nonpositive RF arc radius or sweep")
    step = 2 * math.acos(max(-1.0, 1 - ARC_SAGITTA / radius))
    count = max(2, math.ceil(math.radians(span) / step))
    points = [endpoint(arc, arc["start_angle"] + span * i / count)
              for i in range(count + 1)]
    return LineString(points)


def primitive_line(item, kind):
    if kind == "arc":
        return arc_line(item)
    if "a" in item:
        return LineString([item["a"], item["b"]])
    return LineString([(item["x1"], item["y1"]),
                       (item["x2"], item["y2"])])


def records(data):
    grouped = defaultdict(list)
    for key, kind in (("tracks", "line"), ("arcs", "arc")):
        for index, item in enumerate(data.get(key, [])):
            if not is_rf(item["net"]):
                continue
            # Matching width buckets do not replace the raw-width comparison.
            group = (item["net"], item["layer"], round(item["width"], 5))
            grouped[group].append((kind, index, item, primitive_line(item, kind)))
    return grouped


def sampled_directed_distance(source, target):
    """Discrete Hausdorff diagnostic; strict coverage is separately required."""
    if source.is_empty:
        return 0.0
    # Shapely's symmetric result is not usable after pad clipping; comparing
    # each source point with the target establishes the directed diagnostic.
    maximum = 0.0
    pending = [source]
    while pending:
        geom = pending.pop()
        if hasattr(geom, "geoms"):
            pending.extend(geom.geoms)
        elif hasattr(geom, "coords"):
            points = list(geom.coords)
            for i, xy in enumerate(points):
                maximum = max(maximum, Point(xy).distance(target))
                if i:
                    before = points[i - 1]
                    for f in (.25, .5, .75):
                        q = (before[0] + f * (xy[0] - before[0]),
                             before[1] + f * (xy[1] - before[1]))
                        maximum = max(maximum, Point(q).distance(target))
    return maximum


def angle_intervals(arcs, radius):
    parts = []
    circumference = 2 * math.pi * radius
    for arc in arcs:
        start = math.radians(arc["start_angle"] % 360) * radius
        span = math.radians((arc["end_angle"] - arc["start_angle"]) % 360) * radius
        finish = start + span
        if finish <= circumference:
            parts.append(LineString([(start, 0), (finish, 0)]))
        else:
            parts.append(LineString([(start, 0), (circumference, 0)]))
            parts.append(LineString([(0, 0), (finish - circumference, 0)]))
    return unary_union(parts)


def periodic_copies(geometry, circumference):
    from shapely.affinity import translate
    return unary_union([translate(geometry, xoff=shift)
                        for shift in (-circumference, 0, circumference)])


def arc_families(actual, expected, tolerance):
    """Match physical circles, then compare combined angular sweeps in mm."""
    families = []
    errors = []
    for arc in expected:
        family = next((f for f in families
                       if max(abs(arc[k] - f["reference"][k])
                              for k in ("cx", "cy", "radius", "width")) <= tolerance), None)
        if family is None:
            family = {"reference": arc, "expected": [], "actual": []}
            families.append(family)
        family["expected"].append(arc)
    for arc in actual:
        options = [(max(abs(arc[k] - f["reference"][k])
                        for k in ("cx", "cy", "radius", "width")), i)
                   for i, f in enumerate(families)]
        if not options or min(options)[0] > tolerance:
            errors.append({"kind": "unmatched_native_arc_circle", "arc": arc})
        else:
            families[min(options)[1]]["actual"].append(arc)
    rows = []
    for family in families:
        ref = family["reference"]
        if not family["actual"]:
            errors.append({"kind": "missing_expected_arc_circle", "arc": ref})
            continue
        radius = ref["radius"]
        ac = angle_intervals(family["actual"], radius)
        ec = angle_intervals(family["expected"], radius)
        ap = periodic_copies(ac, 2 * math.pi * radius)
        ep = periodic_copies(ec, 2 * math.pi * radius)
        extra = ac.difference(ep.buffer(tolerance, quad_segs=64)).length
        missing = ec.difference(ap.buffer(tolerance, quad_segs=64)).length
        row = dict(cx=ref["cx"], cy=ref["cy"], radius=radius,
                   actual_arc_count=len(family["actual"]), expected_arc_count=len(family["expected"]),
                   maximum_circle_parameter_error_mm=max(
                       abs(a[k] - ref[k]) for a in family["actual"]
                       for k in ("cx", "cy", "radius", "width")),
                   extra_sweep_outside_tolerance_mm=extra,
                   missing_sweep_outside_tolerance_mm=missing,
                   sweep_coverage_error_mm=max(sampled_directed_distance(ac, ep),
                                               sampled_directed_distance(ec, ap)))
        rows.append(row)
        if max(extra, missing) > 1e-11:
            errors.append({"kind": "arc_sweep_coverage_mismatch", **row})
    return rows, errors


def tangent_endpoints(record):
    kind, index, item, line = record
    if kind == "line":
        a, b = tuple(line.coords[0]), tuple(line.coords[-1])
        length = math.dist(a, b)
        direction = ((b[0] - a[0]) / length, (b[1] - a[1]) / length)
        return [(a, direction, length), (b, direction, length)]
    radius = item["radius"]
    span = math.radians((item["end_angle"] - item["start_angle"]) % 360)
    support = min(radius, radius * span)
    return [(endpoint(item, angle), (-math.sin(math.radians(angle)), math.cos(math.radians(angle))), support)
            for angle in (item["start_angle"], item["end_angle"])]


def tangent_checks(group, contacts, tolerance):
    """Report raw tangent angles and their local spatial quantization effect.

    Native cleanup can leave submicron overlapping track/arc records.  Their
    raw slope is ill-conditioned on a 2.54 nm grid.  A large angle is never
    accepted on its own: its finite support must stay inside the unchanged
    reference-curve tube, independently proved by the union coverage checks.
    """
    rows = []
    errors = []
    endpoints = [tangent_endpoints(record) for record in group]
    for i, record in enumerate(group):
        if record[0] != "arc":
            continue
        for end_index, (point, tangent, support) in enumerate(endpoints[i]):
            if contacts.covers(Point(point)):
                continue
            options = []
            for j, other in enumerate(group):
                if i == j:
                    continue
                for q, vector, other_support in endpoints[j]:
                    gap = math.dist(point, q)
                    if gap > tolerance:
                        continue
                    cosine = min(1.0, max(0.0, abs(sum(a*b for a,b in zip(tangent, vector)))))
                    angle = math.acos(cosine)
                    local_scale = min(support, other_support)
                    transverse = local_scale * math.sin(angle)
                    options.append(dict(other_kind=other[0], other_index=other[1],
                                        endpoint_gap_mm=gap, tangent_angle_deg=math.degrees(angle),
                                        local_support_mm=local_scale,
                                        local_transverse_displacement_mm=transverse))
            if not options:
                errors.append(dict(kind="arc_endpoint_without_tangent_neighbor", arc_index=record[1], end=end_index, point=point))
                continue
            # A cleanup overlap may touch both a retained tiny arc and line.
            # Report the worst apparent local slope, but require at least one
            # quantization-consistent continuation rather than infer topology
            # from duplicate primitive endpoint counts.
            best = min(options, key=lambda v: v["local_transverse_displacement_mm"])
            worst = max(options, key=lambda v: v["tangent_angle_deg"])
            rows.append(dict(arc_index=record[1], end=end_index, point=point,
                             best_continuation=best, maximum_raw_neighbor=worst))
            if best["local_transverse_displacement_mm"] > tolerance:
                errors.append(dict(kind="non_tangent_native_continuation", arc_index=record[1], end=end_index, **best))
    return rows, errors


def inspect_combined_path_equivalence(native, plan, tol=TOL):
    actual, expected = records(native), records(plan)
    failures = []
    rows = []
    if set(actual) != set(expected):
        failures.append(dict(kind="RF_group_membership_mismatch",
                             actual=sorted(actual), expected=sorted(expected)))
    for key in sorted(set(actual) & set(expected)):
        net, layer, width = key
        ag, eg = actual[key], expected[key]
        ap = unary_union([pad_geometry(p) for p in native["pads"]
                          if p["net"] == net and p["layer"] in (layer, 74)])
        ep = unary_union([pgeom(p) for p in plan["physical_pads"]
                          if p["net"] == net and p["layer"] in (layer, 74)])
        contacts = ap.intersection(ep)
        ac, ec = unary_union([r[3] for r in ag]), unary_union([r[3] for r in eg])
        ac_out, ec_out = ac.difference(contacts), ec.difference(contacts)
        ashape = unary_union([r[3].buffer(r[2]["width"] / 2, quad_segs=BUFFER_QUADS) for r in ag])
        eshape = unary_union([r[3].buffer(r[2]["width"] / 2, quad_segs=BUFFER_QUADS) for r in eg])
        ashape_out, eshape_out = ashape.difference(contacts), eshape.difference(contacts)
        # Reserving the error budget proves coverage for exact circular arcs,
        # rather than merely for the sampled chord approximation.
        approximation_bound = 2 * ARC_SAGITTA + max(width / 2 * (1 - math.cos(math.pi / (4 * BUFFER_QUADS))), 1e-10) * 2
        cover_tol = tol - approximation_bound
        actual_target = unary_union([ashape, contacts])
        expected_target = unary_union([eshape, contacts])
        values = dict(
            extra_centerline_outside_tolerance_mm=ac_out.difference(unary_union([ec, contacts]).buffer(cover_tol, quad_segs=128)).length,
            missing_centerline_outside_tolerance_mm=ec_out.difference(unary_union([ac, contacts]).buffer(cover_tol, quad_segs=128)).length,
            extra_copper_outside_tolerance_mm2=ashape_out.difference(expected_target.buffer(cover_tol, quad_segs=128)).area,
            missing_copper_outside_tolerance_mm2=eshape_out.difference(actual_target.buffer(cover_tol, quad_segs=128)).area)
        family_rows, family_errors = arc_families([r[2] for r in ag if r[0] == "arc"],
                                                [r[2] for r in eg if r[0] == "arc"], tol)
        tangent_rows, tangent_errors = tangent_checks(ag, contacts, tol)
        actual_widths, expected_widths = sorted({r[2]["width"] for r in ag}), sorted({r[2]["width"] for r in eg})
        width_error = max(abs(a-e) for a in actual_widths for e in expected_widths)
        # Hausdorff distance on copper unions including the contact copper is
        # meaningful even where cleanup trimmed a track inside its own pad.
        copper_hd = hausdorff_distance(actual_target, expected_target, densify=.25)
        row = dict(net=net, layer=layer, nominal_width=width,
                   actual_track_count=sum(r[0] == "line" for r in ag), expected_track_count=sum(r[0] == "line" for r in eg),
                   actual_arc_count=sum(r[0] == "arc" for r in ag), expected_arc_count=sum(r[0] == "arc" for r in eg),
                   actual_widths=actual_widths, expected_widths=expected_widths, maximum_width_error_mm=width_error,
                   raw_centerline_hausdorff_mm=hausdorff_distance(ac, ec, densify=.25),
                   outside_pad_centerline_maximum_sampled_distance_mm=max(sampled_directed_distance(ac_out, unary_union([ec, contacts])), sampled_directed_distance(ec_out, unary_union([ac, contacts]))),
                   contact_inclusive_copper_hausdorff_mm=copper_hd,
                   copper_approximation_error_budget_mm=approximation_bound,
                   comparison_tolerance_mm=tol,
                   arc_families=family_rows, tangency=tangent_rows, **values)
        local_failures = family_errors + tangent_errors
        if width_error > tol:
            local_failures.append(dict(kind="RF_width_mismatch", error_mm=width_error))
        if max(values["extra_centerline_outside_tolerance_mm"], values["missing_centerline_outside_tolerance_mm"]) > 1e-10:
            local_failures.append(dict(kind="combined_centerline_coverage_mismatch", **values))
        if max(values["extra_copper_outside_tolerance_mm2"], values["missing_copper_outside_tolerance_mm2"]) > 1e-12:
            local_failures.append(dict(kind="combined_copper_coverage_mismatch", **values))
        row["passed"] = not local_failures
        rows.append(row)
        failures.extend(dict(net=net, layer=layer, **error) for error in local_failures)
    return dict(passed=not failures, failures=failures, groups=rows, tolerance_mm=tol,
                arc_chord_error_bound_mm=ARC_SAGITTA,
                scope="RF only. Unsnapped full line+arc path and width-specific copper equivalence outside common matching same-net pad copper; expected circle/sweep families retained. Native pad equivalence and full route topology are separate mandatory checks.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("native", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    nb, pb = args.native.read_bytes(), args.candidate.read_bytes()
    n, p = json.loads(nb), json.loads(pb)
    result = inspect_combined_path_equivalence(n, p)
    result.update(native_sha256=n.get("source_sha256"), native_snapshot_sha256=hashlib.sha256(nb).hexdigest(),
                  candidate_sha256=hashlib.sha256(pb).hexdigest(), helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k != "groups"}, indent=2))
    print(json.dumps(dict(group_count=len(result["groups"]),
                         maximum_outside_pad_centerline_error_mm=max(r["outside_pad_centerline_maximum_sampled_distance_mm"] for r in result["groups"]),
                         maximum_contact_inclusive_copper_hausdorff_mm=max(r["contact_inclusive_copper_hausdorff_mm"] for r in result["groups"])), indent=2))
    raise SystemExit(0 if result["passed"] else 2)


if __name__ == "__main__":
    main()
