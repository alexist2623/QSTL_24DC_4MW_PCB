"""Minimal local GND cutback from frozen saved-native geometry.

The complete existing mask and shield definitions are retained.  Existing
ground is only removed where newly moved signal copper needs clearance or a
newly isolated local island lacks a ground anchor.  Never refill/rebuild the
rest of the board and never globally simplify already saved remote contours.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter, defaultdict
import hashlib
import json
import math
import sys

import shapely
from shapely.geometry import Point, LineString, Polygon, box, shape, mapping
from shapely.ops import unary_union
from shapely.strtree import STRtree

H=Path(__file__).resolve().parent
OLD=H.parent/"qd38_rotation_20261011"
ROOT=H.parents[1]
sys.path.insert(0,str(OLD))
from audit_saved_revision_surface import read_snapshot
from route_rf_corridor_bounded import pgeom, arc_line
from audit_candidate import audit as audit_signals
from audit_shield_surface_geometry import inspect_shield_clearance

UNIT=2.54e-6
LOCAL=box(5.5,36,14,49)
COPPER=(1,2,3,4,5,32)
GAP=.203
BASE_SHA="835347e328b421354c924653c1e877808d68353ba2ac7c85b727b1fe96d92495"
NATIVE_SHA="1ac42a098d0eb7f50f13e6ab7242dc9a81e40564f2cf7057d0134fa5732c723c"


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def polygons(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=="Polygon":return [geometry]
    return [p for g in geometry.geoms for p in polygons(g)]


def key(track):
    return (track["net"],track["layer"],track["width"],*sorted([tuple(track["a"]),tuple(track["b"])]))


def ground_connected(plan,ground):
    nodes=[]
    for p in plan["physical_pads"]:
        if p["net"]=="GND":
            nodes.append((set(COPPER) if p["layer"]==74 else {p["layer"]},pgeom(p),f"PAD:{p['ref']}-{p['pin']}"))
    for i,v in enumerate(plan["shield_vias"]):
        nodes.append(({5,32},Point(v["x"],v["y"]).buffer(v["diameter"]/2,quad_segs=96),f"SHIELD:{i}"))
    for layer,g in ground.items():
        for i,p in enumerate(polygons(g)):
            nodes.append(({layer},p,f"REGION:{layer}-{i}"))
    parents=list(range(len(nodes)))
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for layer in COPPER:
        indices=[i for i,n in enumerate(nodes) if layer in n[0]]
        geometries=[nodes[i][1] for i in indices]
        tree=STRtree(geometries)
        for i,g in enumerate(geometries):
            for j in tree.query(g.buffer(1e-8)):
                if i<int(j) and g.distance(geometries[int(j)])<=1e-8:
                    parents[root(indices[i])]=root(indices[int(j)])
    groups=defaultdict(list)
    for i,n in enumerate(nodes):groups[root(i)].append(n[2])
    return dict(passed=len(groups)==1,group_count=len(groups),groups=list(groups.values()) if len(groups)>1 else [],primitive_count=len(nodes))


def ground_clearance(plan,ground):
    rows=[]
    failures=[]
    for layer in COPPER:
        g=ground[layer]
        objects=[]
        for p in plan["physical_pads"]:
            if p["net"] not in (None,"GND") and p["layer"] in (layer,74):
                objects.append((f"PAD:{p['ref']}-{p['pin']}",pgeom(p),0.0))
        for v in plan["vias"]:
            if v["low"]<=layer<=v["high"]:
                objects.append((f"VIA:{v['label']}",Point(v["x"],v["y"]),v["diameter"]/2))
        for i,t in enumerate(plan["tracks"]):
            if t["layer"]==layer and t["net"]!="GND":
                objects.append((f"TRACK:{i}:{t['net']}",LineString([t["a"],t["b"]]),t["width"]/2))
        for i,a in enumerate(plan.get("arcs",[])):
            if a["layer"]==layer and a["net"]!="GND":
                objects.append((f"ARC:{i}:{a['net']}",arc_line(a),a["width"]/2+.00011))
        gap,label=min((g.distance(obj)-radius,label) for label,obj,radius in objects)
        row=dict(layer=layer,minimum_signal_gap_mm=gap,nearest=label,passed=gap>=.2-1e-6)
        rows.append(row)
        if not row["passed"]:failures.append(row)
    return dict(passed=not failures,failures=failures,layers=rows)


def main():
    source=H/"alignment_routed_candidate.json"
    signal_audit=H/"alignment_signal_audit.json"
    oldfile=H/"before_alignment/full_copper_candidate.json"
    nativefile=H/"before_alignment/QSTL_QD4_2SET_38PAD.PcbDoc"
    assert sha(oldfile)==BASE_SHA and sha(nativefile)==NATIVE_SHA
    old=json.loads(oldfile.read_text())
    plan=json.loads(source.read_text())
    source_hash=sha(source)
    evidence=json.loads(signal_audit.read_text())
    assert evidence["passed"] and evidence["candidate_sha256"]==source_hash
    schem=json.loads((ROOT/"QSTL_QD4_2SET_38PAD/schematic_validation.json").read_text())
    native_pads,native_regions,_,_,_=read_snapshot(nativefile,schem)
    saved_ground={layer:unary_union([r["geometry"] for r in native_regions if r["layer"]==layer and r["net"]=="GND"]) for layer in COPPER}
    # Mask and shield geometries are inherited, never regenerated.
    preserved=("shield_vias","solder_openings","qd_mask_field","qd_ground_exclusion","rc_mask_rectangles","zif_bottom_mask_rectangle","pad_solder_mask_overrides")
    for field in preserved:assert plan[field]==old[field],field
    assert plan["arcs"]==old["arcs"]
    assert [t for t in plan["tracks"] if t["net"].startswith(("S","MW"))]==[t for t in old["tracks"] if t["net"].startswith(("S","MW"))]
    op={(p["ref"],p["pin"]):p for p in old["physical_pads"] if p["ref"]}
    changed_pads=[p for p in plan["physical_pads"] if p["ref"] and p!=op[(p["ref"],p["pin"])]]
    assert all(p["ref"]=="Q1" for p in changed_pads)
    ov={v["label"]:v for v in old["vias"]}
    changed_vias=[v for v in plan["vias"] if any(v[k]!=ov[v["label"]][k] for k in ("x","y","diameter","hole","low","high"))]
    assert len(changed_vias)==22 and all(v["label"].startswith("Q1-") for v in changed_vias)
    oldtracks=Counter(key(t) for t in old["tracks"])
    changed_tracks=[]
    for t in plan["tracks"]:
        k=key(t)
        if oldtracks[k]:oldtracks[k]-=1
        else:changed_tracks.append(t)
    assert all(t["net"].startswith("DC") and t["layer"] in (2,4) for t in changed_tracks)
    newground={}
    changes=[]
    routing_clearance_deltas=[]
    for layer in COPPER:
        cutters=[]
        for p in changed_pads:
            if p["layer"] in (layer,74):cutters.append(pgeom(p).buffer(GAP,quad_segs=48))
        for v in changed_vias:
            if v["low"]<=layer<=v["high"]:cutters.append(Point(v["x"],v["y"]).buffer(v["diameter"]/2+GAP,quad_segs=48))
        # A repaired tail can merge with an unchanged long collinear segment.
        # Compare geometric clearance unions, not primitive records, so this
        # harmless segmentation change never cuts remote native ground.
        new_track_cut=unary_union([LineString([t["a"],t["b"]]).buffer(t["width"]/2+GAP,quad_segs=48)
                                   for t in changed_tracks if t["layer"]==layer])
        old_track_cut=unary_union([LineString([t["a"],t["b"]]).buffer(t["width"]/2+GAP,quad_segs=48)
                                   for t in old["tracks"] if t["layer"]==layer])
        routing_delta=new_track_cut.difference(old_track_cut)
        routing_outside=routing_delta.difference(LOCAL).area
        assert routing_outside<1e-10,("Remote route clearance delta",layer,routing_outside)
        routing_clearance_deltas.append(dict(layer=layer,new_clearance_area_mm2=routing_delta.area,
                                             outside_local_box_area_mm2=routing_outside))
        cutters.append(routing_delta.intersection(LOCAL))
        cut=unary_union(cutters)
        assert LOCAL.covers(cut),f"Layer {layer} signal-clearance cut exceeds authorized local box"
        actual=saved_ground[layer].difference(cut)
        anchors=unary_union([pgeom(p) for p in plan["physical_pads"] if p["net"]=="GND" and p["layer"] in (layer,74)]+
                            [Point(v["x"],v["y"]).buffer(v["diameter"]/2,quad_segs=96) for v in plan["shield_vias"] if v["low"]<=layer<=v["high"]])
        kept,removed=[],[]
        for island in polygons(actual):
            (kept if island.intersects(anchors) else removed).append(island)
        removed_geometry=unary_union(removed)
        assert removed_geometry.difference(LOCAL).area<1e-10,"Local cut disconnected remote ground"
        # Freeze exact native-grid contours. The native delta must not apply a
        # second global simplification to these already exported coordinates.
        actual=shapely.set_precision(unary_union(kept),grid_size=UNIT,mode="valid_output")
        difference=saved_ground[layer].symmetric_difference(actual)
        outside=difference.difference(LOCAL)
        assert outside.area<1e-9,(layer,outside.area)
        newground[layer]=actual
        changes.append(dict(layer=layer,changed_area_mm2=difference.area,changed_bounds_mm=list(difference.bounds),
                            outside_local_box_difference_mm2=outside.area,removed_unanchored_islands=len(removed),
                            removed_unanchored_area_mm2=removed_geometry.area,
                            component_count=len(polygons(actual)),
                            baseline_saved_ground_area_mm2=saved_ground[layer].area,new_area_mm2=actual.area,
                            global_simplify_would_change_outside_area_mm2=actual.symmetric_difference(actual.simplify(.001,preserve_topology=True)).difference(LOCAL).area))
    plan["ground_regions"]={str(layer):mapping(g) for layer,g in newground.items()}
    plan["surface_validation"]=deepcopy(old["surface_validation"])
    plan["surface_validation"].update(status="OFFLINE_ALIGNMENT_NATIVE_PENDING",native_ground_simplify_mm=0,
                                       native_mask_simplify_mm=.001,local_ground_update_box_mm=list(LOCAL.bounds),
                                       local_ground_update="Subtractive cutback from frozen saved-native ground; old keepouts retained.",
                                       inherited_qd_mask_field_preserved=True)
    plan["alignment_region_export"]=dict(native_ground_contours_prequantized=True,native_grid_mm=UNIT,
                                          ground_simplify_mm=0,mask_families_unchanged=True,
                                          source_native_sha256=NATIVE_SHA,local_box_mm=list(LOCAL.bounds),
                                          changed_layers=[r["layer"] for r in changes if r["changed_area_mm2"]>1e-8])
    signal_result=audit_signals(plan)
    ground_result=ground_clearance(plan,newground)
    connection=ground_connected(plan,newground)
    pads=[dict(p,geometry=pgeom(p)) for p in plan["physical_pads"]]
    tracks=[dict(t,geometry=LineString([t["a"],t["b"]])) for t in plan["tracks"]]
    tracks += [dict(a,geometry=arc_line(a),is_arc=True) for a in plan.get("arcs",[])]
    shields=inspect_shield_clearance(plan,pads,tracks,plan["vias"]+plan["shield_vias"],newground)
    field=shape(plan["qd_mask_field"])
    qd=unary_union([pgeom(p) for p in plan["physical_pads"] if p["ref"]=="Q1"])
    cavity=box(7.6,39.85,11.9,45.15)
    mask=dict(all_fields_unchanged=all(plan[k]==old[k] for k in preserved),
              all_new_qd_pads_inside_preserved_field=field.covers(qd),
              field_open_on_bottom=shape(plan["solder_openings"]["38"]).buffer(1e-9).covers(field),
              cavity_inside_preserved_field=field.covers(cavity),
              inherited_field_bounds_mm=list(field.bounds),C_R_aperture_overrides_preserved=plan["pad_solder_mask_overrides"]==old["pad_solder_mask_overrides"],
              no_new_mask_opening=True)
    mask["passed"]=all(mask[k] for k in ("all_fields_unchanged","all_new_qd_pads_inside_preserved_field","field_open_on_bottom","cavity_inside_preserved_field","C_R_aperture_overrides_preserved"))
    exclusion=shape(plan["qd_ground_exclusion"])
    exclusion_rows=[]
    for layer,g in newground.items():
        area=exclusion.difference(g.buffer(1e-5)).area if layer==1 else g.intersection(exclusion.buffer(-1e-5)).area
        exclusion_rows.append(dict(layer=layer,area_mm2=area,passed=area<1e-8))
    overlap=[]
    for n in (2,21):
        p=next(p for p in plan["physical_pads"] if p["ref"]=="Q1" and p["pin"]==str(n))
        copper=unary_union([t["geometry"].buffer(t["width"]/2,quad_segs=64) for t in tracks if t["net"]==p["net"]])
        area=copper.intersection(pgeom(p)).area
        overlap.append(dict(pad=n,net=p["net"],retained_RF_overlap_mm2=area,passed=area>1e-4))
    failures=[]
    for label,result in (("signal",signal_result),("ground_clearance",ground_result),("ground_connectivity",connection),("shield",shields),("mask",mask)):
        if not result["passed"]:failures.append(dict(kind=label,detail=result))
    if not all(r["passed"] for r in exclusion_rows):failures.append(dict(kind="QD_ground_exclusion",detail=exclusion_rows))
    if not all(r["passed"] for r in overlap):failures.append(dict(kind="RF_pad_overlap",detail=overlap))
    result=dict(passed=not failures,failures=failures,source_routed_candidate_sha256=source_hash,
                source_routed_audit_sha256=sha(signal_audit),source_baseline_candidate_sha256=BASE_SHA,
                source_native_sha256=NATIVE_SHA,local_box_mm=list(LOCAL.bounds),changed_ground_layers=plan["alignment_region_export"]["changed_layers"],
                ground_changes=changes,signal_audit=signal_result,ground_clearance=ground_result,ground_connectivity=connection,
                routing_clearance_deltas=routing_clearance_deltas,
                shield_audit=shields,mask_audit=mask,QD_ground_exclusion=exclusion_rows,RF_2_21_overlap=overlap,
                inherited_mask_field_note="The previous larger field is intentionally retained and verified to contain all new pads and the cavity; no new mask opening area is introduced.",
                native_export_requirement="Export prequantized ground contours directly with NO global simplification. Leave all native mask regions and shield primitives untouched.",
                scope="Offline complete signal, local GND, unchanged shield/mask geometry. Native save/reopen, paste, library correspondence and DRC remain mandatory.")
    output=H/"alignment_full_candidate.json"
    output.write_text(json.dumps(plan,indent=2))
    result["candidate_sha256"]=sha(output)
    (H/"alignment_full_audit.json").write_text(json.dumps(result,indent=2))
    exports=[]
    for layer in plan["alignment_region_export"]["changed_layers"]:
        for i,poly in enumerate(polygons(newground[layer])):
            exports.append(dict(name=f"QD38_GND_{layer}_{i}",layer=layer,net="GND",geometry=mapping(poly)))
    (H/"alignment_ground_export.json").write_text(json.dumps(dict(candidate_sha256=sha(output),source_native_sha256=NATIVE_SHA,
                                                                  simplify_mm=0,grid_mm=UNIT,changed_layers=plan["alignment_region_export"]["changed_layers"],regions=exports),indent=2))
    assert sha(source)==source_hash and sha(oldfile)==BASE_SHA and sha(nativefile)==NATIVE_SHA
    print(json.dumps({k:v for k,v in result.items() if k not in ("signal_audit","shield_audit","ground_changes")},indent=2))
    raise SystemExit(0 if result["passed"] else 2)


if __name__=="__main__":main()
