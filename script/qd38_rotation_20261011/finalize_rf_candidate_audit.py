"""Set offline RF pass metadata only after a matching-hash independent audit."""
from pathlib import Path
import argparse,hashlib,json
ap=argparse.ArgumentParser();ap.add_argument('candidate',type=Path);ap.add_argument('audit',type=Path)
args=ap.parse_args();raw=args.candidate.read_bytes();audit=json.loads(args.audit.read_text())
assert audit['passed'] and audit['topology_passed'] and not audit['quality_flags']
assert audit['sha256']==hashlib.sha256(raw).hexdigest()
p=json.loads(raw)
p['rf_routing_validation'].update(passed=True,
    status='Offline full-copper spacing, topology, tangency and staircase audits passed. Native save/reopen and fabrication checks remain.',
    min_static_gap_mm=audit['minimum_foreign_static_gap'][0],
    min_RF_pair_gap_mm=audit['minimum_RF_pair_gap'][0],
    min_reserved_ring_gap_mm=audit['minimum_reserved_ring_gap'][0],
    routes=len(p['rf_routed_jobs']),arcs=len(p['arcs']),quality_flags=[])
args.candidate.write_text(json.dumps(p,indent=2))
print(hashlib.sha256(args.candidate.read_bytes()).hexdigest())
