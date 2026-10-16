"""Read original embedded body transforms without editing or opening Altium."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import zlib

import olefile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'script/_support/qd_center_revision'))
from native_metadata_helpers import properties


def mm(value):
    return float(value.removesuffix('mil')) * .0254


def inspect(path):
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with olefile.OleFileIO(path) as doc:
        components = properties(doc.openstream('Components6/Data').read())
        models = properties(doc.openstream('Models/Data').read())
        data = doc.openstream('ComponentBodies6/Data').read()
        offset = 0
        out = []
        while offset < len(data):
            kind = data[offset]
            count = struct.unpack_from('<I', data, offset+1)[0] & 0xffffff
            raw = data[offset+5:offset+5+count]
            offset += 5+count
            assert kind == 12
            ci = struct.unpack_from('<H', raw, 7)[0]
            if ci == 65535:
                continue
            component = components[ci]
            marker = raw.index(b'V7_LAYER=')
            length = struct.unpack_from('<I', raw, marker-4)[0] & 0xffffff
            fields = dict(x.split('=',1) for x in raw[marker:marker+length].rstrip(b'\0').decode('cp1252').split('|') if '=' in x)
            tail = raw[marker+length:]
            vertices = struct.unpack_from('<I', tail)[0]
            outline = []
            if len(tail) == 4+vertices*16:
                outline = [[v*2.54e-6 for v in struct.unpack_from('<2d', tail, 4+i*16)] for i in range(vertices)]
            model_ids = [i for i, model in enumerate(models) if model.get('ID') == fields.get('MODELID')]
            model_records = []
            for index in model_ids:
                metadata = models[index]
                checksum = None
                if metadata.get('EMBED') == 'TRUE':
                    checksum = hashlib.sha256(zlib.decompress(doc.openstream(f'Models/{index}').read())).hexdigest()
                model_records.append(dict(metadata=metadata, embedded_step_sha256=checksum))
            origin = [mm(fields['MODEL.2D.X']), mm(fields['MODEL.2D.Y'])]
            component_origin = [mm(component['X']), mm(component['Y'])]
            out.append(dict(component=component.get('SOURCEDESIGNATOR'), component_fields=component,
                            body_fields=fields, model_origin_mm=origin, component_origin_mm=component_origin,
                            model_origin_minus_component_mm=[a-b for a,b in zip(origin, component_origin)],
                            rotation_xyz_deg=[float(fields['MODEL.3D.'+key]) for key in ('ROTX','ROTY','ROTZ')],
                            dz_mm=mm(fields['MODEL.3D.DZ']), standoff_mm=mm(fields['STANDOFFHEIGHT']),
                            overall_height_mm=mm(fields['OVERALLHEIGHT']), body_projection=int(fields['BODYPROJECTION']),
                            outline_mm=outline, embedded_model_records=model_records))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    return dict(source=str(path), source_sha256=before, source_unchanged=True, bodies=out)


def main():
    path = ROOT/'QSTL_24DC_4MW_PCB/QSTL_24DC_4MW_PCB.PcbDoc'
    report = inspect(path)
    (HERE/'source_model_transform_audit.json').write_text(json.dumps(report, indent=2))
    for body in report['bodies']:
        if body['component'].startswith('SMP') or body['component'] in ('R1','C1'):
            print(json.dumps({k:v for k,v in body.items() if k not in ('component_fields','body_fields','outline_mm','embedded_model_records')}, indent=2))
    print('SOURCE', report['source_sha256'])


if __name__ == '__main__':
    main()
