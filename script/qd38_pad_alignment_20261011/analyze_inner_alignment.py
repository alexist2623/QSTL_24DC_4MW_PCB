"""Offline QD nearest-corner alignment feasibility; never edits source designs."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import math
import sys

import numpy as np
import shapely
from shapely.geometry import Point, Polygon, box
from shapely.affinity import translate
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "script/qd38_rotation_20261011"
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OLD))
from route_rf_corridor_bounded import pgeom

BOUNDARIES = {"LEFT": (0, 7.4, 1), "RIGHT": (0, 12.1, -1),
              "BOTTOM": (1, 39.65, 1), "TOP": (1, 45.35, -1)}
GAP = .15


def effective_side(meta):
    # The four corner pads already meet the horizontal inner line.  Their
    # unequal-angle rays cannot meet both rectangular boundaries at once.
    if meta["side"] == "CORNER":
        return "TOP" if meta["normal"][1] > 0 else "BOTTOM"
    return meta["side"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nearest_coordinate(geometry, side):
    axis, _, sign = BOUNDARIES[side]
    values = [xy[axis] for xy in list(geometry.exterior.coords)[:-1]]
    return max(values) if sign > 0 else min(values)


def summarize(pads, meta, vias, all_vias, other_pads):
    geometry = {int(p["pin"]): pgeom(p) for p in pads}
    pairs = [(geometry[a].distance(geometry[b]), a, b)
             for a in geometry for b in geometry if a < b]
    cavity = box(7.6, 39.85, 11.9, 45.15)
    via_rows = []
    for via in vias:
        number = int(via["label"].split("-")[1])
        q = next(p for p in pads if int(p["pin"]) == number)
        centre = Point(via["x"], via["y"])
        drill = centre.buffer(via["hole"] / 2, quad_segs=128)
        # Subtract radius from the exact point-to-polygon distance instead of
        # allowing a polygonized via land to understate its occupied radius.
        blockers = [(f"Q1-{n}", g) for n, g in geometry.items() if n != number]
        blockers += [(f"{p['ref']}-{p['pin']}", pgeom(p)) for p in other_pads if p["net"] != via["net"]]
        gap, nearest = min((centre.distance(g) - via["diameter"] / 2, label) for label, g in blockers)
        rows = [(math.hypot(via["x"] - v["x"], via["y"] - v["y"]) - (via["diameter"] + v["diameter"]) / 2,
                 v["label"]) for v in all_vias if v["label"] != via["label"] and v["net"] != via["net"]]
        vg, vn = min(rows)
        via_rows.append(dict(pad=number, drill_contained=geometry[number].covers(drill),
                             drill_outside_pad_area_mm2=drill.difference(geometry[number]).area,
                             foreign_pad_gap_mm=gap, nearest_foreign_pad=nearest,
                             foreign_via_gap_mm=vg, nearest_foreign_via=vn,
                             passed=geometry[number].covers(drill) and gap >= GAP - 1e-8 and vg >= GAP - 1e-8))
    sides = {}
    for side in BOUNDARIES:
        data = [nearest_coordinate(geometry[m["number"]], side) for m in meta if effective_side(m) == side]
        sides[side] = dict(minimum=min(data), maximum=max(data), spread_mm=max(data) - min(data),
                           target=BOUNDARIES[side][1])
    return dict(minimum_pad_pair_gap_mm=min(pairs)[0], nearest_pad_pair=list(min(pairs)[1:]),
                minimum_cavity_gap_mm=min(g.distance(cavity) for g in geometry.values()),
                nearest_corner_boundaries=sides, via_checks=via_rows,
                via_failure_pad_ids=[v["pad"] for v in via_rows if not v["passed"]],
                pad_geometry_passed=min(pairs)[0] >= GAP - 1e-8 and min(g.distance(cavity) for g in geometry.values()) >= .2 - 1e-8)


def main():
    src = OLD / "full_copper_candidate.json"
    native_path = OLD / "saved_revision_snapshot.json"
    old = json.loads(src.read_text())
    native = json.loads(native_path.read_text())
    assert sha(src) == "835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495"
    qd = deepcopy([p for p in old["physical_pads"] if p["ref"] == "Q1"])
    metadata = {m["number"]: m for m in old["pads"]}
    before = deepcopy(qd)
    qvias = deepcopy([v for v in old["vias"] if v["label"].startswith("Q1-")])
    other_pads = [p for p in old["physical_pads"] if p["ref"] != "Q1" and p["layer"] in (32, 74)]
    shifts = []
    for p in qd:
        n = int(p["pin"])
        side = effective_side(metadata[n])
        axis, target, _ = BOUNDARIES[side]
        direction = np.array(metadata[n]["normal"])
        existing = nearest_coordinate(pgeom(p), side)
        displacement = (target - existing) / direction[axis]
        dx, dy = displacement * direction
        p["x"] += float(dx)
        p["y"] += float(dy)
        # Translation preserves each individual pad's ray and rectangle; it
        # does not align its complete, tilted short edge with a board axis.
        tangent_axis_span = p["sy"] * abs(direction[1 - axis])
        shifts.append(dict(pad=n, side=side, original_side=metadata[n]["side"], before=[before[qd.index(p)]["x"], before[qd.index(p)]["y"]],
                           after=[p["x"], p["y"]], displacement_mm=float(displacement),
                           delta_mm=[float(dx), float(dy)], nearest_corner_before=existing,
                           nearest_corner_after=nearest_coordinate(pgeom(p), side),
                           complete_end_edge_normal_span_mm=float(tangent_axis_span), rf=metadata[n]["rf"]))
    before_metrics = summarize(before, old["pads"], qvias, old["vias"], other_pads)
    fixed_metrics = summarize(qd, old["pads"], qvias, old["vias"], other_pads)
    geom = {int(p["pin"]): pgeom(p) for p in qd}
    best_vias = []
    feasibility = []
    candidate_lists = {}
    offsets = np.linspace(-.3, .3, 241)
    lateral = np.linspace(-.025, .025, 11)
    other_vias = [v for v in old["vias"] if not v["label"].startswith("Q1-")]
    for via in qvias:
        n = int(via["label"].split("-")[1])
        p = next(p for p in qd if int(p["pin"]) == n)
        u = np.array(metadata[n]["normal"])
        v = np.array([-u[1], u[0]])
        grid = np.array([(a, b) for a in offsets for b in lateral])
        xy = np.array([p["x"], p["y"]]) + grid[:, :1] * u + grid[:, 1:] * v
        points = shapely.points(xy)
        blockers = [g for number, g in geom.items() if number != n]
        blockers += [pgeom(op) for op in other_pads if op["net"] != via["net"]]
        foreign = unary_union(blockers)
        gaps = shapely.distance(points, foreign) - .2
        for ov in other_vias:
            if ov["net"] == via["net"]:
                continue
            gaps = np.minimum(gaps, np.linalg.norm(xy - np.array([ov["x"], ov["y"]]), axis=1) - (.4 + ov["diameter"]) / 2)
        displacement = np.linalg.norm(xy - np.array([via["x"], via["y"]]), axis=1)
        feasible = np.where(gaps >= GAP + 1e-5)[0]
        best_index = min(feasible, key=lambda i: displacement[i]) if len(feasible) else int(np.argmax(gaps))
        best = deepcopy(via)
        best.update(x=float(xy[best_index, 0]), y=float(xy[best_index, 1]),
                    pad_axis_offset_mm=float(grid[best_index, 0]), pad_lateral_offset_mm=float(grid[best_index, 1]))
        best_vias.append(best)
        # Candidate grid endpoints have their complete .2 mm drill inside
        # the unchanged .8 x .25 pad, including tangent-boundary cases.
        candidate_lists[n] = [dict(x=float(xy[i, 0]), y=float(xy[i, 1]),
                                   axial=float(grid[i, 0]), lateral=float(grid[i, 1]),
                                   clearance_mm=float(gaps[i]), movement_mm=float(displacement[i]))
                             for i in sorted(feasible, key=lambda i: displacement[i])[:50]]
        feasibility.append(dict(pad=n, feasible_grid_count=len(feasible),
                                maximum_foreign_pad_and_fixed_via_gap_mm=float(np.max(gaps)),
                                selected_gap_mm=float(gaps[best_index]), selected_via_xy=[best["x"], best["y"]],
                                selected_movement_mm=float(displacement[best_index]),
                                placement_feasible_individually=bool(len(feasible)),
                                caveat="Individual feasibility excludes movable QD-to-QD via pair constraints; grid is 2.5 um axial / 5 um lateral."))
    updated_all = other_vias + best_vias
    relocated_metrics = summarize(qd, old["pads"], best_vias, updated_all, other_pads)
    result = dict(scope="Offline nearest-corner alignment feasibility, not a native design or routed candidate.",
                  source_candidate_sha256=sha(src), source_native_sha256=native["source_sha256"],
                  cavity_mm=old["cavity_mm"], sample_center=old["sample_center"], pad_size_mm=[.8, .25],
                  full_short_edges_collinear=False,
                  explanation="At preserved unequal pad rotations, common horizontal/vertical complete short edges are mathematically incompatible with fixed rectangular pads. This proposal aligns only each nearest corner while translating along the existing long-axis/bond ray.",
                  maximum_pad_movement_mm=max(abs(s["displacement_mm"]) for s in shifts),
                  moved_rf_pad_ids=[s["pad"] for s in shifts if s["rf"] and abs(s["displacement_mm"]) > 1e-9],
                  pad_shifts=shifts, before=before_metrics, fixed_vias=fixed_metrics,
                  independent_via_search=feasibility, relocated_vias=relocated_metrics,
                  preserved_source_hashes=(sha(src) == "835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495"))
    (OUT / "nearest_corner_alignment_metrics.json").write_text(json.dumps(result, indent=2))
    proposal = dict(status="OFFLINE PROPOSAL ONLY; existing routing/surfaces are not revalidated", qd_pads=qd,
                    fixed_qd_vias=qvias, individually_selected_qd_vias=best_vias,
                    feasible_via_candidates=candidate_lists, source_candidate_sha256=sha(src))
    (OUT / "nearest_corner_alignment_proposal.json").write_text(json.dumps(proposal, indent=2))
    render(before, qd, qvias, best_vias, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("pad_shifts", "before", "fixed_vias", "relocated_vias")}, indent=2))
    print(json.dumps(dict(before_min_gap=before_metrics["minimum_pad_pair_gap_mm"],
                          aligned_min_gap=fixed_metrics["minimum_pad_pair_gap_mm"],
                          fixed_via_failures=fixed_metrics["via_failure_pad_ids"],
                          individually_infeasible=[r["pad"] for r in feasibility if not r["placement_feasible_individually"]],
                          relocated_via_failures=relocated_metrics["via_failure_pad_ids"]), indent=2))


def render(before, after, fixed_vias, best_vias, report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch, Circle, Rectangle
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    fig.subplots_adjust(bottom=.15, top=.89, left=.065, right=.99, wspace=.19)
    for ax, pads, vias, title in zip(axes, (before, after), (fixed_vias, best_vias),
                                   ("Saved QD pad field", "Common nearest-corner boundary (offline proposal)")):
        ax.add_patch(Rectangle((7.6, 39.85), 4.3, 5.3, facecolor="#d9e2eb", edgecolor="#637183", lw=1.2))
        ax.add_patch(Rectangle((7.4, 39.65), 4.7, 5.7, fill=False, edgecolor="#14836b", ls="--", lw=1.2))
        for p in pads:
            color = "#387fa6" if p["net"].startswith("MW") else "#cd9a3f"
            ax.add_patch(Patch(np.array(pgeom(p).exterior.coords), facecolor=color, edgecolor="#394956", lw=.5))
            ax.text(p["x"], p["y"], p["pin"], fontsize=7, ha="center", va="center", color="white")
        for via in vias:
            ax.add_patch(Circle((via["x"], via["y"]), .2, fill=False, edgecolor="#652a68", lw=.8))
            ax.add_patch(Circle((via["x"], via["y"]), .1, fill=False, edgecolor="#652a68", lw=.6))
        ax.set(xlim=(6, 13.5), ylim=(38, 47), aspect="equal", title=title, xlabel="X (mm)", ylabel="Y (mm)")
        ax.grid(alpha=.15)
    fig.suptitle("QD pad-end alignment review: same dimensions, angles and bond rays", fontsize=14)
    fig.text(.5, .028, "Dashed boundary: X=7.4 / 12.1, Y=39.65 / 45.35 mm. Tilted complete short edges are NOT collinear.\nPurple: Ø0.4 / Ø0.2 mm direct-DC vias. Right panel is an infeasible trial: adjacent via gaps remain below 0.15 mm.", ha="center", fontsize=9)
    fig.savefig(OUT / "nearest_corner_alignment_preview.png", dpi=180, bbox_inches="tight")


if __name__ == "__main__":
    main()
