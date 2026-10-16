"""Check actual L5/Bottom shields and nonempty symmetric equal-angle SMP rings."""
from collections import Counter
import math

import numpy as np
from scipy.spatial import cKDTree

TOL=1e-5
ANGLE_TOL=.002


def inspect_smp_rings(plan, pads, vias):
    failures=[];rings=[]
    shield=[v for v in vias if v["net"]=="GND"]
    if not shield:
        return dict(passed=False,failures=[dict(kind="no_saved_shield_vias")],rings=[])
    for i,v in enumerate(shield):
        if (v["low"],v["high"])!=(5,32) or abs(v["diameter"]-.25)>TOL or abs(v["hole"]-.10)>TOL:
            failures.append(dict(kind="shield_span_or_size",index=i,via=v))
    xy=np.array([[v["x"],v["y"]] for v in shield]);tree=cKDTree(xy)
    min_pitch=float(tree.query(xy,k=2)[0][:,1].min()) if len(shield)>1 else None
    if min_pitch is None or min_pitch<.40-TOL:failures.append(dict(kind="shield_minimum_pitch",actual_mm=min_pitch,required_mm=.40))
    active={p["ref"]:p for p in pads if (p["ref"] or "").startswith("SMP") and p["pin"]=="1"}
    requested={s["ref"]:s for s in plan["smp"]}
    if set(active)!=set(requested) or len(active)!=16:failures.append(dict(kind="active_SMP_ring_membership",saved=sorted(active),planned=sorted(requested)))
    ring_labels=Counter(v["label"] for v in plan["shield_vias"] if v["label"].endswith("-ring"))
    unexpected=set(ring_labels)-{ref+"-ring" for ref in active}
    if unexpected:failures.append(dict(kind="unknown_ring_label",labels=sorted(unexpected)))
    declared=plan.get("surface_validation",{}).get("smp_ring_counts",{})
    for ref,pad in active.items():
        if ref not in requested:continue
        smp=requested[ref]
        if "escape_angle_deg" not in smp:
            failures.append(dict(kind="SMP_escape_axis_missing",component=ref));continue
        axis=float(smp["escape_angle_deg"])
        planned=[v for v in plan["shield_vias"] if v["label"]==ref+"-ring"]
        actual=[];indices=[]
        for candidate in planned:
            distance,index=tree.query([candidate["x"],candidate["y"]])
            if distance>TOL:
                failures.append(dict(kind="planned_ring_via_not_saved",component=ref,nearest_mm=float(distance)));continue
            actual.append(shield[int(index)]);indices.append(int(index))
        count=len(actual)
        if not count:failures.append(dict(kind="missing_SMP_ring",component=ref))
        if len(set(indices))!=len(indices):failures.append(dict(kind="duplicate_ring_via_match",component=ref))
        if declared.get(ref)!=len(planned):failures.append(dict(kind="SMP_ring_count_metadata_mismatch",component=ref,declared=declared.get(ref),planned=len(planned)))
        grid=[];maximum_radius_error=0.;maximum_grid_error=0.
        for via in actual:
            dx,dy=via["x"]-pad["x"],via["y"]-pad["y"]
            radius=math.hypot(dx,dy);angle=math.degrees(math.atan2(dy,dx))
            offset=(angle-axis)%360;k=int(round(offset/22.5))%16
            grid_error=abs((offset-22.5*k+180)%360-180)
            maximum_radius_error=max(maximum_radius_error,abs(radius-1.05));maximum_grid_error=max(maximum_grid_error,grid_error)
            grid.append(k)
        valid=set(range(3,14))
        symmetric=len(set(grid))==len(grid) and all((-k)%16 in set(grid) for k in grid)
        if maximum_radius_error>TOL:failures.append(dict(kind="SMP_ring_radius",component=ref,maximum_error_mm=maximum_radius_error))
        if maximum_grid_error>ANGLE_TOL:failures.append(dict(kind="SMP_ring_unequal_angle_grid",component=ref,maximum_error_deg=maximum_grid_error))
        if set(grid)-valid:failures.append(dict(kind="SMP_ring_RF_escape_blocked",component=ref,grid_indices=grid))
        if not symmetric:failures.append(dict(kind="SMP_ring_escape_not_symmetric",component=ref,grid_indices=grid))
        rings.append(dict(component=ref,count=count,planned_count=len(planned),centre_mm=[pad["x"],pad["y"]],
                          axis_deg=axis,radius_mm=1.05,grid_deg=22.5,grid_indices=sorted(grid),symmetric=symmetric,
                          maximum_radius_error_mm=maximum_radius_error,maximum_grid_error_deg=maximum_grid_error,
                          minimum_required_escape_half_angle_deg=45,nonempty=count>0))
    return dict(passed=not failures,failures=failures,rings=rings,shield_via_count=len(shield),minimum_shield_pitch_mm=min_pitch,
                shield_span=[5,32],shield_land_mm=.25,shield_hole_mm=.10,
                note="Every active SMP requires a nonempty ring. Saved vias must match planned ring labels, a 1.05 mm radius and a 22.5-degree grid mirrored about the planned RF escape axis. Missing rings are failures.")
