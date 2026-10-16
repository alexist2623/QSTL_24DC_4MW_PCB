"""Prepare a guarded native revision of the existing 50-component carrier.

This generator does not launch Altium, edit a native document, or save the PCB.
The candidate and its independent copper audit must already be complete. Reopen
the frozen saved PCB before executing the generated DelphiScript; generation
checks its SHA256, while the script checks the live component/count fingerprint.

Signal arcs use the saved-reader schema, with angles counterclockwise in degrees:
    {net, layer, cx, cy, radius, start_angle, end_angle, width}

The existing J1 object, mounting pads, Mechanical 1 outline, board definition,
layer stack and rules are retained. All other component/copper/mask geometry is
rebuilt from the explicitly supplied audited plan. The result remains unsaved
until a separate native review/save/reopen/DRC procedure is run.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from shapely.geometry import box, shape
from shapely.geometry.polygon import orient
from revision_invariants import assert_plan_contacts, via_groups
from audit_smp_rings import inspect_smp_rings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREVIOUS = ROOT / "script/qd38_carrier_20261010"
DEST = ROOT / "QSTL_QD4_2SET_38PAD"
TARGET = DEST / "QSTL_QD4_2SET_38PAD.PcbDoc"
FROZEN_SHA256 = "f8356dd694810d2318a51e99544ab2345f8b9996de80e9ddc4456bbc6a14c632"
UNIT = 2.54e-6
LAYERS = {
    1: "eTopLayer", 2: "eMidLayer1", 3: "eMidLayer2",
    4: "eMidLayer3", 5: "eMidLayer4", 32: "eBottomLayer",
    37: "eTopSolder", 38: "eBottomSolder", 59: "eMechanical3",
    74: "eMultiLayer",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def number(value) -> str:
    value = float(value)
    assert math.isfinite(value), "Non-finite native geometry"
    result = format(value, ".12f").rstrip("0").rstrip(".")
    return "0" if result in ("", "-0") else result


def quote(value) -> str:
    value = str(value)
    assert "\n" not in value and "\r" not in value
    return "'" + value.replace("'", "''") + "'"


def family(ref: str) -> str:
    return "SMP" if ref.startswith("SMP") else ref[0]


def layer(value) -> str:
    return LAYERS[int(value)]


def checked_inputs(candidate_path: Path, audit_path: Path, schematic_path: Path):
    assert sha(TARGET) == FROZEN_SHA256, "Native PCB differs from the frozen pre-revision board"
    candidate_hash = sha(candidate_path)
    plan, audit, schematic = map(read_json, (candidate_path, audit_path, schematic_path))
    assert audit.get("passed") is True, "Candidate audit failed"
    assert audit.get("candidate_sha256") == candidate_hash, "Candidate audit hash is stale"
    assert plan.get("routing_complete") is True, "Routing is not complete"
    assert plan["nets"] == schematic["nets"], "Schematic net membership differs from the plan"
    assert schematic["schematic_sha256"] == sha(DEST / "QSTL_QD4_2SET_38PAD.SchDoc"), "Saved schematic differs from validation"

    previous = read_json(PREVIOUS / "through_dc_saved_native_snapshot.json")
    assert previous["source_sha256"] == FROZEN_SHA256
    # The native snapshot is authoritative for retained objects and the runtime
    # fingerprint; the old plan file may already have been replaced by the caller.
    model_audit = read_json(PREVIOUS / "saved_model_validation.json")
    assert model_audit["passed"] and model_audit["native_sha256"] == FROZEN_SHA256
    models = {entry["component"]: entry for entry in model_audit["models"]}
    for ref in ("R02", "C02", "SMP02"):
        assert ref in models and len(models[ref]["embedded_step_sha256"]) == 1
    model_sources = {key: models[ref] for key, ref in (("R", "R02"), ("C", "C02"), ("SMP", "SMP02"))}
    for key, item in model_sources.items():
        expected = (90, 0) if key == "SMP" else (0, 0)
        assert tuple(item["rotation_xyz_deg"][:2]) == expected
        assert item["board_projection"] == (0 if key == "SMP" else 1)

    provenance = read_json(DEST / "copy_provenance.json")
    source_root = ROOT / "QSTL_24DC_4MW_PCB"
    assert all(sha(source_root / name) == expected for name, expected in provenance["source_sha256"].items()), "Original source was changed"
    components = {c["ref"]: c for c in plan["components"]}
    assert len(components) == len(plan["components"]) == 50
    assert set(components) == set(schematic["components"])
    assert set(components) == {c["designator"] for c in previous["components"]}
    assert len(plan["physical_pads"]) == 243
    assert len(plan["vias"]) == 76
    assert all((v["low"], v["high"]) == (1, 32) for v in plan["vias"])
    assert plan["shield_vias"] and all((v["low"], v["high"]) == (5, 32) for v in plan["shield_vias"])
    assert all(v["net"] == "GND" and abs(v["diameter"] - .25) < 1e-8 and abs(v["hole"] - .10) < 1e-8 for v in plan["shield_vias"])
    assert math.dist(plan["sample_center"], [9.75, 42.5]) < 1e-8
    assert math.dist(plan["cavity_mm"], [4.3, 5.3]) < 1e-8
    assert abs(plan["cavity_depth_mm"] - 1.2) < 1e-8
    assert abs((components["Q1"]["rotation"] % 360) - 90) < 1e-8
    smps = [c for c in plan["components"] if c["ref"].startswith("SMP")]
    rows = Counter(round(c["y"], 6) for c in smps)
    assert [rows[y] for y in sorted(rows)] == [3, 2, 2, 2, 2, 2, 3]
    assert rows[42.5] == 2
    assert len({p["pin"] for p in plan["physical_pads"] if p["ref"] == "Q1"}) == 38
    assert {int(row["qd_pad"]) for row in plan["pinmap"]} == set(range(1, 39))
    assert_plan_contacts(plan)
    via_groups(plan)
    ring_check=inspect_smp_rings(plan,plan['physical_pads'],plan['vias']+plan['shield_vias'])
    assert ring_check['passed'], ring_check['failures']

    # J1 and mounting geometry will not be recreated. Reject a candidate that
    # silently asks the generator to move those retained native primitives.
    old_components = {c["designator"]: c for c in previous["components"]}
    for key in ("x", "y", "rotation"):
        assert abs(components["J1"][key] - old_components["J1"][key]) < 1e-5
    assert components["J1"]["pattern"] == old_components["J1"]["pattern"]
    old_pads = {(p["component"], p["number"]): p for p in previous["pads"] if p["component"] in (None, "J1")}
    new_pads = {(p["ref"], p["pin"]): p for p in plan["physical_pads"] if p["ref"] in (None, "J1")}
    assert old_pads.keys() == new_pads.keys()
    for key, old in old_pads.items():
        new = new_pads[key]
        for nk, ok in (("x", "x"), ("y", "y"), ("sx", "size_x"), ("sy", "size_y"), ("hole", "hole"), ("rotation", "rotation")):
            assert abs(new[nk] - old[ok]) < 1e-5, f"Retained pad changed: {key} {nk}"
        assert new["layer"] == old["layer"]

    net_names = set(plan["nets"])
    assert "GND" in net_names
    for sequence in (plan["tracks"], plan["arcs"], plan["vias"], plan["shield_vias"]):
        assert all(item["net"] in net_names for item in sequence)
    assert plan["arcs"], "RF tangent arcs are required"
    for arc in plan["arcs"]:
        assert set(("net", "layer", "cx", "cy", "radius", "start_angle", "end_angle", "width")).issubset(arc)
        assert arc["layer"] == 32 and arc["net"].startswith(("MW", "S"))
        assert arc["radius"] > 0 and arc["width"] > 0
        assert 0 < (arc["end_angle"] - arc["start_angle"]) % 360 < 360
    for comp in plan["components"]:
        if family(comp["ref"]) in ("R", "C"):
            own = [p for p in plan["physical_pads"] if p["ref"] == comp["ref"]]
            assert len(own) == 2
            assert math.dist([comp["x"], comp["y"]], [sum(p[k] for p in own)/2 for k in ("x", "y")]) < 1e-5

    # Check the supplied (already audited) ground maps against the rotated
    # inner pad boundary. Surface generation and guard clearances stay separate.
    cx, cy = plan["sample_center"]
    ex, ey = (v + .4 for v in plan["cavity_mm"])
    excluded = box(cx-ex/2, cy-ey/2, cx+ex/2, cy+ey/2)
    assert set(map(int, plan["ground_regions"])) == {1, 2, 3, 4, 5, 32}
    assert set(map(int, plan["solder_openings"])) == {37, 38}
    for key, geo in plan["ground_regions"].items():
        geom = shape(geo)
        assert geom.is_valid
        area = geom.intersection(excluded).area
        assert area > 0 if int(key) == 1 else area < 1e-8
    for geo in plan["solder_openings"].values():
        assert shape(geo).is_valid
    return plan, schematic, previous, model_sources, candidate_hash


HEADER = r"""Var B:IPCB_Board;Log:TStringList;
 D:IServerDocument;I:IPCB_BoardIterator;P:IPCB_Primitive;C,J1:IPCB_Component;
 Dead:Array[0..30000] Of IPCB_Primitive;ND,K,NC:Integer;
 Cs:Array[0..__COMPONENT_MAX__] Of IPCB_Component;Ns:Array[0..__NET_MAX__] Of IPCB_Net;N:IPCB_Net;
 Body:IPCB_ComponentBody;Models:Array[0..2] Of IPCB_Model;M:IPCB_Model;Pt:TCoordPoint;
 PD:IPCB_Pad;V:IPCB_Via;Cache:TPadCache;G:IPCB_GeometricPolygon;CT:IPCB_Contour;RG:IPCB_Region;
 Good:Boolean;FabText:IPCB_Text;
