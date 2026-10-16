"""Read-only rotated-QD mask and solid-ground checks, including RF arcs.

Run only after the final native save/reopen. This checks explicit mask regions;
ordinary pad apertures and effective via paste remain separate CAM checks.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import html
import json
import math
import re
import struct
import sys

import olefile
from shapely.affinity import rotate, translate
from shapely.geometry import Point, LineString, Polygon, box, shape
from shapely.ops import unary_union
from audit_smp_rings import inspect_smp_rings

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / "QSTL_QD4_2SET_38PAD"
sys.path.insert(0, str(ROOT / "script/_support/qd_center_revision"))
from native_metadata_helpers import properties, binary_records, pads_stream, UNIT

COPPER = (1, 2, 3, 4, 5, 32)
COORD_TOL = 1e-5
EXPORT_TOL = .003  # 1 um simplification plus tessellation of up-to-5-mm round lands.


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pad_shape(p):
    if p["shape"] == 1:
        assert abs(p["sx"] - p["sy"]) < COORD_TOL
        return Point(p["x"], p["y"]).buffer(p["sx"] / 2, quad_segs=96)
    assert p["shape"] == 2, "Unexpected saved pad shape"
    return translate(rotate(box(-p["sx"] / 2, -p["sy"] / 2,
                                p["sx"] / 2, p["sy"] / 2),
                            p["rotation"], origin=(0, 0)), p["x"], p["y"])


def rectangle(g, margin):
    a, b, c, d = g.bounds
    return box(a - margin, b - margin, c + margin, d + margin)


def read_snapshot(path, sch):
    with olefile.OleFileIO(path) as doc:
        streams = {"/".join(k): doc.openstream(k).read() for k in doc.listdir()}
    components = properties(streams["Components6/Data"])
    nets = properties(streams["Nets6/Data"])
    uid = {value: ref for ref, value in sch["components"].items()}
    names = {i: uid.get(c.get("SOURCEUNIQUEID", "").strip("\\"), c.get("SOURCEDESIGNATOR"))
             for i, c in enumerate(components)}
    assert all(names.values()), "Missing saved schematic component mapping"
    def net(index):
        return None if index == 65535 else nets[index]["NAME"]
    pads = []
    for raw in pads_stream(streams["Pads6/Data"]):
        x, y, sx, sy, _, _, _, _, drill = (v * UNIT for v in raw["coords"])
        p = dict(ref=None if raw["component"] == 65535 else names[raw["component"]],
                 pin=raw["number"], net=net(raw["net"]), x=x, y=y, sx=sx, sy=sy,
                 hole=drill, rotation=raw["rotation"], shape=raw["shape"], layer=raw["layer"])
        p["geometry"] = pad_shape(p)
        pads.append(p)
    regions = []
    for record in binary_records(streams["Regions6/Data"], 11):
        b = record["body"]
        start = b.index(b"V7_LAYER=")
        length = struct.unpack_from("<I", b, start - 4)[0] & 0xffffff
        fields = dict(t.split("=", 1) for t in b[start:start + length].rstrip(b"\0").decode("cp1252").split("|") if "=" in t)
        pos = start + length
        rings = []
        while pos < len(b):
            count = struct.unpack_from("<I", b, pos)[0]
            pos += 4
            rings.append([tuple(v * UNIT for v in struct.unpack_from("<2d", b, pos + 16 * i)) for i in range(count)])
            pos += count * 16
        assert pos == len(b)
        regions.append(dict(name=fields.get("NAME"), layer=b[0],
                            net=net(struct.unpack_from("<H", b, 3)[0]),
                            geometry=Polygon(rings[0], rings[1:])))
    tracks = []
    for record in binary_records(streams["Tracks6/Data"], 4):
        b = record["body"]
        x1, y1, x2, y2, width = (v * UNIT for v in struct.unpack_from("<5i", b, 13))
        tracks.append(dict(net=net(struct.unpack_from("<H", b, 3)[0]), layer=b[0],
                           width=width, geometry=LineString([(x1, y1), (x2, y2)])))
    # Sample exact saved circle parameters with less than 0.1 um chord error.
    # The native revision audit separately verifies those exact parameters.
    for record in binary_records(streams["Arcs6/Data"], 1):
        b = record["body"]
        cx, cy, radius = (v * UNIT for v in struct.unpack_from("<3i", b, 13))
        a0, a1 = struct.unpack_from("<2d", b, 25)
        sweep = (a1 - a0) % 360 or 360
        if radius <= 0:
            continue
        max_step = 2 * math.acos(max(-1, 1 - 1e-4 / radius))
        count = max(2, math.ceil(math.radians(sweep) / max_step))
        points = [(cx + radius * math.cos(math.radians(a0 + sweep * j / count)),
                   cy + radius * math.sin(math.radians(a0 + sweep * j / count)))
                  for j in range(count + 1)]
        tracks.append(dict(net=net(struct.unpack_from("<H", b, 3)[0]), layer=b[0],
                           width=struct.unpack_from("<i", b, 41)[0] * UNIT,
                           geometry=LineString(points), is_arc=True))
    vias = []
    for record in binary_records(streams["Vias6/Data"], 3):
        b = record["body"]
        x, y, diameter, hole = (v * UNIT for v in struct.unpack_from("<4i", b, 13))
        vias.append(dict(net=net(struct.unpack_from("<H", b, 3)[0]), x=x, y=y,
                         diameter=diameter, hole=hole, low=b[29], high=b[30]))
    board = properties(streams["Board6/Data"])[0]
    mm = lambda v: float(v.removesuffix("mil")) * .0254
    outline = Polygon([(mm(board["VX" + str(i)]), mm(board["VY" + str(i)])) for i in range(4)])
    return pads, regions, tracks, vias, outline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--schematic", type=Path, default=DEST / "schematic_validation.json")
    parser.add_argument("--expected-rules", type=int, default=23)
    parser.add_argument("--expected-via-rules", type=int, default=4)
    args = parser.parse_args()
    assert args.expected_rules >= 23 and args.expected_via_rules >= 4
    native_path = DEST / "QSTL_QD4_2SET_38PAD.PcbDoc"
    candidate_path = args.candidate.resolve()
    native_sha, candidate_sha = digest(native_path), digest(candidate_path)
    plan = json.loads(candidate_path.read_text())
    sch = json.loads(args.schematic.read_text())
    pads, regions, tracks, vias, board = read_snapshot(native_path, sch)
    errors, results = [], {}
    def check(ok, issue, details=None):
        if not ok:
            errors.append(dict(issue=issue, details=details))
    ring_audit=inspect_smp_rings(plan,pads,vias)
    check(ring_audit['passed'],'saved_SMP_ring_requirements',ring_audit['failures'])
    results['SMP_rings']=ring_audit
    ground = {layer: unary_union([r["geometry"] for r in regions if r["layer"] == layer and r["net"] == "GND"]) for layer in COPPER}
    from audit_shield_surface_geometry import inspect_shield_clearance
    shield_audit=inspect_shield_clearance(plan,pads,tracks,vias,ground)
    check(shield_audit['passed'],'saved_shield_GND_signal_clearance',shield_audit['errors'])
    results['shield_geometry']=shield_audit
    openings = {layer: unary_union([r["geometry"] for r in regions if r["layer"] == layer]) for layer in (37, 38)}
    # Compare the physical saved regions, not just a previous audit status.
    comparisons = []
    for family, field in (("GND", "ground_regions"), ("MASK", "solder_openings")):
        for layer, geojson in plan[field].items():
            expected = shape(geojson).simplify(.001, preserve_topology=True)
            actual = ground[int(layer)] if family == "GND" else openings[int(layer)]
            distance = actual.hausdorff_distance(expected)
            comparisons.append(dict(family=family, layer=int(layer), hausdorff_mm=distance))
            check(distance <= COORD_TOL, "saved_candidate_region_mismatch", comparisons[-1])
    results["saved_candidate_region_comparison"] = comparisons

    mounts = [p for p in pads if p["ref"] is None]
    check(len(mounts) == 8, "mount_count", len(mounts))
    check(all(p["net"] == "GND" and p["layer"] == 74 for p in mounts), "mount_ground_or_layer")
    mount_opening = unary_union([p["geometry"].buffer(.10, quad_segs=96) for p in mounts])
    results["mount_mask"] = []
    for p in mounts:
        wanted = p["geometry"].buffer(.10, quad_segs=96)
        per_side = {}
        for layer in (37, 38):
            missing = wanted.difference(openings[layer].buffer(EXPORT_TOL)).area
            per_side[str(layer)] = missing
            check(missing < 1e-8, "mount_not_open_on_both_faces", dict(pin=p["pin"], x=p["x"], y=p["y"], layer=layer, missing_mm2=missing))
        results["mount_mask"].append(dict(pin=p["pin"], center_mm=[p["x"], p["y"]], missing_mm2=per_side))

    field = rectangle(unary_union([p["geometry"] for p in pads if p["ref"] == "Q1"]), .15)
    check(field.hausdorff_distance(shape(plan["qd_mask_field"])) < COORD_TOL, "QD_mask_field_geometry")
    missing = field.difference(openings[38].buffer(EXPORT_TOL)).area
    check(missing < 1e-8, "QD_Bottom_mask_not_open", missing)
    results["QD_Bottom_mask_open_missing_mm2"] = missing
    cx, cy = plan["sample_center"]
    ex, ey = (v + .4 for v in plan["cavity_mm"])
    check(math.dist([cx, cy], [9.75, 42.5]) < COORD_TOL, "sample_datum_changed")
    check(math.dist(plan["cavity_mm"], [4.3, 5.3]) < COORD_TOL, "cavity_not_rotated_4p3x5p3")
    exclusion = box(cx-ex/2, cy-ey/2, cx+ex/2, cy+ey/2)
    check(exclusion.hausdorff_distance(shape(plan["qd_ground_exclusion"])) < COORD_TOL, "QD_exclusion_not_4p7x5p7")
    results["QD_GND"] = {}
    for layer in COPPER:
        complete_ground = unary_union([ground[layer]] +
            [p["geometry"] for p in pads if p["net"] == "GND" and p["layer"] in (layer, 74)] +
            [Point(v["x"], v["y"]).buffer(v["diameter"] / 2, quad_segs=96)
             for v in vias if v["net"] == "GND" and v["low"] <= layer <= v["high"]] +
            [t["geometry"].buffer(t["width"] / 2, quad_segs=96)
             for t in tracks if t["net"] == "GND" and t["layer"] == layer])
        if layer == 1:
            missing = exclusion.difference(complete_ground.buffer(COORD_TOL)).area
            check(missing < 1e-8, "QD_Top_GND_not_preserved", missing)
            results["QD_GND"][str(layer)] = dict(missing_Top_mm2=missing)
        else:
            overlap = complete_ground.intersection(exclusion.buffer(-COORD_TOL)).area
            check(overlap < 1e-8, "QD_GND_inside_exclusion", dict(layer=layer, overlap_mm2=overlap))
            results["QD_GND"][str(layer)] = dict(unwanted_GND_mm2=overlap)

    def protected_check(wanted, label, layer):
        # Apertures due to explicit general-opening regions may not intrude
        # into the protected area. Native standard pad apertures are separate.
        forbidden_opening = wanted.buffer(-EXPORT_TOL).intersection(openings[layer]).area
        check(forbidden_opening < 1e-8, label, dict(layer=layer, intrusion_mm2=forbidden_opening))
        return forbidden_opening
    rc_results = []
    for number in sorted(plan["rc_mask_rectangles"], key=int):
        group = [p["geometry"] for p in pads if p["ref"] in (f"R{int(number):02}", f"C{int(number):02}")]
        check(len(group) == 4, "RC_pad_count", number)
        wanted = rectangle(unary_union(group), .90)
        distance = wanted.hausdorff_distance(shape(plan["rc_mask_rectangles"][number]))
        check(distance <= COORD_TOL, "RC_rectangle_not_0p90_margin", dict(pair=number, error_mm=distance))
        top = wanted.difference(mount_opening)
        bottom = wanted.difference(field).difference(mount_opening)
        rc_results.append(dict(pair=number, bounds_mm=list(wanted.bounds), margin_mm=.90,
                               top_intrusion_mm2=protected_check(top, "RC_Top_mask_unprotected", 37),
                               bottom_intrusion_mm2=protected_check(bottom, "RC_Bottom_mask_unprotected", 38)))
    results["RC_protected_rectangles"] = rc_results
    zif = [v for v in vias if v["net"] != "GND" and v["y"] < 8]
    check(len(zif) == 38, "ZIF_via_count", len(zif))
    zifbox = rectangle(unary_union([Point(v["x"], v["y"]).buffer(v["diameter"] / 2, quad_segs=96) for v in zif]), .40)
    check(zifbox.hausdorff_distance(shape(plan["zif_bottom_mask_rectangle"])) < COORD_TOL, "ZIF_Bottom_rectangle_margin")
    results["ZIF_Bottom_mask"] = dict(bounds_mm=list(zifbox.bounds), margin_mm=.40,
        intrusion_mm2=protected_check(zifbox.difference(field).difference(mount_opening), "ZIF_Bottom_mask_unprotected", 38))
    rf = unary_union([t["geometry"] for t in tracks if t["layer"] == 32 and (t["net"] or "").startswith(("S", "MW"))])
    protected = rf.buffer(.71, quad_segs=96).difference(field).difference(mount_opening)
    results["RF_Bottom_mask"] = dict(centerline_buffer_mm=.71,
        intrusion_mm2=protected_check(protected, "RF_Bottom_strip_unprotected", 38))

    # An independent local plane construction contains only real signal
    # clearance voids, not a thermal-relief ring or spokes. Compare every
    # mounting land's immediate neighbourhood against that solid reference.
    attachment = []
    for layer in COPPER:
        obstacles = [p["geometry"].buffer(.203, quad_segs=96) for p in pads
                     if p["net"] != "GND" and p["layer"] in (layer, 74)]
        obstacles += [t["geometry"].buffer(t["width"] / 2 + .203, quad_segs=96)
                      for t in tracks if t["net"] not in (None, "GND") and t["layer"] == layer]
        obstacles += [Point(v["x"], v["y"]).buffer(v["diameter"] / 2 + .203, quad_segs=96)
                      for v in vias if v["net"] != "GND" and v["low"] <= layer <= v["high"]]
        if layer != 1:
            obstacles.append(exclusion)
        solid_reference = board.buffer(-.2, join_style="mitre").difference(unary_union(obstacles))
        for p in mounts:
            neighbourhood = p["geometry"].buffer(.10, quad_segs=96)
            expected = solid_reference.intersection(neighbourhood)
            missing = expected.difference(ground[layer].buffer(EXPORT_TOL)).area
            land_contact = ground[layer].intersection(p["geometry"]).area
            check(missing < 1e-8 and land_contact > .05, "mount_not_direct_solid_GND",
                  dict(layer=layer, x=p["x"], y=p["y"], missing_mm2=missing, land_contact_mm2=land_contact))
            attachment.append(dict(layer=layer, center_mm=[p["x"], p["y"]],
                                   unexpected_thermal_void_mm2=missing, land_contact_mm2=land_contact))
    results["mount_direct_GND"] = attachment
    drc_path = H / "Native_DRC.html"
    drc_sha = digest(drc_path)
    drc_text = drc_path.read_text(errors="replace")
    summary = re.findall(r'<td class="column1"><a href="#[^"]+">(.*?)</a></td>\s*<td class="column2">(\d+)</td>', drc_text, re.S)
    summary = [dict(rule=html.unescape(re.sub("<[^>]+>", "", name)), violations=int(count))
               for name, count in summary]
    early_stop = bool(re.search(r"DRC\s+was\s+stopped", drc_text, re.I))
    via_rules = [v for v in summary if "Via" in v["rule"] and ("Style" in v["rule"] or "Routing" in v["rule"])]
    component_rules = [v for v in summary if "Component Clearance" in v["rule"]]
    dc_pair_rules = [v for v in summary if "Clearance Constraint" in v["rule"] and
                     "ExistsOnLayer('L2_DC_A')" in v["rule"] and "ExistsOnLayer('L4_DC_B')" in v["rule"] and
                     "InNet('DC01')" in v["rule"] and "InNet('DC38')" in v["rule"] and
                     re.search(r"Gap=0\.10?mm", v["rule"])]
    dc_ground_rules = [v for v in summary if "Clearance Constraint" in v["rule"] and
                       "ExistsOnLayer('L2_DC_A')" in v["rule"] and "ExistsOnLayer('L4_DC_B')" in v["rule"] and
                       "InNet('GND')" in v["rule"] and "InNet('DC01')" in v["rule"] and "InNet('DC38')" in v["rule"] and
                       re.search(r"Gap=0\.20?mm",v["rule"])]
    check(len(summary) == args.expected_rules and all(v["violations"] == 0 for v in summary), "native_DRC_expected_zero_rules_missing", summary)
    check(len(via_rules) == args.expected_via_rules and len(component_rules) == 1, "native_DRC_missing_via_or_component_coverage", summary)
    check(len(dc_pair_rules) == 1 and dc_pair_rules[0]["violations"] == 0, "native_DRC_missing_DC_pair_clearance_coverage", dc_pair_rules)
    check(len(dc_ground_rules) == 1 and dc_ground_rules[0]["violations"] == 0, "native_DRC_missing_DC_GND_through_object_coverage", dc_ground_rules)
    check(not early_stop, "native_DRC_stopped_early")
    results["native_DRC"] = dict(report=str(drc_path), report_sha256=drc_sha,
        categories=len(summary), violation_sum=sum(v["violations"] for v in summary),
        via_style_rule_count=len(via_rules), component_rule_count=len(component_rules),
        DC_pair_clearance_rule_count=len(dc_pair_rules),
        early_stop=early_stop, summary=summary)
    assert digest(native_path) == native_sha, "Native changed during audit"
    assert digest(candidate_path) == candidate_sha, "Candidate changed during audit"
    assert digest(drc_path) == drc_sha, "DRC report changed during audit"
    report = dict(passed=not errors, status="SAVED_NATIVE_SURFACE_SEMANTICS_READ_ONLY",
                  native_file=str(native_path), native_sha256=native_sha,
                  candidate_sha256=candidate_sha, export_geometry_tolerance_mm=EXPORT_TOL,
                  coordinate_tolerance_mm=COORD_TOL, checks=results, errors=errors,
                  limitation="Explicit solder-mask regions checked. Ordinary pad apertures and effective via paste require separate native/CAM verification.")
    (H / "saved_revision_surface.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(dict(passed=not errors, native_sha256=native_sha, candidate_sha256=candidate_sha,
                          mounts=len(mounts), RC_groups=len(rc_results), direct_GND_checks=len(attachment),
                          native_DRC_categories=len(summary), native_DRC_violations=sum(v["violations"] for v in summary),
                          errors=errors), indent=2))


if __name__ == "__main__":
    main()
