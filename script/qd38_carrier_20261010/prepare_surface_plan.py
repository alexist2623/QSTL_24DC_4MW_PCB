"""Prepare explicit ground, mask and Bottom/L5 shielding for native review."""
import json
import math
from collections import defaultdict
import numpy as np
import shapely
from shapely.geometry import Point, LineString, Polygon, box, mapping
from shapely.ops import unary_union
from route_circuit import pgeom
from design_geometry import DEST

GROUND_GAP_MM = .2
GROUND_GEOMETRY_GUARD_MM = .003
NATIVE_REGION_SIMPLIFY_MM = .001


def rect(g, margin):
    a,b,c,d=g.bounds
    return box(a-margin,b-margin,c+margin,d+margin)


def parts(g):
    return list(g.geoms) if hasattr(g,'geoms') else [g]


def main():
    p=json.loads((DEST/'negotiated_plan.json').read_text())
    audit=json.loads((DEST/'routed_candidate_audit.json').read_text())
    assert audit['passed']
    pads=p['physical_pads'];padgeom=[pgeom(d) for d in pads]
    bounds=Polygon(p['board_outline'])
    field=rect(unary_union([g for d,g in zip(pads,padgeom) if d['ref']=='Q1']),.15)
    exclusion=box(6.9,40.15,12.6,44.85)
    rc={}
    body=[]
    for n in [s['q'] for s in p['smp']]:
        rr,cc=f'R{n:02}',f'C{n:02}'
        rc[str(n)]=rect(unary_union([g for d,g in zip(pads,padgeom) if d['ref'] in (rr,cc)]),.9)
        for ref in (rr,cc):
            body.append(unary_union([g for d,g in zip(pads,padgeom) if d['ref']==ref]).convex_hull)
    body_keepout=unary_union(body).buffer(.001)
    smp=[unary_union([g for d,g in zip(pads,padgeom) if d['ref']==s['ref']]).convex_hull.buffer(.3,quad_segs=24)
         for s in p['smp']]
    zifvias=unary_union([Point(v['x'],v['y']).buffer(v['diameter']/2) for v in p['vias'] if v['label'].startswith('J1-')])
    ziftop=rect(unary_union([zifvias]+[g for d,g in zip(pads,padgeom) if d['ref']=='J1']),.3)
    zifbottom=rect(zifvias,.4)
    rf_lines=[LineString([t['a'],t['b']]) for t in p['tracks'] if t['layer']==32 and t['net'].startswith(('S','MW'))]
    rf=unary_union(rf_lines)
    extent=bounds.buffer(.05,join_style='mitre')
    retained_top=unary_union(smp+list(rc.values())+[ziftop,field.buffer(.25,join_style='mitre')])
    retained_bottom=unary_union(smp+list(rc.values())+[zifbottom,rf.buffer(.71,quad_segs=32)]).difference(field)
    mounts=unary_union([g.buffer(.10) for d,g in zip(pads,padgeom) if d['ref'] is None])
    openings={37:extent.difference(retained_top).union(mounts),38:extent.difference(retained_bottom).union(mounts).union(field)}

    signal_bottom=[g for d,g in zip(pads,padgeom) if d['layer'] in (32,74) and d['net']!='GND']
    signal_bottom += [Point(v['x'],v['y']).buffer(v['diameter']/2,quad_segs=32) for v in p['vias'] if v['high']==32]
    signal_bottom += [LineString([t['a'],t['b']]).buffer(t['width']/2,quad_segs=24) for t in p['tracks'] if t['layer']==32]
    forbidden=unary_union(signal_bottom)
    # Include same-net plated holes: copper clearance alone does not stop
    # an RF ground microvia colliding with an SMP ground mounting drill.
    other_holes=[(d['x'],d['y'],d['hole']/2) for d in pads if d['hole']>0]
    other_holes += [(v['x'],v['y'],v['hole']/2) for v in p['vias']]
    shields=[];rejected=defaultdict(int)
    def legal(x,y):
        land=Point(x,y).buffer(.125,quad_segs=24)
        if any(math.hypot(x-hx,y-hy)-radius-.05<.255 for hx,hy,radius in other_holes):return 'hole_clearance'
        if not bounds.buffer(-.15).covers(land):return 'edge'
        if land.intersects(field) or land.intersects(body_keepout):return 'bond_or_body'
        if land.distance(forbidden)<.15-1e-7:return 'signal_clearance'
        if any(math.hypot(x-v['x'],y-v['y'])<.40-1e-7 for v in shields):return 'via_pitch'
        return None
    def append(x,y,source):
        why=legal(x,y)
        if why:rejected[why]+=1;return False
        shields.append(dict(x=x,y=y,net='GND',diameter=.25,hole=.10,low=5,high=32,label=source))
        return True
    # Equal-angle SMP rings have paired escape gaps, mirrored about the
    # actual vertical RF escape. Candidate pairs are accepted together.
    ring_counts={}
    for s in p['smp']:
        direction=90 if s['y']<42.5 else 270
        count=0
        for k in range(9):
            offset=22.5*k
            if offset<=45:continue
            angles=[direction+offset] if k==8 else [direction+offset,direction-offset]
            pts=[(s['x']+1.05*math.cos(math.radians(a)),s['y']+1.05*math.sin(math.radians(a))) for a in angles]
            if all(legal(x,y) is None for x,y in pts):
                for x,y in pts:
                    assert append(x,y,s['ref']+'-ring');count+=1
        ring_counts[s['ref']]=count
    for ref,g in rc.items():
        # Around the two complete footprint envelopes, never between pads.
        perimeter=unary_union([gg for d,gg in zip(pads,padgeom) if d['ref'] in (f'R{int(ref):02}',f'C{int(ref):02}')]).convex_hull.buffer(.32,join_style='round').exterior
        for distance in np.arange(0,perimeter.length,.40):
            v=perimeter.interpolate(distance);append(v.x,v.y,'RC'+ref+'-perimeter')
    for line in rf_lines:
        for offset in (-.435,.435):
            for curve in parts(line.offset_curve(offset,join_style='round')):
                if curve.is_empty:continue
                for distance in np.arange(0,curve.length+.000001,.4):
                    v=curve.interpolate(distance);append(v.x,v.y,'RF-offset')

    # Native circles are exact; polygon buffers are inscribed and the native
    # generator also simplifies regions by 1 um. Reserve a 3 um geometry
    # margin rather than weakening the actual 0.2 mm clearance rule.
    ground_gap=GROUND_GAP_MM+GROUND_GEOMETRY_GUARD_MM
    ground={};islands={};gnd_pads=[g for d,g in zip(pads,padgeom) if d['net']=='GND']
    for layer in (1,2,3,4,5,32):
        obstacles=[]
        for d,g in zip(pads,padgeom):
            if d['layer'] in (layer,74) and d['net']!='GND':
                obstacles.append(g.buffer(ground_gap,quad_segs=24))
        for t in p['tracks']:
            if t['layer']==layer:
                obstacles.append(LineString([t['a'],t['b']]).buffer(t['width']/2+ground_gap,quad_segs=24))
        for v in p['vias']:
            if v['low']<=layer<=v['high']:
                obstacles.append(Point(v['x'],v['y']).buffer(v['diameter']/2+ground_gap,quad_segs=24))
        if layer!=1:obstacles.append(exclusion)
        copper=bounds.buffer(-.2,join_style='mitre').difference(unary_union(obstacles))
        anchors=unary_union(gnd_pads+[Point(v['x'],v['y']).buffer(.125,quad_segs=24) for v in shields if v['low']<=layer<=v['high']])
        keep=[];removed=[]
        for island in parts(copper):
            (keep if island.intersects(anchors) else removed).append(island)
        ground[layer]=unary_union(keep)
        islands[layer]=dict(kept=len(keep),removed=len(removed))
    # Every shield must actually land on grounded copper on both layers.
    disconnected=[]
    for v in shields:
        land=Point(v['x'],v['y']).buffer(.125)
        if not all(land.intersects(ground[l]) for l in (5,32)):
            disconnected.append(v)
    assert not disconnected,disconnected[:5]
    assert all(ground[l].intersection(exclusion).area<1e-9 for l in (2,3,4,5,32))
    # Check the same simplified geometry sent to Altium, against exact
    # circle/capsule distances instead of polygon approximations of copper.
    # The extra 10 nm threshold exceeds coordinate rounding on the 2.54 nm
    # Altium grid. Saved native DRC still remains the acceptance test.
    exported_ground_gaps={}
    for layer in (1,2,3,4,5,32):
        exported=ground[layer].simplify(NATIVE_REGION_SIMPLIFY_MM,preserve_topology=True)
        gaps=[]
        for d,g in zip(pads,padgeom):
            if d['layer'] in (layer,74) and d['net']!='GND':
                if d['shape']=='round':
                    assert abs(d['sx']-d['sy'])<1e-6
                    gap=exported.distance(Point(d['x'],d['y']))-d['sx']/2
                else:gap=exported.distance(g)
                gaps.append(gap)
        for t in p['tracks']:
            if t['layer']==layer:
                gaps.append(exported.distance(LineString([t['a'],t['b']]))-t['width']/2)
        for v in p['vias']:
            if v['low']<=layer<=v['high']:
                gaps.append(exported.distance(Point(v['x'],v['y']))-v['diameter']/2)
        exported_ground_gaps[str(layer)]=min(gaps)
        assert min(gaps)>=GROUND_GAP_MM+.00001,(layer,min(gaps))
    p.update(shield_vias=shields,ground_regions={str(l):mapping(g) for l,g in ground.items()},
             solder_openings={str(l):mapping(g) for l,g in openings.items()},
             qd_mask_field=mapping(field),qd_ground_exclusion=mapping(exclusion),
             rc_mask_rectangles={k:mapping(v) for k,v in rc.items()},zif_bottom_mask_rectangle=mapping(zifbottom),
             surface_validation=dict(status='OFFLINE_CANDIDATE_NATIVE_PENDING',shield_vias=len(shields),
                 shield_span=[5,32],shield_land_mm=.25,shield_hole_mm=.10,rf_offset_mm=.435,
                 smp_ring_counts=ring_counts,removed_ground_islands=islands,rejected_shield_candidates=dict(rejected),
                 mounting_mask_open_both=True,rc_mask_margin_mm=.9,via_paste=False,smp_paste=False,
                 ground_nominal_clearance_mm=GROUND_GAP_MM,ground_geometry_guard_mm=GROUND_GEOMETRY_GUARD_MM,
                 native_region_simplify_mm=NATIVE_REGION_SIMPLIFY_MM,
                 minimum_exported_ground_gap_mm=exported_ground_gaps,
                 qd_inner_ground_exclusion_mm=[5.7,4.7],preserve_top_ground=True))
    (DEST/'full_copper_candidate.json').write_text(json.dumps(p,indent=2))
    print(json.dumps(p['surface_validation'],indent=2))


if __name__=='__main__':main()