Procedure Mark(S:String);Begin Log.Add(S);Log.SaveToFile('__LOG__');End;
Procedure Reg(P:IPCB_Primitive);Begin B.AddPCBObject(P);PCBServer.SendMessageToRobots(B.I_ObjectAddress,c_Broadcast,PCBM_BoardRegisteration,P.I_ObjectAddress);End;
Function CopperLayer(L:TLayer):Boolean;
Begin Result:=(L=eTopLayer) Or (L=eMidLayer1) Or (L=eMidLayer2) Or (L=eMidLayer3) Or (L=eMidLayer4) Or (L=eBottomLayer);End;
Function ObjectCount(Kind:String;CopperOnly:Boolean):Integer;
Var CI:IPCB_BoardIterator;CP:IPCB_Primitive;
Begin Result:=0;CI:=B.BoardIterator_Create;CI.SetState_FilterAll;
 If Kind='components' Then CI.AddFilter_ObjectSet(MkSet(eComponentObject));
 If Kind='pads' Then CI.AddFilter_ObjectSet(MkSet(ePadObject));
 If Kind='tracks' Then CI.AddFilter_ObjectSet(MkSet(eTrackObject));
 If Kind='arcs' Then CI.AddFilter_ObjectSet(MkSet(eArcObject));
 If Kind='vias' Then CI.AddFilter_ObjectSet(MkSet(eViaObject));
 If Kind='bodies' Then CI.AddFilter_ObjectSet(MkSet(eComponentBodyObject));
 CP:=CI.FirstPCBObject;
 While CP<>Nil Do Begin If (Not CopperOnly) Or CopperLayer(CP.Layer) Then Inc(Result);CP:=CI.NextPCBObject;End;B.BoardIterator_Destroy(CI);End;
