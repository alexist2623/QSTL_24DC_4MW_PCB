"""Read-only saved copper checks for routing angle and DC via requirements."""
from pathlib import Path
import collections
import hashlib
import json
import math
import struct
import olefile
from shapely.geometry import Point, box
from shapely.affinity import rotate, translate

H = Path(__file__).resolve().parent
ROOT = H.parents[1]
DEST = ROOT / 'QSTL_QD4_2SET_38PAD'
PCB = DEST / 'QSTL_QD4_2SET_38PAD.PcbDoc'
UNIT = 2.54e-6
TOL = 1e-5
snapshot = json.loads((H / 'through_dc_saved_native_snapshot.json').read_text())
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = digest(PCB)
assert snapshot['source_sha256'] == before
plan = json.loads((DEST / 'full_copper_candidate.json').read_text())
audit = json.loads((H / 'through_dc_saved_native_audit.json').read_text())
assert audit['native_sha256'] == before and audit['passed']

def contact_geometries(net, layer):
    result = []
    for p in snapshot['pads']:
        if p['net'] != net or p['layer'] not in (layer, 74):
            continue
        if p['shape'] == 1:
            g = Point(p['x'], p['y']).buffer(p['size_x'] / 2, quad_segs=64)
        else:
            g = translate(rotate(box(-p['size_x']/2, -p['size_y']/2, p['size_x']/2, p['size_y']/2), p['rotation'], origin=(0, 0)), p['x'], p['y'])
        result.append(g.buffer(TOL))
    for v in snapshot['vias']:
        if v['net'] == net:
            result.append(Point(v['x'], v['y']).buffer(v['diameter']/2 + TOL))
    return result

groups = collections.defaultdict(list)
for i, t in enumerate(snapshot['tracks']):
    if t['net'] and (t['net'].startswith('DC') or t['net'].startswith(('MW', 'S'))):
        groups[(t['net'], t['layer'])].append((i, t))
turns = []
directions = []
excluded_contacts = 0
non_degree_two = []
for (net, layer), items in groups.items():
    nodes = collections.defaultdict(list)
    contacts = contact_geometries(net, layer)
    for i, t in items:
        a, b = (t['x1'], t['y1']), (t['x2'], t['y2'])
        if math.dist(a, b) < TOL:
            continue
        angle = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0])) % 180
        off = min(abs(angle - v) for v in (0, 45, 90, 135, 180))
        dx, dy = abs(b[0]-a[0]), abs(b[1]-a[1])
        lateral_error = min(dx, dy, abs(dx-dy) / math.sqrt(2))
        if off > .01 and lateral_error > TOL:
            directions.append(dict(net=net, layer=layer, track_index=i, a_mm=a, b_mm=b, angle_deg=angle, deviation_from_H_V_45_deg=off))
        for pt, other in ((a, b), (b, a)):
            nodes[tuple(round(x / UNIT) for x in pt)].append((i, pt, other))
    for key, edges in nodes.items():
        pt = tuple(x*UNIT for x in key)
        if any(g.covers(Point(pt)) for g in contacts):
            excluded_contacts += 1
            continue
        if len(edges) != 2:
            if len(edges) > 2:
                non_degree_two.append(dict(net=net, layer=layer, at_mm=pt, degree=len(edges)))
            continue
        vec = [(edge[2][0]-pt[0], edge[2][1]-pt[1]) for edge in edges]
        dot = sum(x*y for x, y in zip(*vec)) / (math.hypot(*vec[0])*math.hypot(*vec[1]))
        turn = 180 - math.degrees(math.acos(max(-1, min(1, dot))))
        if turn > .01:
            turns.append(dict(net=net, layer=layer, at_mm=pt, turn_deg=turn,
                              track_indices=[e[0] for e in edges],
                              neighboring_endpoints_mm=[e[2] for e in edges]))
dc_bad = [t for t in turns if t['net'].startswith('DC') and t['turn_deg'] > 45.01]
rf_sharp = [t for t in turns if not t['net'].startswith('DC')]
dc_layers = {f'DC{i:02}': sorted({layer for net, layer in groups if net == f'DC{i:02}' and layer in (2, 4)}) for i in range(1, 39)}
vias_by_net = collections.defaultdict(list)
for v in snapshot['vias']:
    if v['net'] and v['net'].startswith('DC'):
        vias_by_net[v['net']].append(v)
via_checks = []
for row in plan['pinmap']:
    net = row['dc_net']
    vias = vias_by_net[net]
    targets = [p for p in snapshot['pads'] if p['net'] == net and p['component'] != 'J1']
    zif = [v for v in vias if 2 < v['y'] < 7.1]
    device = [v for v in vias if v not in zif]
    in_pad = []
    for v in device:
        for p in targets:
            pad_geom = translate(rotate(box(-p['size_x']/2, -p['size_y']/2, p['size_x']/2, p['size_y']/2), p['rotation'], origin=(0, 0)), p['x'], p['y'])
            if pad_geom.buffer(TOL).covers(Point(v['x'], v['y'])):
                in_pad.append(v)
    via_checks.append(dict(net=net, count=len(vias), device_terminal_fanout_vias=len(device), device_via_centres_within_pad=len(in_pad),
                           device_via_pad_centre_distance_mm=[min(math.dist((v['x'], v['y']), (p['x'], p['y'])) for p in targets) for v in device],
                           zif_fanout_vias=len(zif), direct_QD=not row['rf'],
                           internal_layers=dc_layers[net], passed=len(vias)==2 and len(device)==1 and len(zif)==1 and len(dc_layers[net])==1))
report = dict(native_file=str(PCB), native_sha256=before, source_unchanged=digest(PCB)==before,
              methodology='Read-only saved-native track endpoint graph. Degree-two turns outside same-net pad and via land envelopes are checked. Native coordinates are grouped on the 2.54 nm integer grid. No pad/via endpoint turns are counted. Angular tolerance 0.01 degree.',
              track_count=len(snapshot['tracks']), arc_count=len(snapshot['arcs']),
              dc_turns_over_45_count=len(dc_bad), dc_turns_over_45=dc_bad,
              dc_bad_nets=sorted({x['net'] for x in dc_bad}),
              rf_sharp_turn_count=len(rf_sharp), rf_sharp_turns=rf_sharp,
              rf_bad_nets=sorted({x['net'] for x in rf_sharp}),
              non_H_V_45_track_count=len(directions), non_H_V_45_tracks=directions,
              excluded_pad_via_endpoint_nodes=excluded_contacts,
              multiway_junctions_not_counted=non_degree_two,
              dc_via_checks=via_checks, no_standalone_DC_transition_vias=all(x['passed'] for x in via_checks),
              direct_QD_DC_via_in_pad_count=sum(x['device_via_centres_within_pad'] for x in via_checks if x['direct_QD']),
              direct_QD_DC_via_outside_pad_count=sum(x['device_terminal_fanout_vias']-x['device_via_centres_within_pad'] for x in via_checks if x['direct_QD']),
              passed=not dc_bad and not rf_sharp and not directions
                     and all(x['passed'] and x['device_via_centres_within_pad']==1 for x in via_checks))
(H / 'saved_routing_requirement_audit.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k: report[k] for k in ('native_sha256', 'track_count', 'arc_count', 'dc_turns_over_45_count', 'dc_bad_nets', 'rf_sharp_turn_count', 'rf_bad_nets', 'non_H_V_45_track_count', 'no_standalone_DC_transition_vias', 'passed')}, indent=2))
print('DC_EXAMPLES', json.dumps(dc_bad[:5]))
print('RF_EXAMPLES', json.dumps(rf_sharp[:5]))
