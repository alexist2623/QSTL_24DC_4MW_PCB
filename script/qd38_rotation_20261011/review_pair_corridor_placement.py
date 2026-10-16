"""Read-only search for local R11/C11 and R30/C30 corridor-opening moves."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union

from build_rotated_placement import pg

HERE=Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate",type=Path,default=HERE/"dc_routed_candidate.json")
    args=parser.parse_args()
    data=args.candidate.read_bytes();plan=json.loads(data)
    board=Polygon(plan["board_outline"])
    cavity=box(7.6,39.85,11.9,45.15)
    result=[]
    for group,side in ((11,"left"),(30,"right")):
        refs={f"R{group:02}",f"C{group:02}"}
        components=[c for c in plan["components"] if c["ref"] in refs]
        original_pads=[p for p in plan["physical_pads"] if p["ref"] in refs]
        pad_shapes=[pg(p) for p in original_pads]
        original_bodies=[b for b in plan["passive_bodies"] if b["ref"] in refs]
        body_shapes=[Polygon(b["outline"]) for b in original_bodies]
        pivot=next([c["x"],c["y"]] for c in components if c["ref"]==f"C{group:02}")
        fixed_pads=[p for p in plan["physical_pads"] if p["ref"] not in refs and p["layer"] in (32,74)]
        fixed_vias=[v for v in plan["vias"] if v["label"]!=f"R{group:02}-2"]
        fixed_copper=unary_union([pg(p) for p in fixed_pads]+[Point(v["x"],v["y"]).buffer(v["diameter"]/2,quad_segs=48) for v in fixed_vias]+[cavity])
        fixed_bodies=unary_union([Polygon(b["outline"]) for b in plan["passive_bodies"] if b["ref"] not in refs])
        fixed_drills=unary_union([Point(p["x"],p["y"]).buffer(p["hole"]/2,quad_segs=48) for p in fixed_pads if p["hole"]]+[cavity]+[pg(p) for p in fixed_pads if p["ref"]=="Q1"])
        legal=[];considered=0
        for angle in (0,90,180,270):
            rotated_pads=[rotate(g,angle,origin=pivot) for g in pad_shapes]
            rotated_bodies=[rotate(g,angle,origin=pivot) for g in body_shapes]
            for dx in np.arange(-3,3.001,.1):
                for dy in np.arange(-3,3.001,.1):
                    considered+=1
                    transform=lambda g:translate(g,float(dx),float(dy))
                    pads=[transform(g) for g in rotated_pads]
                    resistor=unary_union([g for p,g in zip(original_pads,pads) if p["ref"]==f"R{group:02}"]).convex_hull
                    # Copper has a .20 board edge margin, and DC observes
                    # .15 clearance outside the full resistor envelope.
                    corridor=resistor.bounds[0]-.35 if side=="left" else 19.5-resistor.bounds[2]-.35
                    if corridor<1.-1e-8:continue
                    copper=unary_union(pads)
                    if not board.buffer(-.2).covers(copper):continue
                    copper_gap=copper.distance(fixed_copper)
                    if copper_gap<.155-1e-8:continue
                    bodies=[transform(g) for g in rotated_bodies]
                    bodies_union=unary_union(bodies)
                    body_gap=bodies_union.distance(fixed_bodies)
                    body_drill_gap=bodies_union.distance(fixed_drills)
                    if min(body_gap,body_drill_gap)<.254-1e-8:continue
                    moved=[]
                    for comp in components:
                        xy=transform(rotate(Point(comp["x"],comp["y"]),angle,origin=pivot))
                        moved.append(dict(ref=comp["ref"],x=xy.x,y=xy.y,rotation=(comp["rotation"]+angle)%360,displacement_mm=math.dist([comp["x"],comp["y"]],[xy.x,xy.y])))
                    legal.append(dict(angle_delta_deg=angle,translation_mm=[float(dx),float(dy)],pivot_mm=pivot,
                        components=moved,maximum_component_displacement_mm=max(c["displacement_mm"] for c in moved),
                        R_hull_bounds_mm=list(resistor.bounds),local_edge_corridor_after_clearances_mm=corridor,
                        minimum_pad_to_fixed_copper_mm=copper_gap,minimum_body_to_other_body_mm=body_gap,
                        minimum_body_to_drill_or_QD_mm=body_drill_gap,pair_internal_body_gap_mm=bodies[0].distance(bodies[1])))
        legal.sort(key=lambda r:(r["maximum_component_displacement_mm"],abs(r["angle_delta_deg"]),-r["minimum_pad_to_fixed_copper_mm"]))
        top=legal[:5]
        translations=[v for v in legal if v["angle_delta_deg"]==0][:3]
        result.append(dict(group=group,side=side,considered=considered,legal_placements=len(legal),best=top,best_translations=translations))
        print(json.dumps(result[-1],indent=2),flush=True)
    report=dict(status="READ_ONLY_PLACEMENT_FEASIBILITY",source=str(args.candidate.resolve()),source_sha256=hashlib.sha256(data).hexdigest(),
        scope="Rigid R/C pair transformations; fixed SMP/QD and all other parts preserved. Copper >=.155, source passive body outlines/drills >=.254. Local edge corridor includes .20 edge and .15 resistor clearance. No routing or 3D solid collision certification.",
        groups=result,native_changed=False)
    (HERE/"pair_corridor_placement_review.json").write_text(json.dumps(report,indent=2))
    assert args.candidate.read_bytes()==data


if __name__=="__main__":main()