Function ComponentMatches(S:String;X,Y,R:Double):Boolean;
Var CI:IPCB_BoardIterator;CP:IPCB_Component;Count:Integer;
Begin Result:=False;Count:=0;CI:=B.BoardIterator_Create;CI.SetState_FilterAll;CI.AddFilter_ObjectSet(MkSet(eComponentObject));CP:=CI.FirstPCBObject;
 While CP<>Nil Do Begin If CP.Name.Text=S Then Begin Inc(Count);Result:=(Abs(CoordToMMs(CP.X)-X)<0.00001) And (Abs(CoordToMMs(CP.Y)-Y)<0.00001) And (Abs(CP.Rotation-R)<0.00001);End;CP:=CI.NextPCBObject;End;B.BoardIterator_Destroy(CI);If Count<>1 Then Result:=False;End;
Procedure Track(N:IPCB_Net;L:TLayer;X1,Y1,X2,Y2,W:Double);
Var T:IPCB_Track;
Begin T:=PCBServer.PCBObjectFactory(eTrackObject,eNoDimension,eCreate_Default);T.X1:=MMsToCoord(X1);T.Y1:=MMsToCoord(Y1);T.X2:=MMsToCoord(X2);T.Y2:=MMsToCoord(Y2);T.Width:=MMsToCoord(W);T.Layer:=L;If N<>Nil Then Begin T.Net:=N;T.SetState_InNet(True);End;Reg(T);End;
Procedure SignalArc(N:IPCB_Net;L:TLayer;CX,CY,R,A0,A1,W:Double);
Var A:IPCB_Arc;
Begin A:=PCBServer.PCBObjectFactory(eArcObject,eNoDimension,eCreate_Default);A.XCenter:=MMsToCoord(CX);A.YCenter:=MMsToCoord(CY);A.Radius:=MMsToCoord(R);A.LineWidth:=MMsToCoord(W);A.StartAngle:=A0;A.EndAngle:=A1;A.Layer:=L;If N<>Nil Then Begin A.Net:=N;A.SetState_InNet(True);End;Reg(A);End;
"""


def geometry_lines(plan, schematic, model_sources):
    lines = []
    emit = lines.append
    mask_overrides = {(r['ref'], str(r['pin'])): r for r in plan.get('pad_solder_mask_overrides', [])}
    assert len(mask_overrides) == len(plan.get('pad_solder_mask_overrides', []))
    for (ref, pin), row in mask_overrides.items():
        assert family(ref) in ('R', 'C') and pin in ('1', '2')
        assert 0 < row['expansion_mm'] <= .05
        assert any(p['ref'] == ref and p['pin'] == pin and p['layer'] == 32 for p in plan['physical_pads'])
    nmap = {name: f"Ns[{i}]" for i, name in enumerate(plan["nets"])}
    cmap = {c["ref"]: f"Cs[{i}]" for i, c in enumerate(plan["components"])}
    for name, var in nmap.items():
        emit(f"{var}:=PCBServer.PCBObjectFactory(eNetObject,eNoDimension,eCreate_Default);{var}.Name:={quote(name)};Reg({var});")
    for comp in plan["components"]:
        ref, var = comp["ref"], cmap[comp["ref"]]
        x, y, angle = (number(comp[k]) for k in ("x", "y", "rotation"))
        if ref == "J1":
            emit(f"{var}:=J1;")
        else:
            emit(f"{var}:=PCBServer.PCBObjectFactory(eComponentObject,eNoDimension,eCreate_Default);{var}.Name.Text:={quote(ref)};{var}.Pattern:={quote(comp['pattern'])};{var}.Layer:={layer(comp['layer'])};{var}.X:=MMsToCoord({x});{var}.Y:=MMsToCoord({y});{var}.Rotation:={angle};{var}.NameOn:=False;{var}.CommentOn:=False;Reg({var});")
        emit(f"{var}.SourceUniqueId:={quote(schematic['components'][ref])};")
        key = family(ref)
        if key in model_sources:
            model = model_sources[key]
            index = {"R": 0, "C": 1, "SMP": 2}[key]
            projection = "eBoardSide_Top" if comp["layer"] == 1 else "eBoardSide_Bottom"
            rx, ry = map(number, model["rotation_xyz_deg"][:2])
            dz, standoff, height = (round(model[k]/UNIT) for k in ("dz_mm", "standoff_mm", "overall_height_mm"))
            emit(f"Body:=PCBServer.PCBObjectFactory(eComponentBodyObject,eNoDimension,eCreate_Default);M:=Models[{index}].I_Replicate;Pt:=M.GetOrigin;Pt.X:=MMsToCoord({x});Pt.Y:=MMsToCoord({y});M.SetOrigin(Pt);M.SetState({rx},{ry},{angle},{dz});M.SetEmbed(True);Body.SetModel(M);Body.SetState_FromModel;Body.SetBodyProjection({projection});Body.SetStandoffHeight({standoff});Body.SetOverallHeight({height});{var}.AddPCBObject(Body);Reg(Body);Body.ValidateMesh;")

    for pad in plan["physical_pads"]:
        ref, pin, net = pad["ref"], pad["pin"], nmap.get(pad["net"], "Nil")
        if ref == "J1":
            emit(f"PD:=J1.GetState_PadByName({quote(pin)});If PD<>Nil Then Begin PD.Net:={net};PD.SetState_InNet({str(net != 'Nil')});End;")
            continue
        if ref is None:
            emit("I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;")
            emit(f"While PD<>Nil Do Begin If (PD.Component=Nil) And (PD.Name={quote(pin)}) Then Begin PD.Net:={net};PD.SetState_InNet({str(net != 'Nil')});End;PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);")
            continue
        shp = "eRectangular" if pad["shape"] == "rect" else "eRounded"
        x, y, sx, sy, hole, angle = (number(pad[k]) for k in ("x", "y", "sx", "sy", "hole", "rotation"))
        emit(f"PD:=PCBServer.PCBObjectFactory(ePadObject,eNoDimension,eCreate_Default);PD.Name:={quote(pin)};PD.X:=MMsToCoord({x});PD.Y:=MMsToCoord({y});PD.Layer:={layer(pad['layer'])};PD.Mode:=ePadMode_Simple;PD.TopShape:={shp};PD.MidShape:={shp};PD.BotShape:={shp};PD.TopXSize:=MMsToCoord({sx});PD.TopYSize:=MMsToCoord({sy});PD.MidXSize:=PD.TopXSize;PD.BotXSize:=PD.TopXSize;PD.MidYSize:=PD.TopYSize;PD.BotYSize:=PD.TopYSize;PD.Rotation:={angle};PD.HoleSize:=MMsToCoord({hole});PD.Plated:=True;PD.Net:={net};PD.SetState_InNet({str(net != 'Nil')});")
        paste = family(ref) in ("R", "C")
        mask = number(mask_overrides.get((ref, pin), {}).get('expansion_mm', .05))
        emit(f"PD.SetState_PasteMaskEnabled({str(paste)});Cache:=PD.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord({0 if paste else -2});Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord({mask});Cache.SolderMaskBottomExpansion:=MMsToCoord({mask});PD.SetState_Cache(Cache);{cmap[ref]}.AddPCBObject(PD);Reg(PD);")

    for track in plan["tracks"]:
        coords = ",".join(number(v) for v in [*track["a"], *track["b"], track["width"]])
        emit(f"Track({nmap[track['net']]},{layer(track['layer'])},{coords});")
    for arc in plan["arcs"]:
        values = ",".join(number(arc[k]) for k in ("cx", "cy", "radius", "start_angle", "end_angle", "width"))
        emit(f"SignalArc({nmap[arc['net']]},{layer(arc['layer'])},{values});")
    for via in plan["vias"] + plan["shield_vias"]:
        x, y, diameter, hole = (number(via[k]) for k in ("x", "y", "diameter", "hole"))
        emit(f"V:=PCBServer.PCBObjectFactory(eViaObject,eNoDimension,eCreate_Default);V.X:=MMsToCoord({x});V.Y:=MMsToCoord({y});V.Size:=MMsToCoord({diameter});V.HoleSize:=MMsToCoord({hole});V.LowLayer:={layer(via['low'])};V.HighLayer:={layer(via['high'])};V.Net:={nmap[via['net']]};V.SetState_InNet(True);V.SetState_PasteMaskEnabled(False);Cache:=V.GetState_Cache;Cache.PasteMaskExpansionValid:=eCacheManual;Cache.PasteMaskExpansion:=MMsToCoord(-2);Cache.SolderMaskExpansionValid:=eCacheManual;Cache.SolderMaskExpansion:=MMsToCoord(-1);Cache.SolderMaskBottomExpansion:=MMsToCoord(-1);V.SetState_Cache(Cache);Reg(V);")
    for name, regions in (("GND", plan["ground_regions"]), ("MASK", plan["solder_openings"])):
        for ll, mapping in regions.items():
            geo = shape(mapping).simplify(.001, preserve_topology=True)
            polys = list(geo.geoms) if hasattr(geo, "geoms") else [geo]
            for i, poly in enumerate(polys):
                if poly.is_empty:
                    continue
                assert poly.geom_type == "Polygon" and poly.is_valid
                poly = orient(poly, sign=1)
                emit("G:=PCBServer.PCBGeometricPolygonFactory;")
                for ring, hole in [(poly.exterior, False)] + [(r, True) for r in poly.interiors]:
                    emit("CT:=PCBServer.PCBContourFactory;")
                    for x, y in list(ring.coords)[:-1]:
                        emit(f"CT.AddPoint(MMsToCoord({number(x)}),MMsToCoord({number(y)}));")
                    emit(f"G.AddContourIsHole(CT,{str(hole)});")
                emit(f"RG:=PCBServer.PCBObjectFactory(eRegionObject,eNoDimension,eCreate_Default);RG.Kind:=eRegionKind_Copper;RG.Layer:={layer(ll)};RG.Name:={quote(f'QD38_{name}_{ll}_{i}')};RG.SetGeometricPolygon(G);")
                if name == "GND":
                    emit(f"RG.Net:={nmap['GND']};RG.SetState_InNet(True);")
                emit("Reg(RG);")

    cx, cy = plan["sample_center"]
    width, height = plan["cavity_mm"]
    radius = plan.get("cavity_radius_mm", .5)
    assert 0 < radius < min(width, height)/2
    x0, x1, y0, y1 = cx-width/2, cx+width/2, cy-height/2, cy+height/2
    for a, b in [((x0+radius, y0), (x1-radius, y0)), ((x1, y0+radius), (x1, y1-radius)), ((x1-radius, y1), (x0+radius, y1)), ((x0, y1-radius), (x0, y0+radius))]:
        emit("Track(Nil,eMechanical3," + ",".join(number(v) for v in [*a, *b, .05]) + ");")
    for x, y, a0, a1 in [(x1-radius, y0+radius, 270, 360), (x1-radius, y1-radius, 0, 90), (x0+radius, y1-radius, 90, 180), (x0+radius, y0+radius, 180, 270)]:
        emit("SignalArc(Nil,eMechanical3," + ",".join(number(v) for v in [x, y, radius, a0, a1, .05]) + ");")
    note = f"BOTTOM BLIND POCKET: {number(width)} x {number(height)} mm, R{number(radius)}, DEPTH {number(plan['cavity_depth_mm'])} mm FROM BOTTOM; NON-PLATED; NON-THROUGH"
    emit(f"FabText:=PCBServer.PCBObjectFactory(eTextObject,eNoDimension,eCreate_Default);FabText.Layer:=eMechanical3;FabText.MoveToXY(MMsToCoord(21),MMsToCoord(43));FabText.Size:=MMsToCoord(0.8);FabText.Width:=MMsToCoord(0.12);FabText.Text:={quote(note)};Reg(FabText);")
    return lines


def generate(plan, schematic, previous, model_sources, stem, candidate_hash):
    header = HEADER.replace("__COMPONENT_MAX__", str(len(plan["components"])-1)).replace("__NET_MAX__", str(len(plan["nets"])-1)).replace("__LOG__", str(HERE / (stem + "_native_log.txt")))
    statements = geometry_lines(plan, schematic, model_sources)
    batches = [statements[i:i+250] for i in range(0, len(statements), 250)]
    procedures = []
    for i, batch in enumerate(batches):
        procedures.append(f"Procedure BuildRevision{i:03};\nBegin\n" + "\n".join(batch) + "\nEnd;\n")
    preflight = []
    for key, copper_only in (("components", False), ("pads", False), ("tracks", True), ("arcs", True), ("vias", False), ("bodies", False)):
        preflight.append(f"If ObjectCount({quote(key)},{str(copper_only)})<>{len(previous[key])} Then Begin Mark('STOP_FROZEN_{key.upper()}_COUNT');Log.Free;Exit;End;")
    for comp in previous["components"]:
        preflight.append(f"If Not ComponentMatches({quote(comp['designator'])},{number(comp['x'])},{number(comp['y'])},{number(comp['rotation'])}) Then Begin Mark({quote('STOP_FROZEN_COMPONENT_' + comp['designator'])});Log.Free;Exit;End;")
    main = r"""Procedure __STEM__;
