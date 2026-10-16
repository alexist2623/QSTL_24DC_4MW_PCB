"""Read-only DC spacing and complete SMP/resistor-envelope checks on saved copper.

The .10 mm exception applies only to distinct DC nets on L2/L4. Every other
DC-pair and DC/non-GND-net comparison retains .15 mm. L2/L4 DC-to-GND remains
.20 mm. All geometry comes from saved native pads, vias, tracks and regions.
"""
from collections import defaultdict
import math

from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

from audit_saved_rf_geometry import pad_geometry, arc_centerline, ARC_ERROR

COPPER=(1,2,3,4,5,32)
TOL=1e-5


def dc(net):return (net or "").startswith("DC")


def inspect_saved_dc(native, vias, ground_regions):
    failures=[];bylayer=defaultdict(lambda:defaultdict(list));widths=[]
    for pad in native["pads"]:
        if pad["net"] is None:continue
        geom=pad_geometry(pad)
        for layer in COPPER if pad["layer"]==74 else (pad["layer"],):
            if layer in COPPER:bylayer[layer][pad["net"]].append(geom)
    for via in vias:
        if via["net"] is None:continue
        geom=Point(via["x"],via["y"]).buffer(via["diameter"]/2,quad_segs=128)
        for layer in COPPER:
            if via["low"]<=layer<=via["high"]:bylayer[layer][via["net"]].append(geom)
    for track in native["tracks"]:
        net,layer=track["net"],track["layer"]
        if net is None or layer not in COPPER:continue
        line=LineString([(track["x1"],track["y1"]),(track["x2"],track["y2"])])
        bylayer[layer][net].append(line.buffer(track["width"]/2,quad_segs=128))
        if dc(net) and layer in (2,4):
            widths.append(track["width"])
            if abs(track["width"]-.125)>TOL:failures.append(dict(kind="internal_DC_width",net=net,layer=layer,width_mm=track["width"]))
    for arc in native["arcs"]:
        if arc["net"] is None or arc["layer"] not in COPPER:continue
        bylayer[arc["layer"]][arc["net"]].append(arc_centerline(arc).buffer(arc["width"]/2+ARC_ERROR,quad_segs=128))
        if dc(arc["net"]):failures.append(dict(kind="unexpected_DC_arc",net=arc["net"],layer=arc["layer"]))
    for region in ground_regions:
        bylayer[region["layer"]]["GND"].append(region["geometry"])
    # Work on local primitive pairs. Unioning a full zigzag bus into complex
    # polygons before all-pairs distance makes a read-only audit needlessly
    # slow and obscures the actual offending saved primitive.
    copper={layer:[(net,geom) for net,parts in nets.items() for geom in parts] for layer,nets in bylayer.items()}
    spacing=[]
    search_radius=.201
    for layer,items in copper.items():
        minimum_pair=math.inf;minimum_other=math.inf;minimum_gnd=math.inf
        tree=STRtree([geom for _,geom in items])
        for i,(a,ga) in enumerate(items):
            if not dc(a):continue
            for j in tree.query(ga.buffer(search_radius,quad_segs=8)):
                j=int(j);b,gb=items[j]
                if a==b or (dc(b) and j>=i):continue
                gap=ga.distance(gb)
                if "GND" in (a,b):
                    # The preserved internal ground rule is .20. Elsewhere
                    # the original general .15 clearance is not relaxed.
                    minimum_gnd=min(minimum_gnd,gap);required=.20 if layer in (2,4) else .15
                    category="DC_to_GND"
                elif dc(a) and dc(b):
                    minimum_pair=min(minimum_pair,gap);required=.10 if layer in (2,4) else .15
                    category="DC_pair"
                else:
                    minimum_other=min(minimum_other,gap);required=.15;category="DC_to_other_signal"
                if gap<required-TOL:failures.append(dict(kind=category+"_clearance",layer=layer,nets=[a,b],gap_mm=gap,required_mm=required))
        value=lambda n:None if math.isinf(n) else n
        spacing.append(dict(layer=layer,minimum_DC_pair_gap_mm=value(minimum_pair),minimum_DC_other_signal_gap_mm=value(minimum_other),minimum_DC_GND_gap_mm=value(minimum_gnd),search_radius_mm=search_radius,
                            minimum_interpretation="A numerical value below the search radius is the global minimum; null means no nearby primitive pair in that category."))
    smp=defaultdict(list)
    for pad in native["pads"]:
        if (pad["component"] or "").startswith("SMP"):smp[pad["component"]].append(pad)
    envelopes=[]
    if len(smp)!=16:failures.append(dict(kind="SMP_component_count",actual=len(smp),expected=16))
    for ref,pads in smp.items():
        if len(pads)!=5 or {p["number"] for p in pads}!={"1","2","3","4","5"} or not all(p["layer"]==74 and p["hole"]>0 for p in pads):
            failures.append(dict(kind="SMP_five_plated_pads",ref=ref));continue
        envelope=unary_union([pad_geometry(p) for p in pads]).convex_hull
        for layer in (2,4):
            dc_parts=[geom for net,geom in copper.get(layer,[]) if dc(net)]
            gap=min((part.distance(envelope) for part in dc_parts),default=math.inf)
            record=dict(component=ref,layer=layer,hull_bounds_mm=list(envelope.bounds),DC_to_hull_gap_mm=gap,required_mm=.15)
            envelopes.append(record)
            if gap<.15-TOL:failures.append(dict(kind="DC_inside_SMP_five_pad_envelope_clearance",**record))
    passives=defaultdict(list)
    for pad in native["pads"]:
        ref=pad["component"] or ""
        if len(ref)>1 and ref.startswith("R") and ref[1:].isdigit():passives[ref].append(pad)
    passive_envelopes=[]
    if len(passives)!=16:failures.append(dict(kind="resistor_component_count",actual=len(passives),expected=16))
    for ref,pads in passives.items():
        if len(pads)!=2 or {p["number"] for p in pads}!={"1","2"}:
            failures.append(dict(kind="resistor_two_pad_footprint",ref=ref));continue
        envelope=unary_union([pad_geometry(p) for p in pads]).convex_hull
        dc_pad=next((p for p in pads if ref.startswith("R") and p["number"]=="2" and dc(p["net"])),None)
        for layer in (2,4):
            minimum=math.inf
            for net,parts in bylayer.get(layer,{}).items():
                if not dc(net):continue
                # The intended DC landing on resistor pad 2 is permitted.
                # Its opposite RF pad and the inter-pad bridge stay blocked.
                blocked=envelope.difference(pad_geometry(dc_pad)) if dc_pad and net==dc_pad["net"] else envelope
                gap=min((part.distance(blocked) for part in parts),default=math.inf)
                minimum=min(minimum,gap)
                if gap<.15-TOL:failures.append(dict(kind="DC_inside_resistor_two_pad_envelope_clearance",component=ref,layer=layer,net=net,gap_mm=gap,required_mm=.15,own_DC_pad2_permitted=bool(dc_pad and net==dc_pad["net"])))
            passive_envelopes.append(dict(component=ref,layer=layer,hull_bounds_mm=list(envelope.bounds),minimum_DC_to_forbidden_hull_gap_mm=minimum,required_mm=.15,own_DC_pad2_net=dc_pad["net"] if dc_pad else None))
    return dict(passed=not failures,failures=failures,layer_spacing=spacing,SMP_envelopes=envelopes,resistor_envelopes=passive_envelopes,
                internal_DC_track_count=len(widths),internal_DC_widths_mm=sorted(set(widths)),
                DC_pair_clearance_mm={"L2_L4":.10,"other_copper_layers":.15},
                DC_non_GND_other_net_clearance_mm=.15,L2_L4_DC_GND_clearance_mm=.20,
                full_SMP_envelope_clearance_mm=.15,resistor_two_pad_envelope_clearance_mm=.15,
                scope="Saved copper; includes DC track/via/pad shapes, all five native SMP plated pads and complete resistor two-pad convex hulls on L2/L4. Only the intended resistor DC pad 2 landing is removed from its own net's forbidden hull. Capacitor body projection is not an internal DC keepout. R/C shield keepouts are independently required. Native DRC and electrical connectivity remain separately required.")
