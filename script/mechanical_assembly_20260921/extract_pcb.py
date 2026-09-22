"""Extract current saved Altium geometry without changing the source design."""
from pathlib import Path
import sys, struct, json, zlib, hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROJECT = ROOT / 'QSTL_24DC_4MW_PCB'
SUPPORT = HERE.parent / '_support'
sys.path[:0] = [str(SUPPORT / 'qd_center_revision'), str(SUPPORT / 'final_routing/schematic')]
from native_metadata_helpers import properties, pads_stream, binary_records, UNIT, sha
from build_routed_copy import snapshot

streams = snapshot(PROJECT / 'QSTL_24DC_4MW_PCB.PcbDoc')
components = properties(streams['Components6/Data'])
models = properties(streams['Models/Data'])
model_dir = HERE / 'embedded_models'
model_dir.mkdir(exist_ok=True)
for i, model in enumerate(models):
    if model.get('EMBED') == 'TRUE':
        path = model_dir / f'model_{i}.step'
        path.write_bytes(zlib.decompress(streams[f'Models/{i}']))
        model['extracted_file'] = str(path)

bodies = []
for record in binary_records(streams['ComponentBodies6/Data'], 12):
    raw = record['body']
    ci = struct.unpack_from('<H', raw, 7)[0]
    a = raw.index(b'V7_LAYER=')
    n = struct.unpack_from('<I', raw, a-4)[0] & 0xffffff
    props = dict(x.split('=',1) for x in raw[a:a+n].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
    bodies.append({'component':components[ci]['SOURCEDESIGNATOR'] if ci != 65535 else None, 'props':props})

pads = []
for pad in pads_stream(streams['Pads6/Data']):
    ci = pad['component']
    pads.append({'component':components[ci]['SOURCEDESIGNATOR'] if ci != 65535 else None, 'number':pad['number'], 'layer':pad['layer'], 'rotation':pad['rotation'], 'coords_mm':[v*UNIT for v in pad['coords']]})
report = {'pcb_sha256':sha(PROJECT/'QSTL_24DC_4MW_PCB.PcbDoc'), 'components':components, 'models':models, 'bodies':bodies, 'pads':pads, 'board':properties(streams['Board6/Data'])}
(HERE/'pcb_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for component in components:
    print('COMPONENT', {k:component.get(k) for k in ('SOURCEDESIGNATOR','PATTERN','LAYER','X','Y','ROTATION')})
for body in bodies:
    print('BODY',body)
for pad in pads:
    if pad['coords_mm'][8]>0 and (pad['component'] is None or str(pad['component']).startswith('SMP')): print('HOLE',pad)
print('MODELS', models)