Begin
 Log:=TStringList.Create;Mark('START_REVISION');Mark('CANDIDATE_SHA256=__HASH__');
 D:=Client.OpenDocument('PCB','__PCB__');If D=Nil Then Begin Mark('NO_DOCUMENT');Log.Free;Exit;End;
 Client.ShowDocument(D);B:=PCBServer.GetCurrentPCBBoard;
 If B=Nil Then Begin Mark('NO_BOARD');Log.Free;Exit;End;
 If LowerCase(B.FileName)<>LowerCase('__PCB__') Then Begin Mark('WRONG_BOARD');Log.Free;Exit;End;
 __PREFLIGHT__
 J1:=Nil;For K:=0 To 2 Do Models[K]:=Nil;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
 While C<>Nil Do Begin If C.Name.Text='J1' Then J1:=C;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
 If J1=Nil Then Begin Mark('STOP_MISSING_J1');Log.Free;Exit;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentBodyObject));Body:=I.FirstPCBObject;
 While Body<>Nil Do Begin C:=Body.Component;
  If C<>Nil Then Begin K:=-1;If C.Name.Text='R02' Then K:=0;If C.Name.Text='C02' Then K:=1;If C.Name.Text='SMP02' Then K:=2;
   If K>=0 Then Begin M:=Body.GetModel;If M<>Nil Then Models[K]:=M.I_Replicate;End;
  End;Body:=I.NextPCBObject;
 End;B.BoardIterator_Destroy(I);
 For K:=0 To 2 Do If Models[K]=Nil Then Begin Mark('STOP_MISSING_SOURCE_MODEL');Log.Free;Exit;End;
 Mark('PREFLIGHT_OK');PCBServer.PreProcess;
 Try
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;
  I.AddFilter_ObjectSet(MkSet(eTrackObject,eArcObject,eFillObject,eRegionObject,eTextObject,eComponentBodyObject,eViaObject,ePadObject,ePolyObject));P:=I.FirstPCBObject;
  While P<>Nil Do Begin
   Good:=(P.Component=Nil) And (P.Layer=eMechanical1) And ((P.ObjectId=eTrackObject) Or (P.ObjectId=eArcObject));
   If (P.Component<>J1) And Not Good Then Begin
    If P.ObjectId=ePadObject Then Begin PD:=P;If PD.Component<>Nil Then Begin Dead[ND]:=P;Inc(ND);End;End
    Else Begin Dead[ND]:=P;Inc(ND);End;
   End;P:=I.NextPCBObject;
  End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eComponentObject));C:=I.FirstPCBObject;
  While C<>Nil Do Begin If C<>J1 Then Begin Dead[ND]:=C;Inc(ND);End;C:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);
  I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(ePadObject));PD:=I.FirstPCBObject;
  While PD<>Nil Do Begin PD.Net:=Nil;PD.SetState_InNet(False);PD:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  ND:=0;I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
  While N<>Nil Do Begin Dead[ND]:=N;Inc(ND);N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);
  For K:=0 To ND-1 Do B.RemovePCBObject(Dead[K]);Mark('OLD_REVISION_GEOMETRY_REMOVED');
  __CALLS__
  B.RebuildPadCaches;Mark('GEOMETRY_CREATED');
 Finally PCBServer.PostProcess;End;
 I:=B.BoardIterator_Create;I.SetState_FilterAll;I.AddFilter_ObjectSet(MkSet(eNetObject));N:=I.FirstPCBObject;
 While N<>Nil Do Begin N.ConnectivelyInValidate;N.Rebuild;N:=I.NextPCBObject;End;B.BoardIterator_Destroy(I);B.ConnectivelyValidateNets;
 B.SetState_DocumentHasChanged;B.ViewManager_FullUpdate;B.GraphicallyInvalidate;
 Mark('BUILT_NOT_SAVED_REQUIRES_NATIVE_REVIEW_SAVE_REOPEN_DRC');Log.Free;
