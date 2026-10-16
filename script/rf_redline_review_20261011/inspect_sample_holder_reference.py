"""Read reference PCB board metadata and archive contents without modification."""
import importlib.util
import json
import re
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REF=Path('F:/Nextcloud/Lab/Instruments/CustomParts/Carrier_12MW_72DC/PCB/Sample_Holder')
spec=importlib.util.spec_from_file_location('native_reader',ROOT/'script/_support/zif_revision_v2/render_native_layout.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
for path in (REF/'Sample_Holder.PcbDoc',ROOT/'QSTL_QD4_2SET_38PAD/QSTL_QD4_2SET_38PAD.PcbDoc'):
    with r.olefile.OleFileIO(path) as o:
        board=r.props(o.openstream('Board6/Data').read())[0]
    chosen={k:v for k,v in board.items() if re.fullmatch(r'(VX|VY|KIND|CX|CY|SA|EA|RADIUS)\d+',k)}
    print(path)
    print(json.dumps(chosen,indent=2))
with zipfile.ZipFile(REF/'Sample_Holder_gerbers_new_2025.08.21.zip') as z:
    for name in ('Sample_Holder.GM','Sample_Holder.GM1','Sample_Holder.GM2'):
        print(name, z.read(name).decode('ascii',errors='replace'))
