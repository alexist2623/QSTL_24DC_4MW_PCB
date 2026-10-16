"""Independently inspect saved RF routing against native pads and body outlines.

Called by the saved-revision audit; takes read-only parsed native primitives.
No RF vias or non-Bottom RF copper are allowed. RF cannot pass across the
two-pad resistor envelope, and unrelated RF cannot pass below passive bodies.
Each MW net must be a single C2--R1--QD route with its junction absorbed into
R1's pad rather than a dangling bias branch outside that pad.
"""
from collections import Counter, defaultdict
import math

from shapely.affinity import rotate, translate
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, linemerge, snap

TOL=1e-5
ARC_ERROR=1e-5


def rf(net):return (net or "").startswith(("S","MW"))


def pad_geometry(pad):
    if pad["shape"]==1:
        return Point(pad["x"],pad["y"]).buffer(pad["size_x"]/2,quad_segs=128)
    return translate(rotate(box(-pad["size_x"]/2,-pad["size_y"]/2,pad["size_x"]/2,pad["size_y"]/2),pad["rotation"],origin=(0,0)),pad["x"],pad["y"])


def arc_centerline(arc):
    span=(arc["end_angle"]-arc["start_angle"])%360
    radius=arc["radius"]
    step=math.degrees(2*math.acos(max(-1,min(1,1-ARC_ERROR/radius))))
    steps=max(2,math.ceil(span/min(step,1)))
    return LineString([(arc["cx"]+radius*math.cos(math.radians(arc["start_angle"]+span*i/steps)),
                        arc["cy"]+radius*math.sin(math.radians(arc["start_angle"]+span*i/steps))) for i in range(steps+1)])