End;
"""
    for old, new in {"__STEM__": stem, "__HASH__": candidate_hash, "__PCB__": str(TARGET), "__PREFLIGHT__": "\n ".join(preflight), "__CALLS__": "\n  ".join(f"BuildRevision{i:03};" for i in range(len(batches)))}.items():
        main = main.replace(old, new)
    text = header + "\n".join(procedures) + main
    assert not re.search(r"__[A-Z_]+__", text)
    assert "WorkspaceManager:SaveObject" not in text
    assert "RunBatchDesignRuleCheck" not in text
    text.encode("ascii")
    return text, len(batches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path, help="Independent complete copper audit with passed=true and candidate_sha256")
    parser.add_argument("--schematic", type=Path, default=DEST / "schematic_validation.json")
    parser.add_argument("--stem", default="ApplyQD90SevenRows")
    args = parser.parse_args()
    assert re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", args.stem)
    candidate, audit, schematic = (p.resolve() for p in (args.candidate, args.audit, args.schematic))
    for path in (candidate, audit, schematic):
        assert path.is_file() and path.is_relative_to(ROOT), "All input artifacts must be inside this repository"
    inputs = checked_inputs(candidate, audit, schematic)
    plan, sch, previous, models, candidate_hash = inputs
    text, batches = generate(plan, sch, previous, models, args.stem, candidate_hash)
    assert sha(TARGET) == FROZEN_SHA256 and sha(candidate) == candidate_hash, "Inputs changed during generation"
    pascal = HERE / (args.stem + ".pas")
    pascal.write_text(text, encoding="ascii")
    (HERE / (args.stem + ".PrjScr")).write_text(f"[Design]\nVersion=1.0\n[Document1]\nDocumentPath={args.stem}.pas\n[Generic_ScriptingSystem]\nStartProcName={args.stem}.pas>{args.stem}\n", encoding="ascii")
    report = dict(status="PREPARED_NOT_EXECUTED", native_pcb_modified=False, target=str(TARGET), frozen_native_sha256=FROZEN_SHA256, candidate=str(candidate), candidate_sha256=candidate_hash, audit=str(audit), audit_sha256=sha(audit), schematic_validation=str(schematic), schematic_validation_sha256=sha(schematic), pascal=str(pascal), pascal_sha256=sha(pascal), procedure=args.stem, counts={"components": len(plan["components"]), "pads": len(plan["physical_pads"]), "tracks": len(plan["tracks"]), "signal_arcs": len(plan["arcs"]), "signal_vias": len(plan["vias"]), "shield_vias": len(plan["shield_vias"])}, geometry_batches=batches, model_sources=models, caveat="Reopen the frozen saved PCB before execution. Runtime component/count guards are not a cryptographic live-document hash. Native save/reopen/DRC and independent saved-geometry, connectivity, mask, paste and model audits are still required.")
    (HERE / (args.stem + "_manifest.json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "model_sources"}, indent=2))


if __name__ == "__main__":
    main()
