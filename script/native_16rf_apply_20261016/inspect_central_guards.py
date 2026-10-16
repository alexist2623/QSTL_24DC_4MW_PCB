"""Compare the saved component fingerprint against the staged candidate."""
from pathlib import Path
import json,sys
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import olefile,properties
p=json.loads((H/'candidate.json').read_text())
with olefile.OleFileIO(H/'before_dc_centralization/QSTL_QD4_2SET_38PAD.PcbDoc') as o:
    cs=properties(o.openstream('Components6/Data').read())
sch=json.loads((H/'before_dc_centralization/schematic_validation.json').read_text());uids={v:k for k,v in sch['components'].items()}
for d in cs:
    ref=uids.get(d.get('SOURCEUNIQUEID'))
    if ref in ('R15','R13','J1'):print(ref,d, next(c for c in p['components'] if c['ref']==ref))
