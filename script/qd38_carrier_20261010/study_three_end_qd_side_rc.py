"""Read-only R/C collision projection for the proposed 3-3-2-2-3-3 SMP layout.

This is a placement study only. No native design or candidate routing is edited.
Through-hole envelopes versus Bottom component contours are conservative 2D
checks, not a substitute for a final 3D assembly interference calculation.
"""
from pathlib import Path
import hashlib
import json
from collections import Counter

from shapely.geometry import Point, Polygon
from audit_source_model_transforms import inspect
from route_circuit import pgeom

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / "QSTL_QD4_2SET_38PAD"


def main():
    pcb = DEST / "QSTL_QD4_2SET_38PAD.PcbDoc"
    native_sha = hashlib.sha256(pcb.read_bytes()).hexdigest()
    plan_path = DEST / "full_copper_candidate.json"
    candidate_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    plan = json.loads(plan_path.read_text())
    sch = json.loads((DEST / "schematic_validation.json").read_text())
    native = inspect(pcb)
    uid = {value: ref for ref, value in sch["components"].items()}
    bodies = []
    for body in native["bodies"]:
        ref = uid.get(body["component_fields"].get("SOURCEUNIQUEID"), body["component"])
        if ref and ref.startswith(("R", "C")):
            bodies.append((ref, Polygon(body["outline_mm"])))
    rc_pads = [(p, pgeom(p)) for p in plan["physical_pads"] if (p["ref"] or "").startswith(("R", "C"))]
    assert len(bodies) == 32 and len(rc_pads) == 64
    proposed = []
    for row, y in enumerate((27.5, 33.5, 39.5, 45.5, 51.5, 57.5), 1):
        xs = (3.75, 15.75) if row in (3, 4) else (3.75, 9.75, 15.75)
        for col, x in enumerate(xs, 1):
            proposed.append(dict(label=f"ROW{row}_SMP{col}", row=row, x=x, y=y))
    offsets = [("1", 0, 0), ("2", -1.27, 1.27), ("3", -1.27, -1.27),
               ("4", 1.27, -1.27), ("5", 1.27, 1.27)]
    overlaps, land_conflicts = [], []
    for connector in proposed:
        for pin, dx, dy in offsets:
            x, y = connector["x"] + dx, connector["y"] + dy
            center = Point(x, y)
            drill = center.buffer(.375, quad_segs=128)
            for ref, body in bodies:
                area = drill.intersection(body).area
                if area > 1e-8:
                    overlaps.append(dict(connector=connector["label"], pin=pin,
                        pin_xy_mm=[x, y], RC=ref, drill_body_projection_overlap_mm2=area))
            for pad, copper in rc_pads:
                gap = center.distance(copper) - .5
                if gap < .15 - 1e-5:
                    land_conflicts.append(dict(connector=connector["label"], pin=pin,
                        pin_xy_mm=[x, y], RC_pad=pad["ref"] + "." + pad["pin"],
                        pin_net="GND" if pin != "1" else "RF_SIGNAL_TO_BE_ASSIGNED",
                        RC_net=pad["net"], center_to_pad_minus_land_radius_mm=gap,
                        copper_overlap=gap < 0))
    body_refs = sorted({r["RC"] for r in overlaps})
    pad_refs = sorted({r["RC_pad"].split(".")[0] for r in land_conflicts})
    report = dict(status="PROPOSED_SMP_PLACEMENT_READ_ONLY_RC_PROJECTION_STUDY",
        native_sha256=native_sha, candidate_sha256=candidate_sha,
        proposed_rows=[3, 3, 2, 2, 3, 3], proposed_connectors=proposed,
        footprint=dict(pads=5, through_drill_mm=.75, land_mm=1.0, corner_offset_mm=1.27),
        current_RC_body_projection_count=32,
        drill_body_overlap_count=len(overlaps), affected_RC_bodies=body_refs,
        drill_body_overlaps=overlaps,
        pad_clearance_failure_count=len(land_conflicts), affected_RC_pad_components=pad_refs,
        pad_clearance_failures=land_conflicts,
        conclusion="Proposed SMP coordinates cannot retain all existing R/C placements. R/C relocation, via relocation and routing changes require a new complete clearance and connectivity review.",
        limitation="Drill envelopes versus saved Bottom body projections are conservative 2D checks. No full 3D B-rep interference result is claimed.")
    assert hashlib.sha256(pcb.read_bytes()).hexdigest() == native_sha
    assert hashlib.sha256(plan_path.read_bytes()).hexdigest() == candidate_sha
    (H / "three_end_qd_side_rc_study.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("native_sha256", "drill_body_overlap_count", "affected_RC_bodies", "pad_clearance_failure_count", "affected_RC_pad_components", "conclusion")}, indent=2))
    print("DRILL_BODY_OVERLAPS", overlaps)


if __name__ == "__main__":
    main()
