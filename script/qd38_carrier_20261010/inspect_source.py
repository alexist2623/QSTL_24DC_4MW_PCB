"""Read the copied board and source schematic; preserve a baseline snapshot."""
from pathlib import Path
import importlib.util
import json
import sys
import olefile

ROOT=Path(__file__).resolve().parents[2]
H=Path(__file__).resolve().parent
P=ROOT/'QSTL_QD4_2SET_38PAD'
spec=importlib.util.spec_from_file_location('reader',ROOT/'script/_support/zif_revision_v2/render_native_layout.py')
reader=importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
reader.SOURCE=P/'QSTL_QD4_2SET_38PAD.PcbDoc'
n=reader.read_native()
(H/'baseline_native.json').write_text(json.dumps(n,indent=2))
sys.path.insert(0,str(ROOT/'script/_support/zif_revision/schematic'))
import build_zif_schematic as sch
rs=sch.records(P/'QSTL_QD4_2SET_38PAD.SchDoc')
(H/'baseline_schematic_records.json').write_text(json.dumps(rs,indent=2))
print(json.dumps(dict(outline=n['board_outline'],components=n['components'],mounts=[p for p in n['pads'] if p['component'] is None],
                     zif=[p for p in n['pads'] if p['component']=='J1'][:8]),indent=2))
print('SCHEMATIC VALUES',[(r.get('Name'),r.get('Text')) for r in rs if r.get('RECORD')=='41'][:50])
with olefile.OleFileIO(P/'QSTL_QD4_2SET_38PAD.PcbLib') as o:
    print('PCB LIB STREAMS',o.listdir())
