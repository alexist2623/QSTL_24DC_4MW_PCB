"""Read original reference PCB datums and mechanical primitives without edits."""
from pathlib import Path
import collections
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
SUPPORT = ROOT / 'script' / '_support'
sys.path[:0] = [str(SUPPORT / 'qd_center_revision'), str(SUPPORT / 'final_routing' / 'schematic')]
from native_metadata_helpers import properties, pads_stream, binary_records, UNIT, sha
from build_routed_copy import snapshot

cached = json.loads((SUPPORT / 'reference_placement' / 'placements.json').read_text())
reference = Path(cached['source'])
paths = [reference, Path(r'C:\JeonghyunPark\Workspace\QSTL_25P_ZIF_ZIF\QSTL_25P_ZIF_ZIF\QSTL_25P_ZIF_ZIF.PcbDoc')]
results = []
for path in paths:
    digest = sha(path)
    if path == reference:
        assert digest == cached['source_sha256']
    streams = snapshot(path)
    comps = properties(streams['Components6/Data'])
    board = properties(streams['Board6/Data'])[0]
    mm = lambda value: float(value.removesuffix('mil')) * .0254
    outline = []
    i = 0
    while 'VX' + str(i) in board:
        outline.append([mm(board['VX' + str(i)]), mm(board['VY' + str(i)])])
        i += 1
    compact = [{'index': i, 'name': c.get('SOURCEDESIGNATOR'), 'pattern': c.get('PATTERN'),
                'xy_mm': [mm(c['X']), mm(c['Y'])], 'rotation': float(c['ROTATION'])} for i, c in enumerate(comps)]
    tracks = []
    for r in binary_records(streams['Tracks6/Data'], 4):
        raw = r['body']
        x0, y0, x1, y1, width = [v * UNIT for v in struct.unpack_from('<5i', raw, 13)]
        tracks.append({'layer': raw[0], 'component_index': struct.unpack_from('<H', raw, 7)[0], 'xyxy_mm': [x0, y0, x1, y1], 'width_mm': width})
    fills = []
    for r in binary_records(streams.get('Fills6/Data', b''), 6):
        raw = r['body']
        fills.append({'layer': raw[0], 'component_index': struct.unpack_from('<H', raw, 7)[0], 'xyxy_mm': [v * UNIT for v in struct.unpack_from('<4i', raw, 13)]})
    pads = [{'component': comps[p['component']].get('SOURCEDESIGNATOR') if p['component'] != 65535 else None,
             'number': p['number'], 'coords_mm': [v * UNIT for v in p['coords']], 'rotation': p['rotation'], 'shape': p['shape']} for p in pads_stream(streams['Pads6/Data'])]
    texts = [s.decode('cp1252') for s in re.findall(rb'[\x20-\x7e]{6,}', streams.get('Texts6/Data', b''))]
    rows = {'source': str(path), 'sha256': digest, 'unchanged': sha(path) == digest, 'board_outline_mm': outline, 'components': compact, 'tracks': tracks, 'fills': fills, 'pads': pads, 'texts': texts}
    results.append(rows)
    print(json.dumps({'source': str(path), 'sha256': digest, 'outline': outline, 'components': compact,
                      'track_layers': dict(collections.Counter(t['layer'] for t in tracks)), 'fills': fills,
                      'texts': texts}, indent=2))
(Path(__file__).parent / 'reference_geometry.json').write_text(json.dumps(results, indent=2) + '\n')
