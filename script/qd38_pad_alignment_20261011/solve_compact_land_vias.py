"""Offline finite-domain joint QD via placement with unchanged .20 mm drills."""
from pathlib import Path
from copy import deepcopy
import argparse
import hashlib
import json
import math
import sys
import numpy as np
import shapely
from shapely.geometry import Point, box
from shapely.ops import unary_union
from scipy.spatial.distance import cdist

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / "script/qd38_rotation_20261011"
sys.path.insert(0, str(OLD))
from route_rf_corridor_bounded import pgeom


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--land", type=float, default=.35)
    args = parser.parse_args()
    source_file = OLD / "full_copper_candidate.json"
    source_bytes = source_file.read_bytes()
    source = json.loads(source_bytes)
    proposal = json.loads((HERE / "nearest_corner_alignment_proposal.json").read_text())
    pads = proposal["qd_pads"]
    old_qvias = proposal["fixed_qd_vias"]
    other_pads = [p for p in source["physical_pads"] if p["ref"] != "Q1" and p["layer"] in (32, 74)]
    fixed_vias = [v for v in source["vias"] if not v["label"].startswith("Q1-")]
    safety = 2e-5
    minimum_center = max(args.land + .15, .2 + .254) + safety
    qids = [int(v["label"].split("-")[1]) for v in old_qvias]
    arrays = []
    costs = []
    info = []
    for oldvia, n in zip(old_qvias, qids):
        pad = next(p for p in pads if int(p["pin"]) == n)
        theta = math.radians(pad["rotation"])
        u, v = np.array([math.cos(theta), math.sin(theta)]), np.array([-math.sin(theta), math.cos(theta)])
        original = np.array([oldvia["x"], oldvia["y"]])
        center = np.array([pad["x"], pad["y"]])
        offsets = np.array([(a, b) for a in np.linspace(-.2999, .2999, 241)
                            for b in np.linspace(-.0249, .0249, 21)])
        xy = center + offsets[:, :1]*u + offsets[:, 1:]*v
        xy = np.vstack([original, xy])
        rel = xy - center
        axial, lateral = rel @ u, rel @ v
        drill_inside = (np.abs(axial) <= .3-1e-7) & (np.abs(lateral) <= .025-1e-7)
        blocked = unary_union([pgeom(p) for p in pads + other_pads if p["net"] != oldvia["net"]])
        gaps = shapely.distance(shapely.points(xy), blocked) - args.land/2
        for fv in fixed_vias:
            if fv["net"] != oldvia["net"]:
                gap = np.linalg.norm(xy - np.array([fv["x"], fv["y"]]), axis=1) - (args.land + fv["diameter"])/2
                gaps = np.minimum(gaps, gap)
        allowed = np.where(drill_inside & (gaps >= .15+safety))[0]
        points = xy[allowed]
        movement = np.linalg.norm(points-original, axis=1)
        arrays.append(points)
        # Prioritize keeping unchanged endpoints, then minimum displacement.
        costs.append(movement + (movement > 1e-7)*10)
        info.append(dict(pad=n, domain_count=len(points), old_via_legal=bool(0 in allowed),
                         maximum_individual_gap_mm=float(np.max(gaps[drill_inside]))))
    edges = {}
    neighbors = [[] for _ in arrays]
    impossible = []
    for i, a in enumerate(arrays):
        if not len(a):
            continue
        bounds_a = box(*[float(a[:, 0].min()), float(a[:, 1].min()), float(a[:, 0].max()), float(a[:, 1].max())])
        for j in range(i+1, len(arrays)):
            b = arrays[j]
            if not len(b):
                continue
            bounds_b = box(*[float(b[:, 0].min()), float(b[:, 1].min()), float(b[:, 0].max()), float(b[:, 1].max())])
            if bounds_a.distance(bounds_b) >= minimum_center:
                continue
            compatible = cdist(a, b) >= minimum_center
            if compatible.all():
                continue
            edges[i, j] = compatible
            neighbors[i].append(j)
            neighbors[j].append(i)
            if not compatible.any():
                impossible.append([qids[i], qids[j]])
    visits = 0
    def propagate(active):
        pending = [(a, b) for a, b in edges for a, b in ((a,b), (b,a))]
        while pending:
            a, b = pending.pop()
            ia, ib = np.flatnonzero(active[a]), np.flatnonzero(active[b])
            if not len(ia) or not len(ib):
                return False
            matrix = edges[min(a,b), max(a,b)]
            if a > b:
                matrix = matrix.T
            support = matrix[np.ix_(ia,ib)].any(axis=1)
            removed = ia[~support]
            if len(removed):
                active[a][removed] = False
                if not active[a].any():
                    return False
                pending.extend((neighbor, a) for neighbor in neighbors[a] if neighbor != b)
        return True
    def solve(active):
        nonlocal visits
        visits += 1
        if visits > 100000:
            return None
        if not propagate(active):
            return None
        remaining = [i for i in range(len(active)) if active[i].sum() > 1]
        if not remaining:
            return [int(np.flatnonzero(d)[0]) for d in active]
        # Most-constrained variable plus forward checking solves short neighbor
        # chains without arbitrarily truncating the feasible via domains.
        n = min(remaining, key=lambda i:(active[i].sum(),-len(neighbors[i])))
        for selected in sorted(np.flatnonzero(active[n]), key=lambda i:costs[n][i]):
            trial = [a.copy() for a in active]
            trial[n][:] = False
            trial[n][selected] = True
            found = solve(trial)
            if found is not None:
                return found
        return None
    active = [np.ones(len(a), dtype=bool) for a in arrays]
    choice = None if any(not len(a) for a in arrays) or impossible else solve(active)
    result = dict(status="offline placement only; local routing/surfaces/native validation pending",
                  source_candidate_sha256=hashlib.sha256(source_bytes).hexdigest(),
                  via_land_mm=args.land, via_drill_mm=.2, required_land_gap_mm=.15,
                  required_drill_gap_mm=.254, numerical_guard_mm=safety,
                  domains=info, neighbor_edges=[[qids[a],qids[b]] for a,b in edges],
                  discretely_impossible_pairs=impossible, visited_nodes=visits,
                  joint_solution_found=choice is not None)
    if choice is not None:
        new_vias = []
        changed = []
        for n, old, options, selected in zip(qids, old_qvias, arrays, choice):
            xy = options[selected]
            nv = deepcopy(old)
            pad = next(p for p in pads if int(p["pin"])==n)
            theta = math.radians(pad["rotation"])
            rel = xy - np.array([pad["x"],pad["y"]])
            nv.update(x=float(xy[0]), y=float(xy[1]), diameter=args.land, hole=.2,
                      pad_axis_offset_mm=float(rel @ np.array([math.cos(theta),math.sin(theta)])),
                      pad_lateral_offset_mm=float(rel @ np.array([-math.sin(theta),math.cos(theta)])),
                      via_in_pad=True, drill_fully_in_original_pad=True)
            move = math.dist([old["x"],old["y"]],xy)
            changed.append(dict(pad=n, old_xy=[old["x"],old["y"]], new_xy=list(xy), movement_mm=move))
            new_vias.append(nv)
        rows = []
        for via in new_vias:
            number = int(via["label"].split("-")[1])
            pad = next(p for p in pads if int(p["pin"])==number)
            g = pgeom(pad)
            point = Point(via["x"],via["y"])
            drill_gap = point.distance(g.boundary)-.1
            pad_gap = min(point.distance(pgeom(p))-args.land/2 for p in pads+other_pads if p["net"]!=via["net"])
            via_gap = min(math.dist([via["x"],via["y"]],[v["x"],v["y"]])-(args.land+v["diameter"])/2 for v in new_vias+fixed_vias if v["net"]!=via["net"])
            hole_gap = min(math.dist([via["x"],via["y"]],[v["x"],v["y"]])-(.2+v["hole"])/2 for v in new_vias+fixed_vias if v["label"]!=via["label"])
            rows.append(dict(pad=number, drill_containment_margin_mm=drill_gap, foreign_pad_gap_mm=pad_gap,
                             foreign_via_gap_mm=via_gap, hole_gap_mm=hole_gap,
                             passed=g.covers(point) and drill_gap>=-1e-8 and pad_gap>=.15 and via_gap>=.15 and hole_gap>=.254))
        result.update(qd_pads=pads, qd_vias=new_vias, via_movements=changed, checks=rows,
                      all_static_checks_passed=all(r["passed"] for r in rows),
                      minimum_foreign_pad_gap_mm=min(r["foreign_pad_gap_mm"] for r in rows),
                      minimum_foreign_via_gap_mm=min(r["foreign_via_gap_mm"] for r in rows),
                      minimum_hole_gap_mm=min(r["hole_gap_mm"] for r in rows),
                      maximum_via_movement_mm=max(r["movement_mm"] for r in changed),
                      preserved_via_xy_count=sum(r["movement_mm"]<1e-8 for r in changed))
    suffix=f"{args.land:.2f}".replace(".","p")
    output=HERE/f"aligned_qd_vias_land_{suffix}_candidate.json"
    output.write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ("domains","qd_pads","qd_vias","checks","via_movements")},indent=2))
    print(str(output))


if __name__=="__main__":
    main()
