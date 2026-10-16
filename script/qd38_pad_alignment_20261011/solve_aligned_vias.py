"""Continuous-domain bounds and discrete joint search for aligned QD vias."""
from pathlib import Path
import json
import sys
import math
import numpy as np
from scipy.spatial.distance import cdist
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "script/qd38_rotation_20261011"
sys.path.insert(0, str(OLD))
from route_rf_corridor_bounded import pgeom


def vertices(geometry):
    if geometry.is_empty:
        return np.empty((0, 2))
    if geometry.geom_type == "Polygon":
        return np.array(geometry.exterior.coords)[:-1]
    if geometry.geom_type in ("LineString", "Point"):
        return np.array(geometry.coords)
    return np.vstack([vertices(g) for g in geometry.geoms if not g.is_empty])


def main():
    proposal = json.loads((HERE / "nearest_corner_alignment_proposal.json").read_text())
    source = json.loads((OLD / "full_copper_candidate.json").read_text())
    pads = proposal["qd_pads"]
    vias = proposal["fixed_qd_vias"]
    qids = [int(v["label"].split("-")[1]) for v in vias]
    oldvias = [v for v in source["vias"] if not v["label"].startswith("Q1-")]
    allpads = pads + [p for p in source["physical_pads"] if p["ref"] != "Q1" and p["layer"] in (32, 74)]
    geometries = [(p, pgeom(p)) for p in allpads]
    regions = {}
    domains = []
    for via in vias:
        number = int(via["label"].split("-")[1])
        p, g = next((p, g) for p, g in geometries if p["ref"] == "Q1" and int(p["pin"]) == number)
        # A rectangle inset by the drill radius describes exact full circular
        # hole containment.  Polygonized exterior buffers below underestimate
        # exclusion, so this is an optimistic feasible-region superset: an
        # impossibility bound remains valid despite circle approximation.
        region = g.buffer(-.1, join_style="mitre")
        for other, og in geometries:
            if other["net"] == via["net"] or region.is_empty:
                continue
            if region.distance(og) <= .35 + 1e-9:
                region = region.difference(og.buffer(.35, quad_segs=512))
        for ov in oldvias:
            radius = .2 + ov["diameter"] / 2 + .15
            point = Point(ov["x"], ov["y"])
            if region.distance(point) <= radius + 1e-9:
                region = region.difference(point.buffer(radius, quad_segs=512))
        regions[number] = region
        domains.append(dict(pad=number, empty=region.is_empty, area_mm2=region.area,
                            bounds_mm=list(region.bounds), geometry=region.__geo_interface__))
    pairrows = []
    impossible = []
    for i, a in enumerate(qids):
        ra = regions[a]
        if ra.is_empty:
            continue
        va = vertices(ra.convex_hull)
        for b in qids[i + 1:]:
            rb = regions[b]
            if rb.is_empty or ra.distance(rb) >= .55:
                continue
            vb = vertices(rb.convex_hull)
            distances = cdist(va, vb)
            index = np.unravel_index(np.argmax(distances), distances.shape)
            maximum = float(distances[index])
            row = dict(pads=[a, b], maximum_possible_center_distance_mm=maximum,
                       maximum_possible_land_edge_gap_mm=maximum - .4,
                       required_center_distance_mm=.55,
                       optimistic_farthest_pair_xy=[va[index[0]].tolist(), vb[index[1]].tolist()],
                       impossible=maximum < .55 - 1e-8)
            pairrows.append(row)
            if row["impossible"]:
                impossible.append(row)
    report = dict(status="continuous optimistic via-domain feasibility bound", fixed_inner_boundaries_mm=dict(left=7.4, right=12.1, bottom=39.65, top=45.35),
                  pad_dimensions_preserved=True, pad_angles_and_rays_preserved=True,
                  via_diameter_mm=.4, drill_mm=.2, required_via_land_gap_mm=.15,
                  required_drill_gap_mm=.254,
                  polygon_buffer_underestimate_bound_mm=.35*(1-math.cos(math.pi/(4*512))),
                  empty_domains=[d["pad"] for d in domains if d["empty"]],
                  impossible_pairs=impossible,
                  joint_geometry_impossible=bool(impossible or any(d["empty"] for d in domains)),
                  proof="Each via center lies inside its pad inset by .1 mm, outside all foreign pads inflated by .35 mm and fixed via keepouts. Polygonized circular buffers make domains slightly too large. The farthest pair between convex hull vertices is an upper bound on any two feasible via-center positions. If even this upper bound is below .55 mm, no axial/lateral stagger or discrete search can satisfy .15 mm land clearance.",
                  pair_bounds=pairrows, domains=domains)
    (HERE / "aligned_via_joint_feasibility.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k not in ("pair_bounds", "domains")}, indent=2))


if __name__ == "__main__":
    main()
