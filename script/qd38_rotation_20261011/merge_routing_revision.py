"""Merge independently routed DC and RF without importing stale DC geometry."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from geodesic_rf_assignment import remap
from audit_candidate import audit
from audit_rf_topology import audit as audit_rf

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dc', type=Path, required=True)
    parser.add_argument('--rf', type=Path, required=True)
    args = parser.parse_args()
    dc, rf = [json.loads(path.read_text()) for path in (args.dc, args.rf)]
    assert dc['dc_routing_validation']['passed'], 'DC routing is incomplete'
    assert rf['rf_routing_validation']['passed'], 'RF routing is incomplete'
    assert all(int(s['ref'][3:]) == s['q'] for s in dc['smp']), 'DC source must have original group labels'
    mapping = {int(s['ref'][3:]): s['q'] for s in rf['smp']}
    merged = remap(dc, mapping)
    def pad_key(p):
        return (p['ref'], p['pin']) if p['ref'] else (None, p['pin'], round(p['x'], 7), round(p['y'], 7))
    merged_pads = {pad_key(p): p for p in merged['physical_pads']}
    for p in rf['physical_pads']:
        if p['ref'] == 'J1':
            continue
        target = merged_pads[pad_key(p)]
        assert target['net'] == p['net'], (p['ref'], p['pin'], 'net mismatch')
        for key in ('x', 'y', 'sx', 'sy', 'rotation', 'layer'):
            if key in p:
                assert abs(target[key] - p[key]) < 1e-8, (p['ref'], p['pin'], key)
    merged['tracks'] = [t for t in merged['tracks'] if t['layer'] != 32] + copy.deepcopy([t for t in rf['tracks'] if t['layer'] == 32])
    merged['arcs'] = copy.deepcopy(rf.get('arcs', []))
    merged['rf_routed_jobs'] = copy.deepcopy(rf['rf_routed_jobs'])
    merged['rf_routing_validation'] = copy.deepcopy(rf['rf_routing_validation'])
    merged['status'] = 'ROTATED_SEVEN_ROW_ROUTING_PENDING_INDEPENDENT_AUDIT'
    merged['routing_sources'] = dict(dc=str(args.dc.resolve()), dc_sha256=sha(args.dc), rf=str(args.rf.resolve()), rf_sha256=sha(args.rf))
    result = audit(merged)
    rf_result = audit_rf(merged)
    result['rf_topology'] = rf_result
    result['passed'] = result['passed'] and rf_result['passed']
    merged['routing_complete'] = result['passed']
    if result['passed']:
        merged['status'] = 'ROTATED_SEVEN_ROW_ROUTING_VERIFIED_OFFLINE'
    path = HERE / 'merged_candidate.json'
    path.write_text(json.dumps(merged, indent=2))
    result['candidate_sha256'] = sha(path)
    (HERE / 'routing_audit.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(dict(passed=result['passed'], tracks=len(merged['tracks']), arcs=len(merged['arcs']),
                         failures=result['failures'][:10], rf_failures=rf_result['failures'][:10]), indent=2))
    raise SystemExit(0 if result['passed'] else 2)


if __name__ == '__main__':
    main()