def lines(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=="LineString":return [geometry]
    if hasattr(geometry,"geoms"):return [line for item in geometry.geoms for line in lines(item)]
    return []


def inspect_saved_rf(native, vias):
    failures=[];items=[];paths=defaultdict(list);copper=defaultdict(list)
    for via in vias:
        if rf(via["net"]):failures.append(dict(kind="RF_signal_via",via=via))
    for track in native["tracks"]:
        if not rf(track["net"]):continue
        if track["layer"]!=32:failures.append(dict(kind="RF_track_not_Bottom",track=track))
        path=LineString([(track["x1"],track["y1"]),(track["x2"],track["y2"])])
        paths[track["net"]].append(path);copper[track["net"]].append(path.buffer(track["width"]/2,quad_segs=64))
    for arc in native["arcs"]:
        if not rf(arc["net"]):continue
        if arc["layer"]!=32:failures.append(dict(kind="RF_arc_not_Bottom",arc=arc))
        path=arc_centerline(arc);paths[arc["net"]].append(path)
        copper[arc["net"]].append(path.buffer(arc["width"]/2+ARC_ERROR,quad_segs=64))
    pads=native["pads"]
    bycomponent=defaultdict(list)
    for pad in pads:
        if pad["component"]:bycomponent[pad["component"]].append(pad)
    nets={net:unary_union(parts) for net,parts in copper.items()}
    # Native pad geometry establishes the resistor envelope without accepting
    # any candidate-supplied obstacle hull or component-position assumption.
    for ref,own in bycomponent.items():
        if not ref.startswith("R"):continue
        if len(own)!=2:
            failures.append(dict(kind="R_pad_count",ref=ref,count=len(own)));continue
        hull=unary_union([pad_geometry(p) for p in own]).convex_hull
        for net,trace in nets.items():
            allowed=unary_union([pad_geometry(p).buffer(3*TOL) for p in own if p["net"]==net])
            forbidden=hull.difference(allowed)
            overlap=trace.intersection(forbidden.buffer(-3*TOL)).area
            if overlap>1e-8:failures.append(dict(kind="RF_crosses_resistor_two_pad_envelope",ref=ref,net=net,overlap_mm2=overlap))
    for body in native["bodies"]:
        ref=body["component"]
        if not ref or not ref.startswith(("R","C")):continue
        own_nets={p["net"] for p in bycomponent[ref]}
        geom=Polygon(body["points"])
        if not geom.is_valid or geom.is_empty:
            failures.append(dict(kind="native_passive_body_invalid",ref=ref));continue
        for net,trace in nets.items():
            if net in own_nets:continue
            overlap=trace.intersection(geom.buffer(-3*TOL)).area
            if overlap>1e-8:failures.append(dict(kind="unrelated_RF_under_passive_body",ref=ref,net=net,overlap_mm2=overlap))
    # Node the saved centreline network, cut away contact-pad interiors, and
    # contract each contact to one graph vertex. This reveals a branch or stub
    # outside R1 even when all three terminals are electrically connected.
    for net,raw_paths in paths.items():
        own=[p for p in pads if p["net"]==net and p["component"]]
        contacts={p["component"]+"-"+p["number"]:pad_geometry(p) for p in own}
        expected={}
        for pad in own:
            ref,pin=pad["component"],pad["number"]
            degree=2 if net.startswith("MW") and ref.startswith("R") and pin=="1" else 1
            expected[ref+"-"+pin]=degree
        valid_members=(len(own)==3 and Counter("QD" if p["component"]=="Q1" else p["component"][0] for p in own)=={"QD":1,"C":1,"R":1}
                       and any(p["component"].startswith("C") and p["number"]=="2" for p in own)
                       and any(p["component"].startswith("R") and p["number"]=="1" for p in own)) if net.startswith("MW") else (
                       len(own)==2 and sum(p["component"].startswith("SMP") and p["number"]=="1" for p in own)==1
                       and sum(p["component"].startswith("C") and p["number"]=="1" for p in own)==1)
        if not valid_members:failures.append(dict(kind="RF_terminal_topology",net=net,members=list(contacts)))
        joined=unary_union(raw_paths)
        joined=unary_union(snap(joined,joined,4*TOL))
        cut=joined.difference(unary_union([g.buffer(4*TOL) for g in contacts.values()]))
        pieces=lines(cut)
        if len(pieces)>1:pieces=lines(linemerge(pieces))
        points=[];degree=Counter();adj=defaultdict(set)
        def vertex(xy):
            p=Point(xy)
            member=[label for label,g in contacts.items() if g.buffer(8*TOL).covers(p)]
            if len(member)==1:return member[0]
            for i,q in enumerate(points):
                if math.dist(xy,q)<8*TOL:return "junction-"+str(i)
            points.append(xy);return "junction-"+str(len(points)-1)
        for line in pieces:
            if line.length<4*TOL:continue
            a,b=vertex(line.coords[0]),vertex(line.coords[-1]);degree[a]+=1;degree[b]+=1;adj[a].add(b);adj[b].add(a)
        external={n:d for n,d in degree.items() if n not in contacts and d!=2}
        mismatch={n:dict(actual=degree[n],expected=d) for n,d in expected.items() if degree[n]!=d}
        missing=set(contacts)-set(degree)
        reached=set();pending=[next(iter(degree))] if degree else []
        while pending:
            node=pending.pop()
            if node in reached:continue
            reached.add(node);pending.extend(adj[node]-reached)
        connected=set(degree)==reached and not missing
        passed=valid_members and not external and not mismatch and connected
        item=dict(net=net,passed=passed,contact_degrees={k:degree[k] for k in contacts},external_invalid_degrees=external,
                  contact_degree_mismatch=mismatch,connected=connected,cut_path_piece_count=len(pieces))
        items.append(item)
        if not passed:failures.append(dict(kind="RF_branch_or_stub_outside_contact",**item))
    if len(paths)!=32:failures.append(dict(kind="RF_net_count",actual=len(paths),expected=32))
    return dict(passed=not failures,RF_signal_vias=sum(rf(v["net"]) for v in vias),net_count=len(paths),
                failures=failures,topology=items,arc_chord_error_bound_mm=ARC_ERROR,
                scope="Actual native RF tracks/arcs/vias, resistor pad convex hulls, passive body contours and pad-contracted route topology.")
