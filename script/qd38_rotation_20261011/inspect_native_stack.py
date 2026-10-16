"""Read saved native stack metadata without altering the board."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('stack_reader', ROOT / 'script/_support/zif_revision_v2/render_native_layout.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
source = ROOT / 'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'
with reader.olefile.OleFileIO(source) as ole:
    board = reader.props(ole.openstream('Board6/Data').read())[0]
result = {key: value for key, value in board.items() if key.startswith('V9_STACK_')}
(HERE / 'native_stack_metadata.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
