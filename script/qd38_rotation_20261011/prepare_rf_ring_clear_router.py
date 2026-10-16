"""Reserve active SMP shield rings from foreign RF copper."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
source = (HERE / 'route_rf_inline_safe.py').read_text()
old = "    static.append((None,cavity,'blind_cavity'))"
new = """    static.append((None,cavity,'blind_cavity'))
    # Reserve the 1.05 mm circle of 0.25 mm shield-via lands. Only
    # the SMP's own S net uses its symmetric RF escape sector.
    static += [(f\"S{int(s['ref'][3:]):02}\", Point(s['x'],s['y']).buffer(1.175,quad_segs=96), s['ref']+'-shield-ring')
               for s in plan['smp']]"""
assert old in source
(HERE / 'route_rf_ring_clear.py').write_text(source.replace(old, new))
previous = json.loads((HERE / 'rf_ordered_candidate.json').read_text())
(HERE / 'rf_ring_clear_warm_snapshot.json').write_text(json.dumps({'routes': previous['rf_routed_jobs']}, indent=2))
print('Prepared active-SMP ring keepout router.')
