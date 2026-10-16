"""Read-only R30 adjustment after a +90-degree SMP30-centred pair rotation."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from shapely.affinity import rotate,translate
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from build_rotated_placement import pg

HERE=Path(__file__).resolve().parent
path=HERE/"dc_routed_candidate.json"
raw=path.read_bytes();plan=json.loads(raw)
refs={"R30","C30"};pivot=(15.75,42.5)
cp=[p for p in plan["physical_pads"] if p["ref"]=="C30"]
rp=[p for p in plan["physical_pads"] if p["ref"]=="R30"]
cg=[rotate(pg(p),90,origin=pivot) for p in cp]
rg=[rotate(pg(p),90,origin=pivot) for p in rp]
cb=rotate(Polygon(next(b["outline"] for b in plan["passive_bodies"] if b["ref"]=="C30")),90,origin=pivot)
rb=rotate(Polygon(next(b["outline"] for b in plan["passive_bodies"] if b["ref"]=="R30")),90,origin=pivot)
fixed=[p for p in plan["physical_pads"] if p["ref"] not in refs and p["layer"] in (32,74)]
cavity=box(7.6,39.85,11.9,45.15)
fixed_copper=unary_union([pg(p) for p in fixed]+[Point(v["x"],v["y"]).buffer(v["diameter"]/2,quad_segs=64) for v in plan["vias"] if v["label"]!="R30-2"]+[cavity])
fixed_bodies=unary_union([Polygon(b["outline"]) for b in plan["passive_bodies"] if b["ref"] not in refs])
fixed_drills=unary_union([Point(p["x"],p["y"]).buffer(p["hole"]/2,quad_segs=64) for p in fixed if p["hole"]]+[pg(p) for p in fixed if p["ref"]=="Q1"]+[cavity])
board=Polygon(plan["board_outline"]).buffer(-.2)
disks={s["ref"]:Point(s["x"],s["y"]).buffer(1.175,quad_segs=96) for s in plan["smp"]}
legal=[]
for cdx in (0.,.1,-.1,.2,-.2):
 for cdy in (0.,.1,-.1,.2,-.2):
  cs=[translate(g,cdx,cdy) for g in cg];cbody=translate(cb,cdx,cdy)
  for dx in np.arange(-.5,2.501,.1):
   for dy in np.arange(-.5,1.501,.1):
    rs=[translate(g,float(dx),float(dy)) for g in rg];rbody=translate(rb,float(dx),float(dy))
    copper=unary_union(cs+rs)
    if not board.covers(copper):continue
    if min(g.distance(h) for g in cs for h in rs)<.155-1e-8:continue
    cgap=copper.distance(fixed_copper)
    if cgap<.155-1e-8:continue
    bgap=min(cbody.distance(rbody),unary_union([cbody,rbody]).distance(fixed_bodies))
    dgap=unary_union([cbody,rbody]).distance(fixed_drills)
    if min(bgap,dgap)<.254-1e-8:continue
    ringgap=min(g.distance(disk) for pad,g in zip(cp+rp,cs+rs) for ref,disk in disks.items() if pad["net"]!=f"S{int(ref[3:]):02}")
    if ringgap<.15-1e-8:continue
    rhull=unary_union(rs).convex_hull;corridor=19.5-rhull.bounds[2]-.35
    if corridor<1.-1e-8:continue
    centers=[]
    for ref,ddx,ddy in (("C30",cdx,cdy),("R30",dx,dy)):
     comp=next(c for c in plan["components"] if c["ref"]==ref)
     xy=translate(rotate(Point(comp["x"],comp["y"]),90,origin=pivot),float(ddx),float(ddy))
     centers.append(dict(ref=ref,x=xy.x,y=xy.y,rotation=(comp["rotation"]+90)%360))
    cp1=cs[0].centroid
    legal.append(dict(components=centers,delta_after_90_SMP_rotation={"C30":[cdx,cdy],"R30":[float(dx),float(dy)]},
        adjustment_cost_mm=math.hypot(dx,dy)+math.hypot(cdx,cdy),minimum_pad_fixed_copper_gap_mm=cgap,minimum_body_gap_mm=bgap,
        minimum_body_drill_QD_gap_mm=dgap,foreign_SMP_radius1p175_disk_gap_mm=ringgap,right_edge_corridor_mm=corridor,
        capacitor_pin1=[cp1.x,cp1.y],SMP_escape_angle_deg=math.degrees(math.atan2(cp1.y-pivot[1],cp1.x-pivot[0]))%360,
        R_hull_bounds_mm=list(rhull.bounds)))
legal.sort(key=lambda r:(r["adjustment_cost_mm"],-r["minimum_pad_fixed_copper_gap_mm"]))
report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),legal_count=len(legal),best=legal[:8],
    status="READ_ONLY_PLACEMENT_PROPOSALS",native_changed=False,limitation="Pad/drill and source body-outline placement checks; routing and native 3D solid verification remain required.")
(HERE/"r30_upper_escape_review.json").write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
assert path.read_bytes()==raw
