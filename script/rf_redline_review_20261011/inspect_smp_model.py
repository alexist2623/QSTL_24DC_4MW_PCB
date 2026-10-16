"""Read-only STEP geometry check for the RF redline placement review."""
from pathlib import Path
import hashlib
import json
import math

from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopLoc import TopLoc_Location
from OCP.gp import gp_Pnt, gp_Vec, gp_Trsf, gp_Ax1, gp_Dir

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "QSTL_QD4_2SET_38PAD/SMP-FS-SBPCT.stp"
AUDIT = ROOT / "script/qd38_pad_alignment_20261011/saved_revision_models.json"


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    lo, hi = box.CornerMin(), box.CornerMax()
    return [lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z()]


def move(shape, vector):
    transform = gp_Trsf()
    transform.SetTranslation(gp_Vec(*vector))
    return BRepBuilderAPI_Transform(shape, transform, True).Shape()


def volume(shape):
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, props)
    return props.Mass()


def main():
    audit = json.loads(AUDIT.read_text())
    sources = [m for m in audit["models"] if m["component"].startswith("SMP")]
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert all(m["embedded_step_sha256"] == [source_hash] for m in sources)
    native = Path(audit["native_file"])
    assert hashlib.sha256(native.read_bytes()).hexdigest() == audit["native_sha256"]
    reader = STEPControl_Reader()
    assert int(reader.ReadFile(str(SOURCE))) == 1
    reader.TransferRoots()
    shape = reader.OneShape()
    raw_bounds = bounds(shape)
    transform = gp_Trsf()
    transform.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2)
    rotated = BRepBuilderAPI_Transform(shape, transform, True).Shape()
    rotated_bounds = bounds(rotated)
    pitch_checks = []
    for pitch in [5.0, 5.25, 5.4, 5.45, 5.5, 5.55, 5.6, 5.75, 6.0]:
        other = move(rotated, (0, pitch, 0))
        common = BRepAlgoAPI_Common(rotated, other).Shape()
        distance = BRepExtrema_DistShapeShape(rotated, other)
        distance.Perform()
        pitch_checks.append(dict(pitch_mm=pitch, common_volume_mm3=volume(common), minimum_distance_mm=distance.Value()))
    diagonal_checks = []
    for dx, dy in [(4, 4), (4, 4.25), (4, 3.75), (4, 4.5), (6, 0)]:
        other = move(rotated, (dx, dy, 0))
        common = BRepAlgoAPI_Common(rotated, other).Shape()
        distance = BRepExtrema_DistShapeShape(rotated, other)
        distance.Perform()
        diagonal_checks.append(dict(dx_mm=dx, dy_mm=dy, centre_distance_mm=math.hypot(dx,dy),
                                    circular_envelope_gap_mm=math.hypot(dx,dy)-5.5,
                                    common_volume_mm3=volume(common), minimum_distance_mm=distance.Value()))
    BRepMesh_IncrementalMesh(rotated, 0.001, False, 0.02, True).Perform()
    radial_samples = []
    explorer = TopExp_Explorer(rotated, TopAbs_FACE)
    while explorer.More():
        location = TopLoc_Location()
        triangle = BRep_Tool.Triangulation_s(TopoDS.Face(explorer.Current()), location)
        if triangle is not None:
            for index in range(1, triangle.NbNodes()+1):
                point = triangle.Node(index).Transformed(location.Transformation())
                radial_samples.append([math.hypot(point.X(), point.Y()), point.X(), point.Y(), point.Z()])
        explorer.Next()
    snapshot = json.loads((ROOT / "script/qd38_pad_alignment_20261011/saved_revision_snapshot.json").read_text())
    body = next(b for b in snapshot["bodies"] if b["component"] == "SMP02")
    xs = [p[0] for p in body["points"]]
    ys = [p[1] for p in body["points"]]
    report = dict(
        scope="Read-only saved embedded SMP model geometry; mechanical tolerance and mating-plug access are not certified.",
        source=str(SOURCE), step_sha256=source_hash,
        saved_native_hash_matches=True, all_16_native_models_match_step=True,
        valid=BRepCheck_Analyzer(shape).IsValid(), raw_model_bounds_mm=raw_bounds,
        native_rotation_xyz_deg=sources[0]["rotation_xyz_deg"],
        rotated_local_bounds_mm=rotated_bounds,
        actual_xy_projection_span_mm=[rotated_bounds[3]-rotated_bounds[0], rotated_bounds[4]-rotated_bounds[1]],
        native_body_outline_projection_span_mm=[max(xs)-min(xs), max(ys)-min(ys)],
        translated_left_x_bounds_mm=[2.75+rotated_bounds[0], 2.75+rotated_bounds[3]],
        translated_right_x_bounds_mm=[16.75+rotated_bounds[0], 16.75+rotated_bounds[3]],
        pitch_checks=pitch_checks,
        diagonal_checks=diagonal_checks,
        maximum_meshed_xy_radius_mm=max(radial_samples),
        projection_note="Dense STEP mesh radius check and exact STEP pair-intersection checks assess circular packing; mesh containment is approximate at 0.001 mm linear deflection.",
        manufacturing_note="Zero nominal body gap is not an approved assembly spacing. Cable plug and installation tool envelopes are absent from this STEP.",
    )
    (HERE / "smp_embedded_model_geometry_review.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
