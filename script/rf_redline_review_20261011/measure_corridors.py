"""Read-only corridor measurements from the verified saved native snapshot.

These are local geometry bounds, not a routed candidate or RF certification.
"""
from pathlib import Path
import hashlib
import json
import math
from shapely.geometry import Point, box, LineString
from shapely.affinity import rotate, translate
from shapely.ops import unary_union, nearest_points

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / 'script/qd38_pad_alignment_20261011/saved_revision_snapshot.json'
s = json.loads(SOURCE.read_text())


def geometry(p):
    if p['shape'] == 1:
        assert abs(p['size_x'] - p['size_y']) < 1e-7
        return Point(p['x'], p['y']).buffer(p['size_x']/2, quad_segs=256)
    assert p['shape'] == 2, p
    return translate(rotate(box(-p['size_x']/2, -p['size_y']/2,
                               p['size_x']/2, p['size_y']/2),
                            p['rotation'], origin=(0, 0)), p['x'], p['y'])


pads = {(p['component'], str(p['number'])): p for p in s['pads']}
geos = {key: geometry(p) for key, p in pads.items()}
components = {ref: unary_union([g for (r, _), g in geos.items() if r == ref]).convex_hull
              for ref in {p['component'] for p in s['pads']} if ref}


def gate(a, b):
    ga, gb = a if not isinstance(a, tuple) else geos[a], b if not isinstance(b, tuple) else geos[b]
    pa, pb = nearest_points(ga, gb)
    return {'copper_envelope_gap_mm': ga.distance(gb),
            'nearest_a_xy': list(pa.coords[0]), 'nearest_b_xy': list(pb.coords[0])}


def capacity(gap, left_clearance=.15, right_clearance=.15):
    # Uniform CPWG widths only; zero-width shared GND is a lower bound and is
    # explicitly inadequate for actual shielding or useful return conductors.
    return {'trace_center_interval_mm': gap-left_clearance-right_clearance-.11,
            'two_RF_tracks_with_0p20_gap_to_shared_GND_required_gap_mm': left_clearance+right_clearance+2*.11+2*.20,
            'three_RF_tracks_with_0p20_gap_to_shared_GND_required_gap_mm': left_clearance+right_clearance+3*.11+4*.20,
            'shield_fence_total_edge_span_per_RF_mm': 2*(.435+.125),
            'one_RF_with_full_two_sided_fences_and_0p15_foreign_margin_width_mm': 1.42,
            'two_RF_with_aligned_shared_fence_and_0p15_foreign_margin_width_mm': 2.29,
            'packing_note': 'CPWG packing bounds omit finite shared GND width. Fence widths assume full aligned two-sided columns at nominal offset and 0.25 mm lands. Local fence gaps/longitudinal staggering may change these bounds. No channel capacity is certified.'}


measures = {}
for lr, rr in [('R09','R31'), ('R12','R28')]:
    v=gate(components[lr],components[rr]); v.update(capacity(v['copper_envelope_gap_mm']))
    v['object_a']=lr+' full resistor envelope';v['object_b']=rr+' full resistor envelope'
    measures[lr+'_'+rr]=v

# Same-Y local passage between each inner resistor DC pad/envelope and the
# central capacitor, plus the narrower common straight-X corridor along the
# complete central R/C group (projected bounding envelope).
for side, outer, centre in [('upper_left','R02','C35'),('upper_right','C35','R34'),
                           ('lower_left','R13','R16'),('lower_right','R16','R24')]:
    v=gate(components[outer],components[centre]); v.update(capacity(v['copper_envelope_gap_mm']))
    v['object_a']=outer;v['object_b']=centre
    measures[side+'_local']=v
for name,left,right in [('upper_left_common_X','R02','R35'),
                        ('upper_right_common_X','R35','R34'),
                        ('lower_left_common_X','R13','R16'),
                        ('lower_right_common_X','R16','R24')]:
    x1=components[left].bounds[2]; x2=components[right].bounds[0]
    measures[name]={'x_range_mm':[x1,x2],'projected_envelope_gap_mm':x2-x1,
                    'note':'Common X band for a straight longitudinal lane; objects need not overlap in Y.',
                    **capacity(x2-x1)}

qd=unary_union([g for (r,_),g in geos.items() if r=='Q1'])
for smp,pins in [('SMP11',['4','5']),('SMP30',['2','3']),('SMP09',['4','5']),('SMP31',['2','3'])]:
    for pin in pins:
        key=(smp,pin)
        # Select the inner ground pads based on coordinates, independent of numbering.
        if abs(pads[key]['x']-9.75)>5.0: continue
        v=gate(key,qd); v.update(capacity(v['copper_envelope_gap_mm'],.20,.15))
        v['object_a']=f'{smp}.{pin} GND';v['object_b']='QD pad field'
        measures[f'{smp}_{pin}_to_QD']=v
for name in ['R09','R31','R12','R28']:
    v=gate(components[name],qd);v.update(capacity(v['copper_envelope_gap_mm']))
    v['object_a']=name;v['object_b']='QD pad field'
    measures[name+'_to_QD']=v

report={'scope':'Read-only static pad-envelope measurements. No routing, copper pours, masks, via fences or native DRC were changed or certified.',
        'source_snapshot':str(SOURCE.relative_to(ROOT)),
        'source_pcb_sha256':s['source_sha256'],
        'actual_pcb_sha256':hashlib.sha256(Path(s['source']).read_bytes()).hexdigest(),
        'measures':measures,
        'resistor_body_conflict_examples':[]}
for name in ['R02','R05','R13','R34','R32','R24']:
    p1=pads[(name,'1')];p2=pads[(name,'2')]
    route=LineString([(p1['x'],p1['y']),(9.75,p1['y'])])
    report['resistor_body_conflict_examples'].append({'component':name,'rf_pad1_xy':[p1['x'],p1['y']],
        'dc_pad2_xy':[p2['x'],p2['y']], 'direct_horizontal_inward_route_crosses_dc_pad2':route.intersects(geos[(name,'2')]),
        'two_pad_envelope_bounds':list(components[name].bounds)})
assert report['actual_pcb_sha256']==report['source_pcb_sha256']
(OUT/'corridor_measurements.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
