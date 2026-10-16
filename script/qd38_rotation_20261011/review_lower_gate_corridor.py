"""Read-only local R12/R28 lowering feasibility from the corridor placement."""
import json,hashlib,math
from pathlib import Path
import numpy as np
from shapely.affinity import translate
from shapely.geometry import Point,Polygon,box
from shapely.ops import unary_union
from build_rotated_placement import pg

HERE=Path(__file__).resolve().parent
source=HERE/"placement_corridor_candidate.json";raw=source.read_bytes();plan=json.loads(raw)
board=Polygon(plan["board_outline"]).buffer(-.2);cavity=box(7.6,39.85,11.9,45.15)
disks={s["ref"]:Point(s["x"],s["y"]).buffer(1.175,quad_segs=96) for s in plan["smp"]}
groups=[]
for group,sign in ((12,1),(28,-1)):
 refs={f"R{group}",f"C{group}"};rp=[p for p in plan["physical_pads"] if p["ref"]==f"R{group}"];cp=[p for p in plan["physical_pads"] if p["ref"]==f"C{group}"]
 rb=Polygon(next(b["outline"] for b in plan["passive_bodies"] if b["ref"]==f"R{group}"));cb=Polygon(next(b["outline"] for b in plan["passive_bodies"] if b["ref"]==f"C{group}"))
 fixed=[p for p in plan["physical_pads"] if p["ref"] not in refs and p["layer"] in (32,74)]
 fixed_copper=unary_union([pg(p) for p in fixed]+[Point(v["x"],v["y"]).buffer(v["diameter"]/2,quad_segs=64) for v in plan["vias"] if v["label"]!=f"R{group}-2"]+[cavity])
 fixed_bodies=unary_union([Polygon(b["outline"]) for b in plan["passive_bodies"] if b["ref"] not in refs])
 fixed_drills=unary_union([Point(p["x"],p["y"]).buffer(p["hole"]/2,quad_segs=64) for p in fixed if p["hole"]]+[pg(p) for p in fixed if p["ref"]=="Q1"]+[cavity])
 legal=[]
 for rdy in (-.5,-.6,-.7):
  rs=[translate(pg(p),0,rdy) for p in rp];rbody=translate(rb,0,rdy)
  for cdx in np.arange(0,1.501,.05)*sign:
   for cdy in np.arange(-.8,.001,.05):
    cs=[translate(pg(p),float(cdx),float(cdy)) for p in cp];cbody=translate(cb,float(cdx),float(cdy))
    copper=unary_union(cs+rs)
    if not board.covers(copper):continue
    pair_gap=min(g.distance(h) for g in cs for h in rs)
    if pair_gap<.15-1e-8:continue
    gap=copper.distance(fixed_copper)
    if gap<.155-1e-8:continue
    bgap=min(cbody.distance(rbody),unary_union([cbody,rbody]).distance(fixed_bodies));dgap=unary_union([cbody,rbody]).distance(fixed_drills)
    if min(bgap,dgap)<.254-1e-8:continue
    ringgap=min(g.distance(disk) for pad,g in zip(cp+rp,cs+rs) for ref,disk in disks.items() if pad["net"]!=f"S{int(ref[3:]):02}")
    if ringgap<.15-1e-8:continue
    legal.append(dict(R_delta=[0,rdy],C_delta=[float(cdx),float(cdy)],cost=abs(rdy)+math.hypot(cdx,cdy),pad_fixed_gap_mm=gap,pair_pad_gap_mm=pair_gap,
        body_gap_mm=bgap,body_drill_QD_gap_mm=dgap,foreign_SMP_disk_gap_mm=ringgap,R_hull_bounds_mm=list(unary_union(rs).convex_hull.bounds)))
 legal.sort(key=lambda r:(abs(r["R_delta"][1]+.5),r["cost"],-r["pad_fixed_gap_mm"]))
 groups.append(dict(group=group,legal_count=len(legal),best=legal[:8]));print(json.dumps(groups[-1],indent=2),flush=True)
report=dict(source_sha256=hashlib.sha256(raw).hexdigest(),groups=groups,native_changed=False,status="READ_ONLY_LOCAL_PLACEMENT_FEASIBILITY")
(HERE/"lower_gate_corridor_review.json").write_text(json.dumps(report,indent=2));assert source.read_bytes()==raw
