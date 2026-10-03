"""Inspect footprint storage and source component geometry for library recovery."""
from pathlib import Path
import sys, struct
H=Path(__file__).resolve().parent; R=H.parents[1]
sys.path.insert(0,str(R/'script/_support/qd_center_revision'))
from native_metadata_helpers import olefile, properties, pads_stream
for path in (R/'QSTL_24DC_4MW_PCB/Capacitors_0402.PcbLib', R/'QSTL_24DC_4MW_PCB/FPC_Adapters_20261002/ZIF_to_DSUB25/ZIF_to_DSUB25.PcbDoc'):
    print(path.name)
    with olefile.OleFileIO(path) as o:
        if path.suffix=='.PcbLib':
            for stream in o.listdir():
                b=o.openstream(stream).read()
                if stream==['Library','Data']:
                    n=struct.unpack_from('<I',b,0)[0]
                    print('LIBRARY_TAIL',repr(b[4+n:]))
                elif stream[0] in ('FileHeader','Library') and (len(stream)<3 or stream[1]=='ComponentParamsTOC'):
                    print('/'.join(stream),len(b),repr(b[:250]))
        else:
            print(properties(o.openstream('Components6/Data').read()))
            ps=pads_stream(o.openstream('Pads6/Data').read())
            for p in ps[:2]:print('PAD',p.keys(),p['number'],p['start'],p['end'],p['blocks'][4][:13].hex())
